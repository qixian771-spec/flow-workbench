"""Persistent, fixed-route Toonflow jobs. Unknown submissions are never replayed."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request
import uuid

from agent.config import BASE_DIR

ROOT = BASE_DIR / 'output' / 'toonflow-jobs'
BASE = 'http://127.0.0.1:8100'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def directory(job_id):
    if str(uuid.UUID(job_id)) != job_id:
        raise ValueError('Canonical task UUID required')
    return ROOT / 'jobs' / job_id


@contextmanager
def locked(job_id):
    folder = directory(job_id)
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield folder


def save(state, phase):
    state['phase'] = phase
    state['updatedAt'] = datetime.now(timezone.utc).isoformat()
    target = directory(state['jobId']) / 'state.json'
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(target)
    return state


def read(job_id):
    return json.loads((directory(job_id) / 'state.json').read_text())


def api(path, body=None, method=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(BASE + path, data=data, method=method, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def binding_for(scene_id):
    if not scene_id:
        return None
    try:
        if str(uuid.UUID(scene_id)) != scene_id:
            return None
    except (ValueError, TypeError):
        return None
    path = ROOT / 'bindings' / (scene_id + '.json')
    return json.loads(path.read_text()) if path.exists() else None


def guard_image(scene, orientation, provider):
    binding = binding_for(scene.get('id'))
    if binding is None:
        return None
    state = read(binding['jobId'])
    if (state['phase'] not in ('submitting', 'submitted') or provider != 'flow' or
            orientation != 'HORIZONTAL' or state['input']['model'] != 'BELUGA' or
            scene.get('_project_id') != state['projectId'] or scene.get('video_id') != state['videoId'] or
            scene.get('image_prompt') != state['input']['prompt'] or scene.get('parent_scene_id') or
            scene.get('character_names') not in (None, [], '[]')):
        raise ValueError('Toonflow fixed image route/input changed')
    return 'BELUGA'


def create(body):
    job_id = body['job_id']
    with locked(job_id) as folder:
        contract = {k: body[k] for k in ('model', 'prompt', 'ratio')}
        input_hash = digest(contract)
        if (folder / 'state.json').exists():
            state = read(job_id)
            if state.get('kind') != 'image' or state['inputHash'] != input_hash:
                raise ValueError('Task ID already bound to different input')
            return state
        if contract['model'] != 'BELUGA' or contract['ratio'] != '16:9' or not contract['prompt'].strip():
            raise ValueError('Only explicit BELUGA landscape image route is supported')
        if not api('/health').get('extension_connected'):
            raise ValueError('Flow extension disconnected; no project or generation submitted')
        state = {'jobId': job_id, 'input': contract, 'inputHash': input_hash, 'kind': 'image',
                 'route': {'provider': 'flow', 'model': 'BELUGA', 'orientation': 'HORIZONTAL'},
                 'createdAt': datetime.now(timezone.utc).isoformat()}
        save(state, 'creating-project')
        try:
            project = api('/api/projects', {'name': 'Toonflow local ' + job_id[:8],
                'material': 'realistic', 'video_model_family': 'omni_flash',
                'allow_voice': False, 'allow_music': False})
            state['projectId'] = project['id']; save(state, 'creating-video')
            video = api('/api/videos', {'project_id': project['id'], 'title': 'Toonflow ' + job_id[:8]})
            state['videoId'] = video['id']; save(state, 'creating-scene')
            scene = api('/api/scenes', {'video_id': video['id'], 'prompt': contract['prompt'],
                'image_prompt': contract['prompt'], 'character_names': [], 'chain_type': 'ROOT'})
            state['sceneId'] = scene['id']
            bindings = ROOT / 'bindings'; bindings.mkdir(parents=True, exist_ok=True)
            (bindings / (scene['id'] + '.json')).write_text(json.dumps({'jobId': job_id}))
            save(state, 'submitting')
            rows = api('/api/requests/batch', {'requests': [{'type': 'GENERATE_IMAGE', 'provider': 'flow',
                'orientation': 'HORIZONTAL', 'project_id': project['id'], 'video_id': video['id'], 'scene_id': scene['id']}]})
            if len(rows) != 1 or rows[0]['scene_id'] != scene['id'] or rows[0]['provider'] != 'flow':
                raise ValueError('Batch receipt identity mismatch; inspect without replay')
            state['requestId'] = rows[0]['id']
            return save(state, 'submitted')
        except Exception as error:
            state.update(error=str(error), failedPhase=state['phase'])
            return save(state, 'needs-inspection')


def refresh(job_id):
    with locked(job_id) as folder:
        state = read(job_id)
        if state['phase'] == 'complete':
            if hashlib.sha256((folder / 'image.bin').read_bytes()).hexdigest() != state['sha256']:
                raise ValueError('Stored artifact hash changed')
            return state
        if state['phase'] != 'submitted':
            return state
        req = api('/api/requests/' + state['requestId'])
        if (req['scene_id'] != state['sceneId'] or req['provider'] != 'flow' or req['retry_count'] != 0 or
                req['project_id'] != state['projectId'] or req['video_id'] != state['videoId'] or
                req['type'] != 'GENERATE_IMAGE' or req['orientation'] != 'HORIZONTAL'):
            state['error'] = 'Generation identity or retry count changed'
            return save(state, 'needs-inspection')
        if req['status'] in ('PENDING', 'PROCESSING'):
            return state
        if req['status'] != 'COMPLETED':
            state['error'] = req.get('error_message') or 'Flow generation failed'
            return save(state, 'needs-inspection')
        scene = api('/api/scenes/' + state['sceneId'])
        if scene['id'] != state['sceneId'] or scene['video_id'] != state['videoId']:
            raise ValueError('Completed scene identity mismatch')
        media_id = scene.get('horizontal_image_media_id')
        if not media_id or str(uuid.UUID(media_id)) != media_id or media_id != req['media_id']:
            raise ValueError('Completed image receipt mismatch')
        target = folder / 'image.part'
        result = subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location',
            '--max-time', '90', '--max-filesize', '104857600', '--output', str(target), scene['horizontal_image_url']], capture_output=True)
        if result.returncode:
            raise ValueError('Artifact download failed; generation will not be repeated')
        raw = target.read_bytes()
        if raw.startswith(b'\x89PNG\r\n\x1a\n'):
            mime = 'image/png'
        elif raw.startswith(b'\xff\xd8\xff'):
            mime = 'image/jpeg'
        else:
            raise ValueError('Unsupported returned image encoding')
        target.replace(folder / 'image.bin')
        state.update(mediaId=media_id, sha256=hashlib.sha256(raw).hexdigest(), mimeType=mime,
                     bytes=len(raw), flowRequestId=req.get('request_id'))
        return save(state, 'complete')
