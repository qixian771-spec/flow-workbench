"""Read-only audit: new Omni result, Seko byte readback, same local run continuation."""
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


def require(value, message):
    if not value:
        raise ValueError(message)


def audit(job, evidence, base='http://127.0.0.1:8100'):
    s = read(job / 'state.json'); v = s['video']; r = v['receipt']; n = v['nextStep']
    require(s['workflow'] == 'seko-public-local-v1' and s['textModel'] == 'gpt-6.1-sol', 'Wrong workflow/text model')
    require(v['phase'] == 'complete' and s['currentGate'] == 'assembly_ready_gate', 'Video continuation incomplete')
    route = {'provider':'flow', 'model':'abra_i2v_8s', 'mode':'frame_to_video',
             'duration_s':8, 'resolution':'720p', 'orientation':'HORIZONTAL'}
    require(v['route'] == route, 'Route mismatch')
    require(v['sourceImageMediaId'] == s['mediaId'] and v['sourceImageNodeId'] == s['receipt']['nodeId'], 'First frame changed')
    digest = lambda x: hashlib.sha256(json.dumps(x, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    require(v['sourcePromptHash'] == digest(s['nextStep']['video_prompt']), 'Source intent changed')
    require(v['promptHash'] == digest(v['plan']['prompt']), 'Video prompt changed')
    for key in ('jobId', 'canvasId', 'storyId'):
        require(r[key] == s[key], 'Receipt mismatch: ' + key)
    for key in ('stepId', 'requestId', 'mediaId', 'sha256', 'sourceImageMediaId', 'sourceImageNodeId'):
        require(r[key] == v[key], 'Receipt mismatch: ' + key)
    sha = hashlib.sha256((job / 'flow-video.mp4').read_bytes()).hexdigest()
    require(sha == v['sha256'] == r['readbackSha256'], 'Seko bytes changed')
    require(r['nodeType'] == 'VIDEO' and r['nodeStatus'] == 'GENERATING_COMPLETED', 'Seko video incomplete')
    require(r['nodeId'] != s['receipt']['nodeId'] and v['mediaId'] != s['mediaId'], 'Image reused as video')
    require((r['width'], r['height']) == (1280, 720) and abs(r['duration'] - 8) < .1 and v['decoded'], 'Invalid video')
    require(n['run_id'] == s['jobId'] and n['consumed_video_media_id'] == v['mediaId'] and
            n['consumed_video_node_id'] == r['nodeId'] and n['source_image_media_id'] == s['mediaId'] and
            n['next_step'] == 'assembly_ready_gate', 'Continuation did not consume this video')
    manifest = read(job / 'edit-manifest.json')
    require(manifest == v['editManifest'] and manifest['run_id'] == s['jobId'] and not manifest['exported'], 'Edit manifest mismatch')
    require(manifest['clips'] == [{'media_id':v['mediaId'], 'seko_node_id':r['nodeId'], 'sha256':sha,
                                 'in_s':0, 'out_s':8, 'source_image_media_id':s['mediaId']}], 'Wrong edit media')
    phases = [h['phase'] for h in v['history']]
    ordered = ['planning','binding','submitting','submitted','ready','uploading','uploaded','creating-node','backfilled','continuing','complete']
    indices = [phases.index(p) for p in ordered]
    require(indices == sorted(indices), 'Execution order mismatch')
    calls = {}
    for name, expected in [('video-plan', v['plan']), ('video-continue', n)]:
        events = [json.loads(line) for line in (job / (name + '-events.jsonl')).read_text().splitlines()]
        done = [e for e in events if e['type'] == 'turn.completed']
        require(len(done) == 1 and all(e['item']['type'] in ('agent_message','reasoning') for e in events if 'item' in e), 'Text execution failed or used tools')
        require(read(job / (name + '-result.json')) == expected, 'Journal differs from real text output')
        calls[name] = done[0]['usage']
    require(r['nodeId'] in (job / 'video-continue-input.txt').read_text(), 'Sol never received actual node')
    for name in ('page-complete.json', 'reopened-page.json'):
        p = read(evidence / name)
        require(not p.get('error') and p['state']['jobId'] == s['jobId'] and p['state']['video'] == v, 'Page restored another/incomplete task')
    writes = []; uploads = []
    for name in ('network.json', 'replay-network.json'):
        net = read(evidence / name)
        require(net['complete'] and not net['truncated'], 'Incomplete network window')
        for event in net['events']:
            if event.get('verb') in (None,'GET','OPTIONS'): continue
            url = urllib.parse.urlsplit(event['url'])
            if event['verb'] == 'PUT' and url.path.startswith('/STS/'):
                uploads.append({'window':name,'path':url.path})
            if url.hostname != 'seko.sensetime.com': continue
            require(not re.search(r'/canvas-node/(gen-|regenerate|multi-ref|video-retake|image-lighting)|/agent/run|/openapi/v1/(plan|story)-tasks',url.path), 'Vendor generation observed')
            writes.append({'window':name,'method':event['verb'],'path':url.path})
    creates = [x for x in writes if x['path'].endswith('/canvas-node')]
    require(len(creates) == 1 and creates[0]['window'] == 'network.json', 'Duplicate/missing node')
    # The observed Seko canvas module saves canvasNodeCtx/title to this exact endpoint.
    # Page telemetry and that context save are not generation/upload/node creation.
    allowed_reopen = {'/web_logs', '/seko-api/seko-canvas/v1/canvas/' + s['canvasId']}
    require(all(x['path'] in allowed_reopen for x in writes if x['window'] == 'replay-network.json'), 'Replay caused unexpected writes')
    require(uploads == [{'window':'network.json','path':'/'+v['upload']['path']}], 'Duplicate/missing video upload')
    def get(path):
        with urllib.request.urlopen(base + '/api/' + path, timeout=20) as response: return json.load(response)
    request = get('requests/' + v['requestId']); scene = get('scenes/' + s['sceneId'])
    rows = get('requests?scene_id=' + s['sceneId'])
    require(len(rows) == 2 and {x['id'] for x in rows} == {s['requestId'], v['requestId']}, 'Duplicate/unexpected generation')
    require(request['status'] == 'COMPLETED' and request['retry_count'] == 0 and request['provider'] == 'flow', 'Request failed or retried')
    require(request['request_id'] == v['submitReceipt']['operationId'] and v['submitReceipt']['model'] == route['model'], 'Actual operation/model mismatch')
    require(request['media_id'] == v['mediaId'] == scene['horizontal_video_media_id'], 'Result identity mismatch')
    require(scene['horizontal_image_media_id'] == s['mediaId'] and scene['video_prompt'] == v['plan']['prompt'], 'Scene prompt/reference mismatch')
    created = datetime.fromisoformat(request['created_at'].replace('Z','+00:00'))
    require(datetime.fromisoformat(v['history'][0]['at']) <= created <= datetime.fromisoformat(v['history'][-1]['at']), 'Old video reused')
    quality = read(evidence / 'quality.json')
    require(quality['accepted'] and quality['sha256'] == sha, 'Visual/decoded quality not accepted')
    playback = read(evidence / 'playback.json')
    require(len(playback) == 1 and playback[0]['ended'] and playback[0]['duration'] == 8 and
            playback[0]['width'] == 1280 and playback[0]['height'] == 720 and not playback[0].get('error'), 'Seko playback did not finish')
    return {'schema_version':1, 'accepted_at':datetime.now(timezone.utc).isoformat(),
        'verdict':'pass_local_video_tracer','card':'01-04-02','job_id':s['jobId'], 'scene_id':s['sceneId'],
        'flow_request_id':v['requestId'],'flow_media_id':v['mediaId'], 'submit_receipt':v['submitReceipt'],
        'seko_node_id':r['nodeId'],'seko_node_gen_id':r['nodeGenId'], 'sha256':sha, 'bytes':v['size'],
        'route':route,'text_model':s['textModel'],'text_calls':calls,'history':v['history'],
        'source_image_media_id':s['mediaId'],'source_image_node_id':s['receipt']['nodeId'],
        'source_prompt_hash':v['sourcePromptHash'],'prompt_hash':v['promptHash'], 'prompt':v['plan']['prompt'],
        'same_local_run_continued':True,'next_step':n,'edit_manifest':manifest,'reopen_idempotent':True,
        'flow_requests_for_scene':2,'video_requests':1,'vendor_generation_writes':0,'seko_writes':writes,'uploads':uploads,
        'quality':quality,'cloud_run_resumed':False,'full_film_verified':False,'persistent_page_worker_verified':False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('job','evidence','out'): parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args(); report = audit(args.job,args.evidence)
    args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'verdict':report['verdict'],'job_id':report['job_id']}))
