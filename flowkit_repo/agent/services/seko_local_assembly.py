"""Seko native editing/export in the existing local run. Never render locally."""
import hashlib
import json
import re
import subprocess
from copy import deepcopy
from urllib.parse import urlsplit
from agent.services import seko_local_workflow as w
from agent.services import seko_local_video as v

STEP = 'assemble_export:1'
ROUTE = {'provider':'seko-native', 'model':None, 'in_s':1, 'out_s':7,
         'duration_s':6, 'resolution':'720p', 'orientation':'HORIZONTAL',
         'render_options':{'captionOption':1,'splitOption':0,'watermarkOption':1}}
TRANSITIONS = {'reserved':'creating-canvas','creating-canvas':'canvas-ready',
    'canvas-ready':'adding','adding':'timeline-ready','timeline-ready':'trimming',
    'trimming':'trimmed','trimmed':'rendering','rendering':'render-submitted',
    'render-submitted':'render-ready'}


def save(s, phase=None, **fields):
    a=s['assembly']
    if phase:
        a['phase']=phase; a['history'].append({'phase':phase,'at':w.now()})
    a.update(fields); s['activeStepId']=STEP
    s['currentGate']='export_complete' if a['phase']=='complete' else 'assembly_'+a['phase']
    return w.save(s)


def input_contract(s):
    return {'action':'start_assembly','stepId':STEP,'videoMediaId':s['video']['mediaId'],
        'videoNodeId':s['video']['receipt']['nodeId'],'editManifest':s['video']['editManifest'],
        'in_s':1,'out_s':7}


def digits(value):
    return isinstance(value,str) and value.isdigit()


def validate_source(s):
    video=s['video']; v.validate_receipt(s,video['receipt'])
    if video.get('route')!=v.ROUTE or s.get('textModel')!=w.TEXT_MODEL or s.get('imageModel')!='BELUGA':
        raise ValueError('Upstream model route changed')
    if video['phase']!='complete' or video['nextStep']['next_step']!='assembly_ready_gate':
        raise ValueError('Verified video continuation required')
    if hashlib.sha256((w.job_dir(s['jobId'])/'flow-video.mp4').read_bytes()).hexdigest()!=video['sha256']:
        raise ValueError('Source video bytes changed')
    if video['editManifest']['run_id']!=s['jobId'] or video['editManifest']['clips']!=[{
        'media_id':video['mediaId'],'seko_node_id':video['receipt']['nodeId'],
        'sha256':video['sha256'],'in_s':0,'out_s':8,'source_image_media_id':s['mediaId']}]:
        raise ValueError('Input edit manifest changed')


def start(job_id, body):
    with w.locked(job_id):
        s=w.read(job_id)
        if body!=input_contract(s): raise ValueError('Exact source and edit contract required')
        if 'assembly' in s: return s
        validate_source(s); v.tools_config()
        s['assembly']={'stepId':STEP,'route':deepcopy(ROUTE),'history':[], 'inputHash':w.digest(body),
            'sourceMediaId':s['video']['mediaId'],'sourceNodeId':s['video']['receipt']['nodeId'],
            'sourcePath':s['video']['upload']['path'],'sourceSha256':s['video']['sha256']}
        return save(s,'reserved')


def validate_timeline(s, proof, trimmed):
    a=s['assembly']; target=a['target']
    if (set(proof)!={'storyId','shotId','nodeId','filePath','status','seq','start','end','duration','bindAudioSync'} or
        not digits(proof['storyId']) or not digits(proof['shotId']) or
        proof['storyId']==s['storyId'] or proof['nodeId']!=target['nodeId'] or
        proof['filePath']!=a['sourcePath'] or proof['status']!='GENERATING_COMPLETED' or proof['seq']!=1 or
        (proof['start'],proof['end'])!=((1,7) if trimmed else (0,8)) or
        proof['duration'] not in ((6,8) if trimmed else (8,)) or
        (trimmed and proof['bindAudioSync'] is not False)):
        raise ValueError('Wrong timeline source, duration, trim or ownership')
    if trimmed and (proof['storyId']!=a['timeline']['storyId'] or proof['shotId']!=a['timeline']['shotId']):
        raise ValueError('Trim moved to another shot/story')


def validate_export_url(uri):
    u=urlsplit(uri)
    if u.scheme!='https' or u.hostname not in ('seko-resource.sensetime.com','seko-prod.oss-cn-shenzhen.aliyuncs.com') or u.username or u.port:
        raise ValueError('Unexpected Seko output origin')


def checkpoint(job_id,body):
    if body.get('action')=='start_assembly': return start(job_id,body)
    with w.locked(job_id):
        s=w.read(job_id); a=s['assembly']
        if a['route']!=ROUTE: raise ValueError('Fixed assembly route changed')
        if a.get('acceptedCheckpoint')==w.digest(body): return s
        if body.get('stepId')!=STEP or body.get('expectedPhase')!=a['phase']:
            raise ValueError('Concurrent/wrong assembly checkpoint')
        target=body.get('phase')
        if target=='needs-inspection':
            return save(s,target,failedPhase=a['phase'],error=str(body.get('error','Unknown operation')))
        if TRANSITIONS.get(a['phase'])!=target: raise ValueError('Invalid assembly transition')
        if target=='canvas-ready':
            t=body['target']
            if (set(t)!={'canvasId','nodeId','nodeGenId','filePath','readbackSha256'} or
                not all(digits(t[k]) for k in ('canvasId','nodeId','nodeGenId')) or t['canvasId']==s['canvasId'] or
                t['nodeId']==a['sourceNodeId'] or t['filePath']!=a['sourcePath'] or
                t['readbackSha256']!=a['sourceSha256']): raise ValueError('Wrong isolated target/video bytes')
            a['target']=t
        if target in ('timeline-ready','trimmed'):
            validate_timeline(s,body['timeline'],target=='trimmed')
            a['trimmedTimeline' if target=='trimmed' else 'timeline']=body['timeline']
        if target=='render-submitted':
            r=body['render']
            if (not digits(r.get('id')) or r.get('renderVideoStatus') not in ('INITIALIZATION','GENERATING','GENERATING_COMPLETED') or
                (r.get('splitFlag'),r.get('subtitleFlag'),r.get('watermarkFlag'))!=(0,1,1)):
                raise ValueError('Native render receipt/options mismatch')
            a['render']=r
        if target=='render-ready':
            r=body['renderStatus']
            if r.get('id')!=a['render']['id'] or r.get('renderVideoStatus')!='GENERATING_COMPLETED':
                raise ValueError('Native render incomplete or changed identity')
            validate_export_url(r['videoUrl']); a['renderStatus']=r
        return save(s,target,acceptedCheckpoint=w.digest(body))


def collect(job_id, recheck=False):
    with w.locked(job_id):
        s=w.read(job_id); a=s['assembly']
        if recheck:
            if a['phase']!='needs-inspection' or a.get('failedPhase')!='collecting' or 'renderStatus' not in a:
                raise ValueError('Only completed render media may be rechecked')
            a.setdefault('inspections',[]).append({'at':w.now(),'action':'read completed original render only','error':a.get('error')})
            a.pop('error',None); save(s,'render-ready')
        if a['phase']!='render-ready': return s
        save(s,'collecting')
        try:
            validate_source(s); uri=a['renderStatus']['videoUrl'];validate_export_url(uri)
            path=w.job_dir(job_id)/'seko-export.mp4'; cfg=v.tools_config()
            subprocess.run(['/usr/bin/curl','--fail','--silent','--show-error','--location','--proto','=https',
                '--proto-redir','=https','--max-time','120','--output',str(path),uri],check=True,capture_output=True,timeout=130)
            meta=json.loads(subprocess.run([cfg['ffprobe'],'-v','error','-show_streams','-show_format','-of','json',str(path)],
                check=True,capture_output=True,text=True,timeout=30).stdout)
            videos=[x for x in meta['streams'] if x['codec_type']=='video']
            if len(videos)!=1 or (videos[0]['width'],videos[0]['height'])!=(1280,720) or abs(float(meta['format']['duration'])-6)>.10:
                raise ValueError('Native export must be six seconds at 1280x720')
            subprocess.run([cfg['ffmpeg'],'-v','error','-xerror','-i',str(path),'-f','null','-'],check=True,capture_output=True,timeout=45)
            scores=[]
            for offset in (0,1):
                filters=(f'[0:v]trim=start_frame={offset}:end_frame={144+offset},setpts=PTS-STARTPTS,crop=960:540:160:90[a];'
                    '[1:v]trim=start=1:end=7,setpts=PTS-STARTPTS,crop=960:540:160:90[b];[a][b]ssim')
                check=subprocess.run([cfg['ffmpeg'],'-i',str(path),'-i',str(w.job_dir(job_id)/'flow-video.mp4'),
                    '-filter_complex',filters,'-an','-f','null','-'],check=True,capture_output=True,text=True,timeout=45)
                (w.job_dir(job_id)/f'export-ssim-{offset}.txt').write_text(check.stderr)
                match=re.search(r'All:([0-9.]+)',check.stderr)
                if not match: raise ValueError('SSIM result missing')
                scores.append({'export_offset_frames':offset,'ssim':float(match[1])})
            if max(x['ssim'] for x in scores)<.95: raise ValueError('Export does not match planned source range')
            sha=hashlib.sha256(path.read_bytes()).hexdigest()
            if sha==a['sourceSha256']: raise ValueError('Original video is not a rendered export')
            result={'run_id':job_id,'next_step':'export_complete','render_id':a['render']['id'],
                'story_id':a['timeline']['storyId'],'source_media_id':a['sourceMediaId'],
                'source_node_id':a['sourceNodeId'],'in_s':1,'out_s':7,'export_sha256':sha,'exported':True}
            (w.job_dir(job_id)/'export-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
            return save(s,'complete',sha256=sha,size=path.stat().st_size,meta=meta,decoded=True,ssim=scores,nextStep=result)
        except Exception as error:
            return save(s,'needs-inspection',failedPhase='collecting',error=str(error))
