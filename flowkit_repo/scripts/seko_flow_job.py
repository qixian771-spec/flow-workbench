#!/usr/bin/env python3
"""Durable Flow job for an explicitly captured native Seko canvas request.

Browser operations stay in the CUA session. This CLI only calls local FlowKit and
downloads completed media. Unknown mutations are never retried automatically.
"""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid
from libtv_flow_bridge import api, save

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.services.prompt_adaptation import compile_seko_omni

BASE = 'http://127.0.0.1:8100'


def validate_capture(capture, job_id):
    selected = [j for j in capture['jobs'] if j['jobId'] == job_id]
    if len(selected) != 1:
        raise ValueError('Exactly one captured job required')
    job = selected[0]
    body = job['nativeRequest']
    if (job['state'] != 'captured' or job['actualProvider'] != 'flow' or
        job['actualModelFamily'] != 'omni_flash' or
        job['nativeRoute'] != 'seko-canvas/v1/canvas-node/gen-video' or
        body['canvasId'] != capture['canvasId'] or
        body['firstFrameNodeId'] != capture['referenceNodeId'] or
        body.get('lastFrameNodeId') or body.get('refNodeIds') or
        body['selectedVideoDuration'] != 8 or body['visionRatioId'] != 1 or
        body['resolutionType'] != 1 or not body['videoPrompt'].strip() or
        body['processedPrompt'] != body['videoPrompt']):
        raise ValueError('Unsupported native request; no generation submitted')
    return job


def prepare(args):
    """Shared preflight/compiler used by resident submission and controlled A/B."""
    capture = json.loads(Path(args.capture).read_text())
    job = validate_capture(capture, args.job_id)
    if api(BASE, '/health').get('extension_connected') is not True:
        raise ValueError('Flow extension disconnected')
    project = api(BASE, '/api/projects/' + args.flow_project)
    if project['video_model_family'] != 'omni_flash':
        raise ValueError('Explicit Omni Flash project required')
    ref = api(BASE, '/api/scenes/' + args.reference_scene)
    ref_video = api(BASE, '/api/videos/' + ref['video_id'])
    if ref_video['project_id'] != args.flow_project or ref['horizontal_image_status'] != 'COMPLETED':
        raise ValueError('Reference must be complete and belong to the selected project')
    media_id = str(uuid.UUID(ref['horizontal_image_media_id']))
    adaptation = compile_seko_omni(job['nativeRequest'], project, media_id)
    return job, project, ref, media_id, adaptation


def submit(args, path):
    job, project, ref, media_id, adaptation = prepare(args)
    state = {'phase': 'reserved', 'capture': job, 'reference_scene': args.reference_scene,
             'reference_media_id': media_id, 'flow_project': args.flow_project,
             'prompt': job['nativeRequest']['videoPrompt'], 'adaptation': adaptation}
    with path.open('x') as f:
        json.dump(state, f, ensure_ascii=False)
    state['phase'] = 'creating_video'; save(path, state)
    video = api(BASE, '/api/videos', {'project_id': args.flow_project,
        'title': 'Seko native ' + args.job_id, 'orientation': 'HORIZONTAL', 'target_duration_s': 8})
    state.update(phase='creating_scene', video_id=video['id']); save(path, state)
    scene = api(BASE, '/api/scenes', {'video_id': video['id'], 'prompt': state['prompt'],
        'video_prompt': adaptation['flow_prompt'], 'character_names': []})
    state.update(phase='binding_reference', scene_id=scene['id']); save(path, state)
    api(BASE, '/api/scenes/' + scene['id'], {'horizontal_image_media_id': media_id,
        'horizontal_image_url': ref['horizontal_image_url'], 'horizontal_image_status': 'COMPLETED',
        'duration': 8}, method='PATCH')
    state['phase'] = 'submitting'; save(path, state)
    requests = api(BASE, '/api/requests/batch', {'requests': [{'type': 'GENERATE_VIDEO',
        'provider': 'flow', 'orientation': 'HORIZONTAL', 'project_id': args.flow_project,
        'video_id': video['id'], 'scene_id': scene['id']}]})
    if len(requests) != 1:
        raise ValueError('Unexpected batch receipt; inspect before retrying')
    state.update(phase='submitted', request_id=requests[0]['id']); save(path, state)
    return {k: state[k] for k in ('phase', 'request_id', 'video_id', 'scene_id', 'adaptation')}


def collect(args, path):
    state = json.loads(path.read_text())
    if state['phase'] == 'downloaded':
        return {k: state[k] for k in ('phase', 'media_id', 'media_sha256', 'media_path')}
    if state['phase'] != 'submitted':
        raise ValueError('Ambiguous mutation; inspect state instead of retrying')
    request = api(BASE, '/api/requests/' + state['request_id'])
    if request['status'] in ('PENDING', 'PROCESSING'):
        return {'phase': 'pending', 'status': request['status']}
    scene = api(BASE, '/api/scenes/' + state['scene_id'])
    if request['status'] != 'COMPLETED' or scene['horizontal_video_status'] != 'COMPLETED':
        raise ValueError('Flow request did not complete successfully')
    media_id = str(uuid.UUID(scene['horizontal_video_media_id']))
    uri = scene['horizontal_video_url']
    if not uri.startswith('https://'):
        raise ValueError('Expected real HTTPS output')
    media = path.with_suffix('.mp4')
    partial = path.with_suffix('.mp4.part')
    try:
        subprocess.run(['/usr/bin/curl','--fail','--silent','--show-error','--location',
            '--proto','=https','--proto-redir','=https','--connect-timeout','15','--max-time','120',
            '--output',str(partial),uri],check=True,capture_output=True,text=True)
    except subprocess.CalledProcessError as error:
        raise ValueError(f'Flow generation completed; media download failed (exit {error.returncode}). '
                         'Only collect may be retried; do not submit a new generation.') from None
    meta = json.loads(subprocess.run(['ffprobe','-v','error','-show_streams','-show_format',
        '-of','json',str(partial)],capture_output=True,text=True,check=True).stdout)
    videos = [s for s in meta['streams'] if s['codec_type'] == 'video']
    if len(videos) != 1 or (videos[0]['width'],videos[0]['height']) != (1280,720) or abs(float(meta['format']['duration'])-8)>0.1:
        raise ValueError('Unexpected Flow media dimensions or duration')
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(partial),'-f','null','-'],check=True)
    partial.replace(media)
    state.update(phase='downloaded',media_id=media_id,media_path=str(media),
        media_sha256=hashlib.sha256(media.read_bytes()).hexdigest(),media_meta=meta)
    save(path,state)
    return {k: state[k] for k in ('phase','media_id','media_sha256','media_path')}


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('submit')
    for name in ('capture','job-id','flow-project','reference-scene','state'):
        s.add_argument('--'+name,required=True)
    sub.add_parser('collect').add_argument('--state',required=True)
    args=p.parse_args();path=Path(args.state).resolve()
    try:
        with path.with_suffix(path.suffix+'.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            print(json.dumps(submit(args,path) if args.command=='submit' else collect(args,path)))
    except (ValueError,KeyError,OSError,subprocess.CalledProcessError) as exc:
        print(str(exc),file=sys.stderr);return 1
    return 0

if __name__=='__main__':
    sys.exit(main())
