"""Read-only audit of the real native trim/export for one existing local run."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import urlopen


def read(p): return json.loads(p.read_text())
def require(ok,why):
    if not ok: raise ValueError(why)
def identity(url): return urlsplit(url).path
def shot_identity(x):
    keys=('id','seq','duration','shotVideoStartTime','shotVideoEndTime','videoGenId','bindAudioSync','linesAudioEnabledFlag')
    return {**{k:x.get(k) for k in keys},'media':identity(x.get('shotVideoUrl',''))}


def audit(job,evidence,base='http://127.0.0.1:8100'):
    s=read(job/'state.json');a=s['assembly'];v=s['video'];r=a['render'];t=a['trimmedTimeline']
    require(s['currentGate']=='export_complete' and a['phase']=='complete','Local export not complete')
    require(s['textModel']=='gpt-6.1-sol' and s['imageModel']=='BELUGA' and v['route']['model']=='abra_i2v_8s','Model route changed')
    require(a['route']=={'provider':'seko-native','model':None,'in_s':1,'out_s':7,'duration_s':6,
        'resolution':'720p','orientation':'HORIZONTAL','render_options':{'captionOption':1,'splitOption':0,'watermarkOption':1}},'Editing route changed')
    require(a['sourceMediaId']==v['mediaId'] and a['sourceNodeId']==v['receipt']['nodeId'],'Wrong source input')
    require(a['target']['canvasId']!=s['canvasId'] and t['storyId']!=s['storyId'],'Source workspace overwritten')
    original=hashlib.sha256((job/'flow-video.mp4').read_bytes()).hexdigest()
    exported=hashlib.sha256((job/'seko-export.mp4').read_bytes()).hexdigest()
    require(original==a['sourceSha256']==v['sha256']==a['target']['readbackSha256'],'Source bytes changed')
    require(exported==a['sha256'] and exported!=original,'Export is not a new output file')
    require(t['start']==1 and t['end']==7 and t['duration']==6 and not t['bindAudioSync'],'Trim not persisted')
    meta=a['meta'];video=[x for x in meta['streams'] if x['codec_type']=='video']
    require(len(video)==1 and (video[0]['width'],video[0]['height'])==(1280,720) and
        abs(float(meta['format']['duration'])-6)<.1 and a['decoded'],'Bad output format or incomplete decode')
    for score in a['ssim']:
        log=(job/f"export-ssim-{score['export_offset_frames']}.txt").read_text()
        require(float(re.search(r'All:([0-9.]+)',log)[1])==score['ssim'],'SSIM journal mismatch')
    require(max(x['ssim'] for x in a['ssim'])>=.95,'Export not matched to planned source range')
    manifest=read(job/'export-manifest.json')
    require(manifest==a['nextStep'] and manifest['run_id']==s['jobId'] and manifest['render_id']==r['id'] and
        manifest['story_id']==t['storyId'] and manifest['source_media_id']==v['mediaId'] and
        manifest['source_node_id']==a['sourceNodeId'] and manifest['export_sha256']==exported and
        manifest['exported'] and manifest['next_step']=='export_complete','Same-run output manifest mismatch')
    phases=[x['phase'] for x in a['history']]
    expected=['reserved','creating-canvas','canvas-ready','adding','timeline-ready','trimming','trimmed',
        'rendering','render-submitted','render-ready','collecting','complete']
    order=[phases.index(p) for p in expected]; require(order==sorted(order),'Operation order mismatch')
    for name in ('page-complete.json','reopened-page.json'):
        page=read(evidence/name)
        require(not page.get('error') and page['state']['jobId']==s['jobId'] and page['state']['assembly']==a,'Page resume differs')
    before=read(evidence/'preflight.json');after=read(evidence/'after.json')
    require([shot_identity(x)for x in before['shots']]==[shot_identity(x)for x in after['sourceShots']],'Source timeline changed')
    require(after['targetCanvas']['canvasId']==a['target']['canvasId'] and after['targetCanvas']['storyId']==t['storyId'],'Target canvas ownership mismatch')
    require(len(after['targetShots'])==1,'Unexpected extra clip')
    shot=after['targetShots'][0]
    require(shot['id']==t['shotId'] and shot['genVideoStatus']=='GENERATING_COMPLETED' and
        (shot['shotVideoStartTime'],shot['shotVideoEndTime'],shot['duration'])==(1,7,6) and
        identity(shot['shotVideoUrl'])=='/'+a['sourcePath'],'Native shot not the verified trim')
    node=after['targetNode']['node']
    require(node['id']==a['target']['nodeId'] and node['genId']==a['target']['nodeGenId'] and
        identity(node['genFileUrl'])=='/'+a['sourcePath'],'Target node changed')
    require(after['render']['id']==r['id'] and after['render']['renderVideoStatus']=='GENERATING_COMPLETED' and
        identity(after['render']['videoUrl'])==identity(a['renderStatus']['videoUrl']),'Native export not completed')
    writes=[]
    expected_writes=[('POST','/seko-api/seko-canvas/v1/canvas'),
        ('POST','/seko-api/seko-canvas/v1/canvas-node/add-to-editor'),
        ('PUT','/guodong-api/guodong-studio/v1/shots/'+t['shotId']+'/trim'),
        ('POST','/guodong-api/guodong-studio/v1/stories/'+t['storyId']+'/render')]
    for name in ('network.json','replay-network.json'):
        net=read(evidence/name);require(net['complete'] and not net['truncated'],'Truncated observation')
        for e in net['events']:
            if e.get('verb') in (None,'GET','OPTIONS'):continue
            u=urlsplit(e['url'])
            require(not(e['verb']=='PUT' and u.path.startswith('/STS/')),'Unexpected re-upload')
            if u.hostname!='seko.sensetime.com' or u.path=='/web_logs':continue
            require(name=='network.json','Reopen caused native write')
            writes.append((e['verb'],u.path))
    require(writes==expected_writes,'Unexpected/missing/duplicate native mutation')
    with urlopen(base+'/api/requests?scene_id='+s['sceneId'],timeout=20) as response: requests=json.load(response)
    require({x['id'] for x in requests}=={s['requestId'],v['requestId']} and len(requests)==2,'New generation dispatched')
    started=datetime.fromisoformat(a['history'][0]['at']).timestamp()
    events=list(job.glob('*-events.jsonl'))
    require({p.name for p in events}=={'proposal-events.jsonl','continue-events.jsonl','video-plan-events.jsonl','video-continue-events.jsonl'} and
        all(p.stat().st_mtime<started for p in events),'Unexpected/missing text model journal during editing')
    playback=read(evidence/'playback.json')
    require(playback['durationLabel']=='/00:06' and playback['finished'],'Native editor playback unverified')
    return {'schema_version':1,'accepted_at':datetime.now(timezone.utc).isoformat(),'card':'01-05-01',
        'verdict':'pass_local_native_trim_export','job_id':s['jobId'],'route':a['route'],
        'source_media_id':a['sourceMediaId'],'source_node_id':a['sourceNodeId'],'source_sha256':original,
        'target_canvas_id':a['target']['canvasId'],'target_node_id':a['target']['nodeId'],
        'target_story_id':t['storyId'],'shot_id':t['shotId'],'render_id':r['id'],'export_sha256':exported,
        'bytes':a['size'],'duration_s':float(meta['format']['duration']),'dimensions':[1280,720],
        'source_in_s':1,'source_out_s':7,'ssim':a['ssim'],'full_decode':True,'history':a['history'],
        'same_local_task_continued':True,'reopen_idempotent':True,'source_timeline_unchanged':True,
        'native_writes':[{'method':m,'path':p}for m,p in writes],'new_image_requests':0,'new_video_requests':0,
        'new_text_calls':0,'native_render_count':1,'watermark':'Seko original watermark preserved',
        'next_step':manifest,'full_episode_verified':False,'silence_verified':False,'persistent_injection_verified':False}


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('job','evidence','out'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();result=audit(args.job,args.evidence)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'verdict':result['verdict'],'job_id':result['job_id']}))
