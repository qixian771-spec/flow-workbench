"""Read-only acceptance audit of a real local Seko tracer and captured browser evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request


def read(path):
    return json.loads(path.read_text())


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def audit(job, evidence, base='http://127.0.0.1:8100'):
    state = read(job / 'state.json')
    require(state['phase'] == 'complete', 'Local continuation incomplete')
    require(state['workflow'] == 'seko-public-local-v1', 'Wrong workflow')
    require(state['textModel'] == 'gpt-6.1-sol' and state['imageModel'] == 'BELUGA', 'Wrong model route')
    receipt, next_step = state['receipt'], state['nextStep']
    require(next_step['run_id'] == state['jobId'], 'Continuation changed run')
    require(next_step['consumed_node_id'] == receipt['nodeId'], 'Continuation changed node')
    require(next_step['consumed_media_id'] == state['mediaId'], 'Continuation changed media')
    require(next_step['next_step'] == 'video_ready_gate' and state['nextRoute']['dispatched'] is False,
            'Scope changed beyond image tracer')
    sha = hashlib.sha256((job / 'flow-image.bin').read_bytes()).hexdigest()
    require(sha == state['sha256'] == receipt['readbackSha256'], 'Original and Seko bytes differ')
    for key in ('jobId', 'stepId', 'requestId', 'mediaId', 'sha256', 'canvasId', 'storyId'):
        require(receipt[key] == state[key], 'Receipt changed ' + key)
    require(receipt['nodeStatus'] == 'GENERATING_COMPLETED', 'Seko node incomplete')
    phases = [e['phase'] for e in state['history']]
    required = ['planning', 'creating-video', 'creating-scene', 'submitting', 'submitted',
                'ready', 'uploading', 'uploaded', 'creating-node', 'backfilled', 'continuing', 'complete']
    positions = [phases.index(p) for p in required]
    require(positions == sorted(positions), 'Execution order changed')
    calls = {}
    for name in ('proposal', 'continue'):
        events = [json.loads(line) for line in (job / f'{name}-events.jsonl').read_text().splitlines()]
        completed = [e for e in events if e['type'] == 'turn.completed']
        require(len(completed) == 1, 'Text call did not finish exactly once')
        require(all(e['item']['type'] in ('agent_message', 'reasoning') for e in events if 'item' in e),
                'Text model executed a tool')
        calls[name] = completed[0]['usage']
    require(read(job / 'continue-result.json') == next_step, 'Continuation journal differs from model output')
    require(read(job / 'proposal-result.json') == state['plan'], 'Plan differs from actual text model output')
    require(receipt['nodeId'] in (job / 'continue-input.txt').read_text(), 'Model did not receive real node')
    for name in ('page-complete.json', 'reopened-page.json'):
        page = read(evidence / name)
        require(not page.get('error') and page['state']['phase'] == 'complete', 'Page completion missing')
        require(page['state']['jobId'] == state['jobId'], 'Page restored another task')
        require(page['state']['nextStep'] == next_step, 'Page restored another continuation')
    writes = []
    for name in ('network.json', 'replay-network.json'):
        net = read(evidence / name)
        require(net['complete'] and not net['truncated'], 'Incomplete observation window')
        for event in net['events']:
            if event.get('verb') in (None, 'GET', 'OPTIONS'):
                continue
            url = urllib.parse.urlsplit(event['url'])
            if url.hostname != 'seko.sensetime.com':
                continue
            require(not re.search(r'/canvas-node/(gen-|regenerate|multi-ref|video-retake|image-lighting)|/agent/run|/openapi/v1/(plan|story)-tasks', url.path),
                    'Vendor generation dispatch observed')
            writes.append({'window': name, 'method': event['verb'], 'path': url.path})
    creates = [r for r in writes if r['path'].endswith('/canvas-node')]
    require(len(creates) == 1 and creates[0]['window'] == 'network.json', 'Duplicate/missing Seko node creation')
    ui = (evidence / 'flow-ui.txt').read_text()
    require(state['plan']['image_prompt'] in ui and 'Nano Banana 2.1' in ui, 'Actual Flow model/prompt UI evidence missing')

    def get(path):
        with urllib.request.urlopen(base + '/api/' + path, timeout=20) as response:
            return json.load(response)

    request = get('requests/' + state['requestId'])
    scene = get('scenes/' + state['sceneId'])
    rows = get('requests?scene_id=' + state['sceneId'])
    require(len(rows) == 1, 'Repeated generation or unexpected next request')
    require(request['status'] == 'COMPLETED' and request['retry_count'] == 0, 'Flow completion/retry mismatch')
    require(request['provider'] == 'flow' and request['orientation'] == 'HORIZONTAL', 'Flow provider/orientation mismatch')
    require(request['media_id'] == state['mediaId'] == scene['horizontal_image_media_id'], 'Flow output identity mismatch')
    require(scene['image_prompt'] == state['plan']['image_prompt'], 'Flow did not use the planned image prompt')
    created = datetime.fromisoformat(request['created_at'].replace('Z', '+00:00'))
    start = datetime.fromisoformat(state['history'][0]['at'])
    end = datetime.fromisoformat(state['history'][-1]['at'])
    require(start <= created <= end, 'Flow request predates this local run')
    return {'schema_version': 1, 'accepted_at': datetime.now(timezone.utc).isoformat(),
        'verdict': 'pass_local_image_tracer', 'card': '01-04-01',
        'job_id': state['jobId'], 'step_id': state['stepId'], 'flow_request_id': state['requestId'],
        'flow_scene_id': state['sceneId'], 'flow_media_id': state['mediaId'],
        'seko_node_id': receipt['nodeId'], 'seko_node_gen_id': receipt['nodeGenId'],
        'sha256': sha, 'bytes': state['size'], 'dimensions': [state['width'], state['height']],
        'mime': state['mimeType'], 'source': state['source'], 'text_model': state['textModel'],
        'image_model': state['imageModel'], 'image_model_ui': 'Nano Banana 2.1', 'text_calls': calls,
        'history': state['history'], 'inspections': state.get('inspections', []),
        'local_task_continued': True, 'next_step': next_step, 'next_route': state['nextRoute'],
        'flow_requests_for_scene': len(rows), 'vendor_generation_writes': 0, 'seko_writes': writes,
        'reopened_task_same': True, 'cloud_run_resumed': False, 'full_film_verified': False,
        'persistent_page_worker_verified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.job, args.evidence)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'verdict': report['verdict'], 'job_id': report['job_id']}))
