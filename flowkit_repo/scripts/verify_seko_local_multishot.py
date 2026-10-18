"""Read-only real two-shot acceptance audit. No media generation or rendering."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import urlopen
from verify_seko_local_assembly import require, read, identity, shot_identity


def audit(job,evidence,base='http://127.0.0.1:8100'):
    s=read(job/'state.json');m=s['multishot'];v=s['video'];t=m['trimmedTimeline']
    require(m['phase']=='complete' and s['currentGate']=='multishot_export_complete','Same run not complete')
    require(s['textModel']==m['route']['text']=='gpt-6.1-sol' and s['imageModel']=='BELUGA','Text/image route mismatch')
    require(m['route']['video']==v['route']=={'provider':'flow','model':'abra_i2v_8s','mode':'frame_to_video',
        'duration_s':8,'resolution':'720p','orientation':'HORIZONTAL'},'Video route mismatch')
    require(m['route']['editing']=='seko-native' and m['route']['transition']=='hard-cut' and
        m['route']['clips']==[{'in_s':1,'out_s':5},{'in_s':2,'out_s':6}] and
        m['route']['render_options']=={'captionOption':1,'splitOption':0,'watermarkOption':1},'Edit contract changed')
    hashes=[hashlib.sha256((job/file).read_bytes()).hexdigest() for file in ['flow-video.mp4','multishot-video.mp4','seko-multishot-export.mp4']]
    require(hashes==[v['sha256'],m['sha256'],m['exportSha256']] and len(set(hashes))==3,'Distinct source/output bytes required')
    require(m['mediaId']!=v['mediaId'] and m['submitReceipt']['operationId']!=v['submitReceipt']['operationId'],'Repeated video/operation')
    meta=m['exportMeta'];video=[x for x in meta['streams'] if x['codec_type']=='video']
    require(len(video)==1 and (video[0]['width'],video[0]['height'])==(1280,720) and abs(float(meta['format']['duration'])-8)<.15,'Wrong output shape/duration')
    require(len(m['ssim'])==2 and [x['seq'] for x in m['ssim']]==[1,2],'Missing segment comparisons')
    for i,result in enumerate(m['ssim']):
        require(max(x['ssim'] for x in result['scores'])>=.95,'Wrong ordered segment '+str(i))
        for score in result['scores']:
            log=(job/f"multishot-ssim-{i}-{score['offset_frames']}.txt").read_text()
            require(float(re.search(r'All:([0-9.]+)',log)[1])==score['ssim'],'SSIM log differs')
    manifest=read(job/'multishot-export-manifest.json')
    require(manifest==m['nextStep'] and manifest['run_id']==s['jobId'] and manifest['exported'] and
        manifest['render_id']==m['render']['id'] and manifest['story_id']==t['storyId'] and
        manifest['export_sha256']==hashes[2] and manifest['next_step']=='multishot_export_complete','Manifest/run mismatch')
    require([x['mediaId']for x in manifest['clips']]==[v['mediaId'],m['mediaId']] and
        [x['sha256']for x in manifest['clips']]==hashes[:2],'Manifest order or media wrong')
    for name in ['page-complete.json','reopened-page.json']:
        p=read(evidence/name)
        require(not p.get('error') and p['state']['jobId']==s['jobId'] and p['state']['multishot']==m,'Page/reopen state differs')
    before=read(evidence/'preflight.json');after=read(evidence/'after.json')
    for name in ['sourceShots','previousShots']:
        require([shot_identity(x)for x in before[name]]==[shot_identity(x)for x in after[name]],'Historical timeline changed: '+name)
    require(after['targetCanvas']['canvasId']==m['canvasId'] and after['targetCanvas']['storyId']==t['storyId'],'Canvas ownership mismatch')
    require(len(after['targetShots'])==2 and len(t['clips'])==2,'Missing two clips')
    for i,(shot,proof,node) in enumerate(zip(after['targetShots'],t['clips'],m['nodes'])):
        src=manifest['clips'][i];actualNode=after['targetNodes'][i]['node']
        require(shot['id']==proof['shotId'] and shot['seq']==i+1 and shot['genVideoStatus']=='GENERATING_COMPLETED' and
            (shot['shotVideoStartTime'],shot['shotVideoEndTime'],shot['duration'])==(i+1,i+5,4) and
            identity(shot['shotVideoUrl'])=='/'+src['path'] and not shot['bindAudioSync'],'Wrong native ordered clip')
        require(actualNode['id']==node['nodeId'] and actualNode['genId']==node['nodeGenId'] and
            identity(actualNode['genFileUrl'])=='/'+src['path'] and node['readbackSha256']==src['sha256'],'Wrong target node bytes')
    require(after['render']['id']==m['render']['id'] and after['render']['renderVideoStatus']=='GENERATING_COMPLETED' and
        identity(after['render']['videoUrl'])==identity(m['renderStatus']['videoUrl']),'Render unverified')
    writes=[];uploads=[]
    for name in ['network.json','replay-network.json']:
        net=read(evidence/name);require(net['complete'] and not net['truncated'],'Incomplete network window')
        for e in net['events']:
            if e.get('verb') in (None,'GET','OPTIONS'):continue
            u=urlsplit(e['url'])
            if e['verb']=='PUT' and u.path.startswith('/STS/'):
                require(name=='network.json','Replay uploaded media');uploads.append(u.path)
            if u.hostname!='seko.sensetime.com' or u.path=='/web_logs':continue
            require(name=='network.json','Replay wrote to Seko')
            writes.append((e['verb'],u.path))
    auxiliary=[(verb,path)for verb,path in writes if '/canvas' not in path and '/shots/' not in path and not path.endswith('/render')]
    require(auxiliary==[('POST','/guodong-api/animo-support/content-detection/v1/video-moderation')],
        'Unexpected auxiliary or generation mutation')
    business=[(verb,path)for verb,path in writes if '/canvas' in path or '/shots/' in path or path.endswith('/render')]
    require(business==[
        ('POST','/seko-api/seko-canvas/v1/canvas-node'),('POST','/seko-api/seko-canvas/v1/canvas'),
        ('POST','/seko-api/seko-canvas/v1/canvas-node'),('POST','/seko-api/seko-canvas/v1/canvas-node/add-to-editor'),
        ('PUT','/guodong-api/guodong-studio/v1/shots/'+t['clips'][0]['shotId']+'/trim'),
        ('PUT','/guodong-api/guodong-studio/v1/shots/'+t['clips'][1]['shotId']+'/trim'),
        ('POST','/guodong-api/guodong-studio/v1/stories/'+t['storyId']+'/render')],'Unexpected business mutations')
    require(uploads==['/'+m['upload']['path']],'Must upload precisely the new second video once')
    def request_rows(scene):
        with urlopen(base+'/api/requests?scene_id='+scene,timeout=20)as r:return json.load(r)
    original=request_rows(s['sceneId']);new=request_rows(m['sceneId'])
    require(len(original)==2 and {x['id'] for x in original}=={s['requestId'],v['requestId']},'Original generation changed')
    require(len(new)==1,'Unexpected second-shot generation count');r=new[0]
    require(r['id']==m['requestId'] and r['provider']=='flow' and r['status']=='COMPLETED' and
        r['retry_count']==0 and r['request_id']==m['submitReceipt']['operationId'] and r['media_id']==m['mediaId'],'Wrong actual Omni completion')
    events=[json.loads(line)for line in (job/'multishot-plan-events.jsonl').read_text().splitlines() if line.strip()]
    require(any(e.get('type')=='turn.completed'for e in events) and not any(e.get('item',{}).get('type')not in ('agent_message','reasoning')for e in events if 'item'in e),'Text execution not completed/text-only')
    require(read(job/'multishot-plan-result.json')==m['plan'] and m['plan']['prompt']!=v['plan']['prompt'],'Distinct prompt missing')
    negative=read(evidence/'media-negative-tests.json')
    require(negative['black_intervals']==0 and len(negative['cases'])==2 and all(x['rejected'] and x['ssim']<.95 for x in negative['cases']),
        'Repeated/reversed media counterexamples or black-frame check missing')
    require('black_start:' not in (evidence/'blackdetect.txt').read_text(),'Black interval detected')
    for test in negative['cases']:
        require(float(re.search(r'All:([0-9.]+)',(evidence/(test['case']+'.txt')).read_text())[1])==test['ssim'],'Counterexample log differs')
    playback=read(evidence/'playback.json');require(playback['finished'] and playback['durationLabel']=='/00:08','Two-shot editor playback unverified')
    phases=[x['phase']for x in m['history']]
    expected=['planning','creating-scene','binding','submitting','submitted','ready','uploading','uploaded','creating-node','backfilled',
        'creating-canvas','canvas-ready','adding-node','nodes-ready','adding-timeline','timeline-ready','trimming-first','first-trimmed',
        'trimming-second','trimmed','rendering','render-submitted','render-ready','collecting','complete']
    require(phases==expected,'Unexpected/missing state progression')
    return {'schema_version':1,'card':'01-05-02','verdict':'pass_local_two_shot_native_export',
        'accepted_at':datetime.now(timezone.utc).isoformat(),'job_id':s['jobId'],'route':m['route'],
        'source_media_ids':[v['mediaId'],m['mediaId']],'source_sha256':hashes[:2],
        'second_request_id':m['requestId'],'second_operation_id':m['submitReceipt']['operationId'],
        'canvas_id':m['canvasId'],'story_id':t['storyId'],'shot_ids':[x['shotId']for x in t['clips']],
        'render_id':m['render']['id'],'export_sha256':hashes[2],'duration_s':float(meta['format']['duration']),
        'bytes':m['exportSize'],'dimensions':[1280,720],'ssim':m['ssim'],'history':m['history'],
        'native_writes':[{'method':verb,'path':path}for verb,path in writes],
        'upload_count':len(uploads),'new_image_requests':0,'new_video_requests':1,'new_text_calls':1,
        'same_local_task_continued':True,'two_distinct_clips':True,'replay_writes':0,
        'historical_timelines_unchanged':True,'manifest':manifest,'media_negative_tests':negative,
        'full_episode_verified':False,'voice_lipsync_verified':False,'persistent_injection_verified':False}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('job','evidence','out'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();r=audit(args.job,args.evidence);args.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'verdict':r['verdict'],'job_id':r['job_id']}))
