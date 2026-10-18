"""Video step in the SAME public-workflow local run; no alternative routes."""
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import uuid

from agent.services import seko_local_workflow as w

STEP = 'generate_video:1'
ROUTE = {'provider': 'flow', 'model': 'abra_i2v_8s', 'mode': 'frame_to_video',
         'duration_s': 8, 'resolution': '720p', 'orientation': 'HORIZONTAL'}
PLAN_SCHEMA = w.object_schema({k: {'type': 'string'} for k in
    ('run_id', 'source_image_media_id', 'source_image_node_id', 'prompt')})
NEXT_SCHEMA = w.object_schema({
    'run_id': {'type': 'string'}, 'consumed_video_media_id': {'type': 'string'},
    'consumed_video_node_id': {'type': 'string'}, 'source_image_media_id': {'type': 'string'},
    'next_step': {'type': 'string', 'enum': ['assembly_ready_gate']},
    'edit_plan': {'type': 'string'},
})


def save(state, phase=None, **fields):
    video = state['video']
    if phase:
        video['phase'] = phase
        video['history'].append({'phase': phase, 'at': w.now()})
    video.update(fields)
    state['activeStepId'] = STEP
    state['currentGate'] = 'assembly_ready_gate' if video['phase'] == 'complete' else 'video_' + video['phase']
    return w.save(state)


def tools_config():
    cfg = json.loads((w.ROOT / 'config.json').read_text())
    selected = {}
    for name in ('ffprobe', 'ffmpeg'):
        value = cfg.get(name)
        if not isinstance(value, str) or not Path(value).is_absolute() or not Path(value).is_file():
            raise ValueError('Explicit existing media tool required: ' + name)
        selected[name] = value
    return selected


def input_contract(state):
    return {'action': 'start_video', 'stepId': STEP, 'imageMediaId': state['mediaId'],
            'imageNodeId': state['receipt']['nodeId'], 'sourcePromptHash': w.digest(state['nextStep']['video_prompt'])}


def validate_plan(plan, state):
    w.validate_text(plan, PLAN_SCHEMA)
    if (plan['run_id'] != state['jobId'] or plan['source_image_media_id'] != state['mediaId'] or
        plan['source_image_node_id'] != state['receipt']['nodeId']):
        raise ValueError('Video planner changed the accepted image/run')
    prompt = plan['prompt']
    if re.findall(r'(?<!\d)(\d+)-(\d+)s:', prompt) != [('0', '3'), ('3', '6'), ('6', '8')]:
        raise ValueError('Exact Omni timing segments required')
    if not prompt.startswith('0-3s:') or not all(word in prompt.lower() for word in
            ('no speech', 'no music', 'silent', 'first frame')):
        raise ValueError('Explicit first-frame and silent-shot contract required')
    if any(word in prompt.lower() for word in ('video_ready_gate', 'do not generate', 'flow omni', 'gpt-')):
        raise ValueError('Execution instructions leaked into the media prompt')
    return plan


def start(job_id, body):
    with w.locked(job_id):
        state = w.read(job_id)
        if body != input_contract(state):
            raise ValueError('Video input must match this run, accepted image and source prompt')
        if 'video' in state:
            return state
        if state['phase'] != 'complete' or state['nextStep']['next_step'] != 'video_ready_gate':
            raise ValueError('Accepted image continuation required')
        w.validate_receipt(state, state['receipt'])
        tools_config()
        project = w.api('/api/projects/' + state['flowProject'])
        if project['video_model_family'] != 'omni_flash' or project.get('allow_voice') or project.get('allow_music'):
            raise ValueError('Explicit Omni/no-voice/no-music project required')
        if w.api('/health')['extension_connected'] is not True:
            raise ValueError('Flow extension disconnected')
        scene = w.api('/api/scenes/' + state['sceneId'])
        if (scene['horizontal_image_media_id'] != state['mediaId'] or
            scene['horizontal_image_status'] != 'COMPLETED' or scene.get('horizontal_video_media_id')):
            raise ValueError('First-frame identity changed or an unbound video already exists')
        state['video'] = {'stepId': STEP, 'history': [], 'route': dict(ROUTE),
            'sourceImageMediaId': state['mediaId'], 'sourceImageNodeId': state['receipt']['nodeId'],
            'sourcePromptHash': body['sourcePromptHash'], 'inputHash': w.digest(body)}
        save(state, 'planning')
        try:
            prompt = ('You are the text-only video adapter for the same Seko public-workflow local run. '
                'Return exact JSON only, no tools. Preserve the supplied scene intent: empty teahouse, '
                'blue closed umbrella, white cup at its right, rainy window and gray stone path; gentle push-in, '
                'steam and rain motion, no people or text. Produce a production-ready English prompt for '
                'ONE continuous 8-second horizontal first-frame video, with exact 0-3s:, 3-6s:, 6-8s: segments. '
                'Start the prompt at 0-3s:. Include first frame, silent, no speech, no music. '
                'Do not put model/provider names, workflow instructions, IDs, or do-not-generate instructions '
                'inside the prompt. Preserve the IDs in the other fields. Do not change the gentle push-in '
                'into a locked camera.\n' + json.dumps({'run_id': job_id,
                    'source_image_media_id': state['mediaId'], 'source_image_node_id': state['receipt']['nodeId'],
                    'source_intent': state['nextStep']['video_prompt']}, ensure_ascii=False))
            plan = validate_plan(w.text_call(w.job_dir(job_id), 'video-plan', prompt, PLAN_SCHEMA), state)
            save(state, 'binding', plan=plan, promptHash=w.digest(plan['prompt']))
            w.api('/api/scenes/' + state['sceneId'], {'video_prompt': plan['prompt'], 'duration': 8}, method='PATCH')
            save(state, 'submitting')
            rows = w.api('/api/requests/batch', {'requests': [{'type': 'GENERATE_VIDEO',
                'provider': 'flow', 'orientation': 'HORIZONTAL', 'project_id': state['flowProject'],
                'video_id': state['videoId'], 'scene_id': state['sceneId']}]})
            if len(rows) != 1 or rows[0]['scene_id'] != state['sceneId'] or rows[0]['provider'] != 'flow':
                raise ValueError('Video batch receipt mismatch; inspect without resubmitting')
            return save(state, 'submitted', requestId=rows[0]['id'])
        except Exception as error:
            return save(state, 'needs-inspection', failedPhase=state['video']['phase'], error=str(error))


def guard(scene, orientation, provider, project):
    binding = w.binding_for(scene.get('id'))
    if binding is None:
        return None
    if binding.get('stepId') == 'multishot_export:1':
        from agent.services import seko_local_multishot as multi
        return multi.guard(scene, orientation, provider, project, binding)
    state = w.read(binding['jobId']); video = state.get('video', {})
    if (video.get('phase') not in ('submitting', 'submitted') or video.get('route') != ROUTE or
        scene.get('_project_id') != state['flowProject'] or provider != 'flow' or orientation != 'HORIZONTAL' or
        scene.get('horizontal_image_media_id') != state['mediaId'] or
        scene.get('horizontal_image_status') != 'COMPLETED' or scene.get('horizontal_end_scene_media_id') or
        scene.get('video_prompt') != video.get('plan', {}).get('prompt') or scene.get('duration') != 8 or
        not project or project.get('video_model_family') != 'omni_flash' or
        project.get('allow_voice') or project.get('allow_music')):
        raise ValueError('Local video fixed route, first frame or prompt changed')
    return dict(ROUTE)


def record_submit(scene_id, request_id, response):
    binding = w.binding_for(scene_id)
    if binding.get('stepId') == 'multishot_export:1':
        from agent.services import seko_local_multishot as multi
        return multi.record_submit(binding, request_id, response)
    with w.locked(binding['jobId'], wait=True):
        state = w.read(binding['jobId']); video = state['video']; data = response.get('data', {})
        operations = data.get('operations', [])
        if (video['requestId'] != request_id or data.get('model') != ROUTE['model'] or
            data.get('duration_s') != 8 or data.get('resolution') != '720p' or len(operations) != 1):
            raise ValueError('Actual Omni submit receipt does not match fixed route')
        operation = operations[0]['operation']['name']
        uuid.UUID(operation)
        save(state, submitReceipt={'requestId': request_id, 'operationId': operation,
            'model': data['model'], 'duration_s': data['duration_s'], 'resolution': data['resolution'], 'at': w.now()})


def validate_media(meta):
    streams = meta.get('streams', [])
    videos = [s for s in streams if s['codec_type'] == 'video']
    if (len(videos) != 1 or (videos[0]['width'], videos[0]['height']) != (1280, 720) or
        abs(float(meta['format']['duration']) - 8) > .1):
        raise ValueError('Omni output must be one 8-second 1280x720 video')


def collect(job_id):
    with w.locked(job_id):
        state = w.read(job_id); video = state['video']
        if video['phase'] != 'submitted':
            return state
        try:
            batch = w.api('/api/requests/batch-status?video_id=' + state['videoId'] + '&type=GENERATE_VIDEO')
            if not batch['done']:
                return state
            request = w.api('/api/requests/' + video['requestId'])
            scene = w.api('/api/scenes/' + state['sceneId'])
            if (request['status'] != 'COMPLETED' or request['provider'] != 'flow' or request['retry_count'] != 0 or
                request['scene_id'] != state['sceneId'] or request['request_id'] != video['submitReceipt']['operationId'] or
                scene['horizontal_video_status'] != 'COMPLETED' or request['media_id'] != scene['horizontal_video_media_id'] or
                scene['horizontal_image_media_id'] != state['mediaId']):
                raise ValueError('Video completion/operation/reference identity mismatch: ' + str(request.get('error_message')))
            uri = scene['horizontal_video_url']; media_id = str(uuid.UUID(request['media_id']))
            if media_id == state['mediaId'] or not uri.startswith('https://'):
                raise ValueError('New HTTPS video result required')
            path = w.job_dir(job_id) / 'flow-video.mp4'
            subprocess.run(['/usr/bin/curl', '--fail', '--silent', '--show-error', '--location',
                '--proto', '=https', '--proto-redir', '=https', '--max-time', '120', '--output', str(path), uri],
                check=True, capture_output=True, timeout=130)
            cfg = tools_config()
            meta = json.loads(subprocess.run([cfg['ffprobe'], '-v', 'error', '-show_streams', '-show_format',
                '-of', 'json', str(path)], check=True, capture_output=True, text=True, timeout=30).stdout)
            validate_media(meta)
            subprocess.run([cfg['ffmpeg'], '-v', 'error', '-xerror', '-i', str(path), '-f', 'null', '-'],
                check=True, capture_output=True, timeout=45)
            return save(state, 'ready', mediaId=media_id, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                size=path.stat().st_size, meta=meta, mimeType='video/mp4', decoded=True)
        except Exception as error:
            return save(state, 'needs-inspection', failedPhase=video['phase'], error=str(error))


def media(job_id, offset):
    video = w.read(job_id)['video']
    if video['phase'] not in ('ready', 'uploading', 'uploaded', 'creating-node', 'backfilled', 'continuing', 'complete') or offset < 0:
        raise ValueError('Video not ready')
    with (w.job_dir(job_id) / 'flow-video.mp4').open('rb') as handle:
        handle.seek(offset); chunk = handle.read(65536)
    return {'offset': offset, 'length': len(chunk), 'base64': base64.b64encode(chunk).decode()}


def validate_receipt(state, receipt):
    video = state['video']
    required = {'jobId', 'stepId', 'requestId', 'mediaId', 'sha256', 'canvasId', 'storyId',
        'sourceImageMediaId', 'sourceImageNodeId', 'nodeId', 'nodeGenId', 'nodeStatus', 'nodeType',
        'filePath', 'readbackSha256', 'duration', 'width', 'height'}
    if not isinstance(receipt, dict) or set(receipt) != required:
        raise ValueError('Exact video receipt required')
    for key in ('jobId', 'canvasId', 'storyId'):
        if receipt[key] != state[key]: raise ValueError('Video belongs to another ' + key)
    for key in ('stepId', 'requestId', 'mediaId', 'sha256', 'sourceImageMediaId', 'sourceImageNodeId'):
        if receipt[key] != video[key]: raise ValueError('Video receipt mismatch: ' + key)
    if (receipt['nodeStatus'] != 'GENERATING_COMPLETED' or receipt['nodeType'] != 'VIDEO' or
        receipt['readbackSha256'] != video['sha256'] or receipt['filePath'] != video['upload']['path'] or
        not str(receipt['nodeId']).isdigit() or not str(receipt['nodeGenId']).isdigit() or
        receipt['nodeId'] == state['receipt']['nodeId'] or abs(receipt['duration']-8) > .1 or
        (receipt['width'], receipt['height']) != (1280, 720)):
        raise ValueError('Persisted video identity, bytes or dimensions mismatch')


def checkpoint(job_id, body):
    if body.get('action') == 'start_video':
        return start(job_id, body)
    with w.locked(job_id):
        state = w.read(job_id); video = state['video']
        if video.get('acceptedCheckpoint') == w.digest(body): return state
        if body.get('stepId') != STEP or body.get('expectedPhase') != video['phase']:
            raise ValueError('Wrong/concurrent video checkpoint')
        target = body.get('phase')
        if {'ready':'uploading', 'uploading':'uploaded', 'uploaded':'creating-node', 'creating-node':'backfilled'}.get(video['phase']) != target:
            raise ValueError('Invalid video transition')
        if target == 'uploaded':
            upload = body.get('upload', {})
            if not isinstance(upload.get('path'), str) or not upload['path'].startswith('STS/'):
                raise ValueError('Real Seko video upload path required')
            video['upload'] = {'path': upload['path']}
        if target == 'backfilled':
            validate_receipt(state, body.get('receipt')); video['receipt'] = body['receipt']
        save(state, target, acceptedCheckpoint=w.digest(body))
        if target != 'backfilled': return state
        save(state, 'continuing')
        try:
            receipt = video['receipt']
            prompt = ('Return exact schema JSON, no tools. Continue the SAME local Seko public-workflow run. '
                'A new Omni video has been generated, decoded, and read back from its Seko node with identical '
                'bytes. Consume the supplied EXACT video and image identities; prepare a concise editing plan '
                'for this single 8s clip. Stop at assembly_ready_gate. Do not claim a film was exported.\n' +
                json.dumps({'run_id': job_id, 'consumed_video_media_id': video['mediaId'],
                    'consumed_video_node_id': receipt['nodeId'], 'source_image_media_id': state['mediaId'],
                    'duration_s': 8, 'prompt': video['plan']['prompt']}, ensure_ascii=False))
            next_step = w.text_call(w.job_dir(job_id), 'video-continue', prompt, NEXT_SCHEMA)
            w.validate_text(next_step, NEXT_SCHEMA)
            if (next_step['run_id'] != job_id or next_step['consumed_video_media_id'] != video['mediaId'] or
                next_step['consumed_video_node_id'] != receipt['nodeId'] or
                next_step['source_image_media_id'] != state['mediaId'] or not next_step['edit_plan'].strip()):
                raise ValueError('Next step did not consume this video')
            manifest = {'run_id': job_id, 'gate': 'assembly_ready_gate', 'exported': False,
                'clips': [{'media_id': video['mediaId'], 'seko_node_id': receipt['nodeId'],
                    'sha256': video['sha256'], 'in_s': 0, 'out_s': 8, 'source_image_media_id': state['mediaId']}]}
            (w.job_dir(job_id) / 'edit-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
            return save(state, 'complete', nextStep=next_step, editManifest=manifest)
        except Exception as error:
            return save(state, 'needs-inspection', failedPhase='continuing', error=str(error))
