"""Omni child jobs bound to verified local Toonflow image bytes."""
import hashlib
import json
import re
import subprocess
import uuid
from agent.services import toonflow_jobs as w

ROUTE = dict(provider='flow', model='abra_i2v_8s', mode='singleImage', duration_s=8,
             resolution='720p', orientation='HORIZONTAL')


def source_image(sha256):
    if not re.fullmatch(r'[a-f0-9]{64}', sha256):
        raise ValueError('First-frame SHA256 required')
    matches=[]
    for path in (w.ROOT/'jobs').glob('*/state.json'):
        state=json.loads(path.read_text())
        if state.get('kind')=='image' and state.get('phase')=='complete' and state.get('sha256')==sha256:
            if hashlib.sha256((path.parent/'image.bin').read_bytes()).hexdigest()!=sha256:
                raise ValueError('First-frame bytes changed')
            matches.append(state)
    if len(matches)!=1:
        raise ValueError('First frame must identify exactly one completed local Flow image job')
    return matches[0]


def create(body):
    job_id=body['job_id']
    with w.locked(job_id) as folder:
        contract={k:body[k] for k in ('model','prompt','ratio','duration','resolution','source_image_sha256')}
        if (folder/'state.json').exists():
            state=w.read(job_id)
            if state.get('kind')!='video' or state['inputHash']!=w.digest(contract):
                raise ValueError('Task ID already bound to different input')
            return state
        if (contract['model']!='abra_i2v_8s' or contract['ratio']!='16:9' or
            contract['duration']!=8 or contract['resolution']!='720p' or not contract['prompt'].strip()):
            raise ValueError('Only explicit 8s 720p landscape Omni first-frame route supported')
        source=source_image(contract['source_image_sha256'])
        project=w.api('/api/projects/'+source['projectId'])
        if project['video_model_family']!='omni_flash' or project.get('allow_voice') or project.get('allow_music'):
            raise ValueError('Source project Omni route changed')
        scene=w.api('/api/scenes/'+source['sceneId'])
        if scene.get('horizontal_image_media_id')!=source['mediaId'] or scene.get('horizontal_image_status')!='COMPLETED':
            raise ValueError('First-frame Flow receipt changed')
        if not w.api('/health').get('extension_connected'):
            raise ValueError('Flow disconnected; nothing submitted')
        state=dict(jobId=job_id,kind='video',rootJobId=source['jobId'],input=contract,inputHash=w.digest(contract),
                   route=dict(ROUTE),projectId=source['projectId'],videoId=source['videoId'],sourceImageMediaId=source['mediaId'])
        w.save(state,'creating-scene')
        with w.locked(source['jobId']):
            parent=w.read(source['jobId']);parent.setdefault('videoJobs',{})[job_id]='creating-scene';parent['nextStep']='video-pending';w.save(parent,parent['phase'])
        try:
            created=w.api('/api/scenes',dict(video_id=state['videoId'],prompt=contract['prompt'],video_prompt=contract['prompt'],character_names=[],chain_type='ROOT'))
            state['sceneId']=created['id'];w.save(state,'binding-first-frame')
            w.api('/api/scenes/'+state['sceneId'],dict(horizontal_image_media_id=source['mediaId'],
                horizontal_image_url=scene['horizontal_image_url'],horizontal_image_status='COMPLETED',duration=8),method='PATCH')
            (w.ROOT/'bindings'/(state['sceneId']+'.json')).write_text(json.dumps({'jobId':job_id,'kind':'video'}))
            w.save(state,'submitting')
            rows=w.api('/api/requests/batch',{'requests':[dict(type='GENERATE_VIDEO',provider='flow',orientation='HORIZONTAL',
                project_id=state['projectId'],video_id=state['videoId'],scene_id=state['sceneId'])]})
            if len(rows)!=1 or rows[0]['scene_id']!=state['sceneId'] or rows[0]['provider']!='flow':
                raise ValueError('Video batch receipt mismatch; inspect without replay')
            state['requestId']=rows[0]['id'];return w.save(state,'submitted')
        except Exception as error:
            state.update(error=str(error),failedPhase=state['phase']);return w.save(state,'needs-inspection')


def guard(scene,orientation,provider,project):
    binding=w.binding_for(scene.get('id'))
    if binding is None:return None
    state=w.read(binding['jobId'])
    if (state.get('kind')!='video' or state['phase'] not in ('submitting','submitted') or state['route']!=ROUTE or
        provider!='flow' or orientation!='HORIZONTAL' or scene.get('_project_id')!=state['projectId'] or
        scene.get('video_id')!=state['videoId'] or scene.get('horizontal_image_media_id')!=state['sourceImageMediaId'] or
        scene.get('horizontal_image_status')!='COMPLETED' or scene.get('horizontal_end_scene_media_id') or
        scene.get('duration')!=8 or scene.get('video_prompt')!=state['input']['prompt'] or
        not project or project.get('video_model_family')!='omni_flash' or project.get('allow_voice') or project.get('allow_music')):
        raise ValueError('Toonflow Omni route, input or first frame changed')
    return dict(ROUTE)


def record_submit(scene_id,request_id,response):
    binding=w.binding_for(scene_id)
    with w.locked(binding['jobId']):
        state=w.read(binding['jobId']);data=response.get('data',{});ops=data.get('operations',[])
        if (state['requestId']!=request_id or data.get('model')!='abra_i2v_8s' or data.get('duration_s')!=8 or
            data.get('resolution')!='720p' or len(ops)!=1):
            raise ValueError('Actual Omni submit receipt changed')
        operation=str(uuid.UUID(ops[0]['operation']['name']))
        state['submitReceipt']=dict(requestId=request_id,operationId=operation,model=data['model'],duration_s=8,resolution='720p')
        w.save(state,state['phase'])


def complete_parent(state):
    with w.locked(state['rootJobId']):
        parent=w.read(state['rootJobId'])
        if state['jobId'] not in parent.get('videoJobs',{}):
            raise ValueError('Video is not bound to root task')
        parent['videoJobs'][state['jobId']]='complete'
        parent['nextStep']='assembly-ready' if all(p=='complete' for p in parent['videoJobs'].values()) else 'video-pending'
        w.save(parent,parent['phase'])


def refresh(job_id):
    with w.locked(job_id) as folder:
        state=w.read(job_id)
        if state['kind']!='video':raise ValueError('Video task required')
        if state['phase']=='complete':
            if hashlib.sha256((folder/'video.mp4').read_bytes()).hexdigest()!=state['sha256']:
                raise ValueError('Stored video hash changed')
            complete_parent(state)
            return state
        if state['phase']!='submitted':return state
        req=w.api('/api/requests/'+state['requestId'])
        if (req['scene_id']!=state['sceneId'] or req['provider']!='flow' or req['retry_count']!=0 or
            req['video_id']!=state['videoId'] or req['project_id']!=state['projectId'] or
            req['type']!='GENERATE_VIDEO' or req['orientation']!='HORIZONTAL'):
            state['error']='Video request identity changed';return w.save(state,'needs-inspection')
        if req['status'] in ('PENDING','PROCESSING'):return state
        if req['status']!='COMPLETED':
            state['error']=req.get('error_message') or 'Omni failed';return w.save(state,'needs-inspection')
        scene=w.api('/api/scenes/'+state['sceneId']);receipt=state.get('submitReceipt',{})
        if (req['request_id']!=receipt.get('operationId') or not receipt or
            scene['horizontal_video_status']!='COMPLETED' or req['media_id']!=scene['horizontal_video_media_id'] or
            scene['horizontal_image_media_id']!=state['sourceImageMediaId']):
            raise ValueError('Video completion/first-frame receipt mismatch')
        media_id=str(uuid.UUID(req['media_id']))
        if media_id==state['sourceImageMediaId']:raise ValueError('New video media ID required')
        url=scene['horizontal_video_url']
        if not url.startswith('https://'):raise ValueError('HTTPS video artifact required')
        temporary=folder/'video.part'
        result=subprocess.run(['curl','--fail','--silent','--show-error','--location','--max-time','120',
            '--max-filesize','104857600','--output',str(temporary),url],capture_output=True)
        if result.returncode:raise ValueError('Video download failed; no generation replay')
        raw=temporary.read_bytes()
        if raw[4:8]!=b'ftyp':raise ValueError('Returned bytes are not MP4')
        meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(temporary)]))
        videos=[s for s in meta['streams'] if s['codec_type']=='video']
        if len(videos)!=1 or (videos[0]['width'],videos[0]['height'])!=(1280,720) or abs(float(meta['format']['duration'])-8)>.1:
            raise ValueError('Omni artifact must be 8s 1280x720')
        temporary.replace(folder/'video.mp4')
        state.update(mediaId=media_id,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),mimeType='video/mp4',
            duration=float(meta['format']['duration']),width=1280,height=720,flowRequestId=req['request_id'])
        w.save(state,'complete')
        complete_parent(state)
        return state
