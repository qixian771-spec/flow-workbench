"""Two distinct Flow clips, one persisted run, native Seko editing and rendering."""
import base64
from copy import deepcopy
import hashlib
import json
import re
import subprocess
import uuid
from agent.services import seko_local_workflow as w
from agent.services import seko_local_video as v
from agent.services import seko_local_assembly as a

STEP = 'multishot_export:1'
ROUTE = {'text': w.TEXT_MODEL, 'video': deepcopy(v.ROUTE), 'editing': 'seko-native',
         'clips': [{'in_s': 1, 'out_s': 5}, {'in_s': 2, 'out_s': 6}],
         'transition': 'hard-cut', 'render_options': deepcopy(a.ROUTE['render_options'])}
TRANSITIONS = {'ready':'uploading', 'uploading':'uploaded', 'uploaded':'creating-node',
    'creating-node':'backfilled', 'backfilled':'creating-canvas', 'creating-canvas':'canvas-ready',
    'canvas-ready':'adding-node', 'adding-node':'nodes-ready', 'nodes-ready':'adding-timeline',
    'adding-timeline':'timeline-ready', 'timeline-ready':'trimming-first', 'trimming-first':'first-trimmed',
    'first-trimmed':'trimming-second', 'trimming-second':'trimmed', 'trimmed':'rendering',
    'rendering':'render-submitted', 'render-submitted':'render-ready'}


def save(s, phase=None, **fields):
    m=s['multishot']
    if phase:
        m['phase']=phase; m['history'].append({'phase':phase,'at':w.now()})
    m.update(fields); s['activeStepId']=STEP
    s['currentGate']='multishot_export_complete' if m['phase']=='complete' else 'multishot_'+m['phase']
    return w.save(s)


def contract(s):
    return {'action':'start_multishot','stepId':STEP,'sourceMediaId':s['video']['mediaId'],
            'sourceImageMediaId':s['mediaId'],'previousRenderId':s['assembly']['render']['id']}


def validate_source(s):
    a.validate_source(s)
    if s['assembly']['phase']!='complete' or s['assembly']['route']!=a.ROUTE:
        raise ValueError('Accepted single-clip export required')
    if 'multishot' in s and s['multishot']['route']!=ROUTE:
        raise ValueError('Fixed multishot route changed')


def start(job_id, body):
    with w.locked(job_id):
        s=w.read(job_id)
        if body!=contract(s): raise ValueError('Exact multishot source contract required')
        validate_source(s)
        if 'multishot' in s: return s
        project=w.api('/api/projects/'+s['flowProject'])
        if project['video_model_family']!='omni_flash' or project.get('allow_voice') or project.get('allow_music'):
            raise ValueError('Fixed Omni/no-voice/no-music project required')
        if w.api('/health')['extension_connected'] is not True: raise ValueError('Flow disconnected')
        source=w.api('/api/scenes/'+s['sceneId'])
        if source['horizontal_image_media_id']!=s['mediaId'] or source['horizontal_image_status']!='COMPLETED':
            raise ValueError('Accepted first frame changed')
        s['multishot']={'stepId':STEP,'route':deepcopy(ROUTE),'history':[], 'inputHash':w.digest(body)}
        save(s,'planning')
        try:
            prompt=('Return exact JSON only, no tools. Adapt a SECOND camera shot for the same local run, '
                'using the accepted first frame. The first clip gently pushes in on the empty teahouse, '
                'closed blue umbrella at left, white cup at right, rainy window and stone path. '
                'The second clip must be visually different: lateral dolly to the right, revealing parallax '
                'between the cup, umbrella and rainy window, then hold on the cup. No people, no new objects, '
                'no cuts within the clip, no speech, no music; silent. Describe actions, not character appearance. '
                'Use exact English 0-3s:, 3-6s:, 6-8s: sections, beginning 0-3s:. Include first frame. '
                'Preserve all supplied identities. No model names or execution instructions in prompt.\n'+
                json.dumps({'run_id':job_id,'source_image_media_id':s['mediaId'],
                    'source_image_node_id':s['receipt']['nodeId']}))
            plan=v.validate_plan(w.text_call(w.job_dir(job_id),'multishot-plan',prompt,v.PLAN_SCHEMA),s)
            if plan['prompt']==s['video']['plan']['prompt'] or 'right' not in plan['prompt'].lower():
                raise ValueError('Second shot must have a distinct rightward camera action')
            save(s,'creating-scene',plan=plan)
            scene=w.api('/api/scenes',{'video_id':s['videoId'],'display_order':1,
                'prompt':s['plan']['image_prompt'],'video_prompt':plan['prompt'],'character_names':[]})
            save(s,'binding',sceneId=scene['id'])
            w.index_path(scene['id']).write_text(json.dumps({'jobId':job_id,'stepId':STEP}))
            w.api('/api/scenes/'+scene['id'],{'horizontal_image_media_id':s['mediaId'],
                'horizontal_image_url':source['horizontal_image_url'],'horizontal_image_status':'COMPLETED',
                'duration':8},method='PATCH')
            save(s,'submitting')
            rows=w.api('/api/requests/batch',{'requests':[{'type':'GENERATE_VIDEO','provider':'flow',
                'orientation':'HORIZONTAL','project_id':s['flowProject'],'video_id':s['videoId'],'scene_id':scene['id']}]})
            if len(rows)!=1 or rows[0]['scene_id']!=scene['id'] or rows[0]['provider']!='flow':
                raise ValueError('Second video receipt mismatch; do not resubmit')
            return save(s,'submitted',requestId=rows[0]['id'])
        except Exception as error:
            return save(s,'needs-inspection',failedPhase=s['multishot']['phase'],error=str(error))


def guard(scene, orientation, provider, project, binding):
    s=w.read(binding['jobId']); m=s['multishot']
    if (m['route']!=ROUTE or m['phase'] not in ('submitting','submitted') or scene['id']!=m['sceneId'] or
        scene.get('_project_id')!=s['flowProject'] or provider!='flow' or orientation!='HORIZONTAL' or
        scene.get('horizontal_image_media_id')!=s['mediaId'] or scene.get('horizontal_image_status')!='COMPLETED' or
        scene.get('horizontal_end_scene_media_id') or scene.get('video_prompt')!=m['plan']['prompt'] or
        scene.get('duration')!=8 or not project or project.get('video_model_family')!='omni_flash' or
        project.get('allow_voice') or project.get('allow_music')):
        raise ValueError('Multishot fixed route/reference/prompt changed')
    return deepcopy(v.ROUTE)


def record_submit(binding, request_id, response):
    with w.locked(binding['jobId'],wait=True):
        s=w.read(binding['jobId']);m=s['multishot'];d=response.get('data',{}); ops=d.get('operations',[])
        if (m['requestId']!=request_id or d.get('model')!=v.ROUTE['model'] or d.get('duration_s')!=8 or
            d.get('resolution')!='720p' or len(ops)!=1): raise ValueError('Wrong second-video submit route')
        op=str(uuid.UUID(ops[0]['operation']['name']))
        if op==s['video']['submitReceipt']['operationId']: raise ValueError('Second operation repeats first')
        save(s,submitReceipt={'requestId':request_id,'operationId':op,'model':d['model'],
            'duration_s':8,'resolution':'720p','at':w.now()})


def download(uri,path):
    if not uri.startswith('https://'): raise ValueError('HTTPS media required')
    subprocess.run(['/usr/bin/curl','--fail','--silent','--show-error','--location','--proto','=https',
        '--proto-redir','=https','--max-time','120','--output',str(path),uri],check=True,capture_output=True,timeout=130)


def inspect(path):
    cfg=v.tools_config()
    meta=json.loads(subprocess.run([cfg['ffprobe'],'-v','error','-show_streams','-show_format','-of','json',str(path)],
        check=True,capture_output=True,text=True,timeout=30).stdout)
    v.validate_media(meta)
    subprocess.run([cfg['ffmpeg'],'-v','error','-xerror','-i',str(path),'-f','null','-'],
        check=True,capture_output=True,timeout=45)
    return meta


def sources(s):
    m=s['multishot']
    return [{'mediaId':s['video']['mediaId'],'sha256':s['video']['sha256'],
             'path':s['video']['upload']['path'],'nodeId':s['video']['receipt']['nodeId']},
            {'mediaId':m['mediaId'],'sha256':m['sha256'],'path':m['upload']['path'],'nodeId':m['receipt']['nodeId']}]


def validate_node(proof, source):
    if (set(proof)!={'nodeId','nodeGenId','filePath','readbackSha256','duration','status'} or
        not a.digits(proof['nodeId']) or not a.digits(proof['nodeGenId']) or proof['filePath']!=source['path'] or
        proof['readbackSha256']!=source['sha256'] or proof['duration']!=8 or proof['status']!='GENERATING_COMPLETED'):
        raise ValueError('Native node/media proof mismatch')


def validate_timeline(s, proof, trims):
    m=s['multishot'];clips=proof.get('clips',[])
    if (set(proof)!={'storyId','clips'} or not a.digits(proof['storyId']) or
        proof['storyId'] in (s['storyId'],s['assembly']['timeline']['storyId']) or len(clips)!=2 or
        len({c.get('shotId') for c in clips})!=2): raise ValueError('Isolated two-shot timeline required')
    for i,(clip,src,node) in enumerate(zip(clips,sources(s),m['nodes'])):
        expected=ROUTE['clips'][i] if i<trims else {'in_s':0,'out_s':8}
        if (set(clip)!={'shotId','nodeId','filePath','seq','start','end','duration','status','bindAudioSync'} or
            not a.digits(clip['shotId']) or clip['nodeId']!=node['nodeId'] or clip['filePath']!=src['path'] or
            clip['seq']!=i+1 or (clip['start'],clip['end'])!=(expected['in_s'],expected['out_s']) or
            clip['status']!='GENERATING_COMPLETED' or clip['duration'] not in ((4,8) if i<trims else (8,)) or
            (i<trims and clip['bindAudioSync'] is not False)):
            raise ValueError('Wrong two-shot sequence, source or trim')
    if trims and (proof['storyId']!=m['timeline']['storyId'] or
        [c['shotId'] for c in clips]!=[c['shotId'] for c in m['timeline']['clips']]):
        raise ValueError('Timeline identities changed after trim')


def checkpoint(job_id, body):
    if body.get('action')=='start_multishot': return start(job_id,body)
    with w.locked(job_id):
        s=w.read(job_id);m=s['multishot'];validate_source(s)
        if m.get('acceptedCheckpoint')==w.digest(body): return s
        if body.get('stepId')!=STEP or body.get('expectedPhase')!=m['phase']: raise ValueError('Concurrent/wrong multishot checkpoint')
        target=body.get('phase')
        if target=='needs-inspection': return save(s,target,failedPhase=m['phase'],error=str(body.get('error')))
        if TRANSITIONS.get(m['phase'])!=target: raise ValueError('Invalid multishot transition')
        if target=='uploaded':
            upload=body['upload']
            if set(upload)!={'path'} or not isinstance(upload['path'],str) or not upload['path'].startswith('STS/'):
                raise ValueError('Real video upload path required')
            if upload['path']==s['video']['upload']['path']: raise ValueError('Repeated first video')
            m['upload']=upload
        if target=='backfilled':
            validate_node(body['receipt'],{'path':m['upload']['path'],'sha256':m['sha256']})
            if body['receipt']['nodeId']==s['video']['receipt']['nodeId']: raise ValueError('Repeated source node')
            m['receipt']=body['receipt']
        if target=='canvas-ready':
            if not a.digits(body['canvasId']) or body['canvasId'] in (s['canvasId'],s['assembly']['target']['canvasId']):
                raise ValueError('New isolated canvas required')
            validate_node(body['node'],sources(s)[0]);m['canvasId']=body['canvasId'];m['nodes']=[body['node']]
        if target=='nodes-ready':
            validate_node(body['node'],sources(s)[1])
            if body['node']['nodeId'] in (m['nodes'][0]['nodeId'],m['receipt']['nodeId']): raise ValueError('Wrong second target node')
            m['nodes'].append(body['node'])
        if target in ('timeline-ready','first-trimmed','trimmed'):
            validate_timeline(s,body['timeline'],{'timeline-ready':0,'first-trimmed':1,'trimmed':2}[target])
            m['timeline' if target=='timeline-ready' else 'trimmedTimeline']=body['timeline']
        if target in ('render-submitted','render-ready'):
            r=body['render']
            if (not a.digits(r.get('id')) or (r.get('splitFlag'),r.get('subtitleFlag'),r.get('watermarkFlag'))!=(0,1,1) or
                r.get('renderVideoStatus') not in ('INITIALIZATION','GENERATING','GENERATING_COMPLETED')):
                raise ValueError('Native render receipt/options mismatch')
            if target=='render-ready':
                if r['id']!=m['render']['id'] or r['renderVideoStatus']!='GENERATING_COMPLETED': raise ValueError('Wrong/incomplete render')
                a.validate_export_url(r['videoUrl'])
            m['render' if target=='render-submitted' else 'renderStatus']=r
        return save(s,target,acceptedCheckpoint=w.digest(body))


def compare_export(s, path):
    """Verify every output segment against its own source, never synthesize an output."""
    cfg=v.tools_config();results=[];directory=w.job_dir(s['jobId'])
    for i,(src,trim) in enumerate(zip(['flow-video.mp4','multishot-video.mp4'],ROUTE['clips'])):
        scores=[]
        for offset in (0,1,2):
            start=i*96+offset
            filters=(f'[0:v]trim=start_frame={start}:end_frame={start+94},setpts=PTS-STARTPTS,crop=960:540:160:90[a];'
                f'[1:v]trim=start={trim["in_s"]}:end={trim["out_s"]},setpts=PTS-STARTPTS,crop=960:540:160:90[b];[a][b]ssim=shortest=1')
            check=subprocess.run([cfg['ffmpeg'],'-i',str(path),'-i',str(directory/src),'-filter_complex',filters,
                '-an','-f','null','-'],check=True,capture_output=True,text=True,timeout=45)
            (directory/f'multishot-ssim-{i}-{offset}.txt').write_text(check.stderr)
            match=re.search(r'All:([0-9.]+)',check.stderr)
            if not match: raise ValueError('Missing per-clip SSIM')
            scores.append({'offset_frames':offset,'ssim':float(match[1])})
        if max(x['ssim'] for x in scores)<.95: raise ValueError('Export segment does not match its ordered source: '+str(i))
        results.append({'seq':i+1,'scores':scores})
    return results


def collect(job_id):
    with w.locked(job_id):
        s=w.read(job_id);m=s['multishot'];validate_source(s)
        if m['phase'] not in ('submitted','render-ready'): return s
        try:
            if m['phase']=='submitted':
                r=w.api('/api/requests/'+m['requestId'])
                if r['status'] in ('PENDING','PROCESSING'): return s
                scene=w.api('/api/scenes/'+m['sceneId'])
                if (r['status']!='COMPLETED' or r['provider']!='flow' or r['retry_count']!=0 or
                    r['scene_id']!=m['sceneId'] or r['request_id']!=m['submitReceipt']['operationId'] or
                    scene['horizontal_image_media_id']!=s['mediaId'] or scene['horizontal_video_status']!='COMPLETED' or
                    r['media_id']!=scene['horizontal_video_media_id'] or r['media_id']==s['video']['mediaId']):
                    raise ValueError('Second video completion/reference/operation mismatch')
                path=w.job_dir(job_id)/'multishot-video.mp4';download(scene['horizontal_video_url'],path)
                meta=inspect(path);sha=hashlib.sha256(path.read_bytes()).hexdigest()
                if sha==s['video']['sha256']: raise ValueError('Second video repeats first bytes')
                return save(s,'ready',mediaId=str(uuid.UUID(r['media_id'])),sha256=sha,size=path.stat().st_size,meta=meta)
            save(s,'collecting')
            uri=m['renderStatus']['videoUrl'];a.validate_export_url(uri)
            path=w.job_dir(job_id)/'seko-multishot-export.mp4';download(uri,path);meta=inspect(path)
            if abs(float(meta['format']['duration'])-8)>.15: raise ValueError('Wrong two-shot duration')
            for src,file in zip(sources(s),['flow-video.mp4','multishot-video.mp4']):
                if hashlib.sha256((w.job_dir(job_id)/file).read_bytes()).hexdigest()!=src['sha256']:
                    raise ValueError('Source file bytes changed')
            scores=compare_export(s,path);sha=hashlib.sha256(path.read_bytes()).hexdigest()
            if sha in [src['sha256'] for src in sources(s)]: raise ValueError('Export is an original clip')
            manifest={'run_id':job_id,'next_step':'multishot_export_complete','exported':True,
                'story_id':m['timeline']['storyId'],'render_id':m['render']['id'],'export_sha256':sha,
                'clips':[dict(src,**trim,seq=i+1) for i,(src,trim) in enumerate(zip(sources(s),ROUTE['clips']))]}
            (w.job_dir(job_id)/'multishot-export-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
            return save(s,'complete',exportSha256=sha,exportSize=path.stat().st_size,exportMeta=meta,ssim=scores,nextStep=manifest)
        except Exception as error:
            return save(s,'needs-inspection',failedPhase=m['phase'],error=str(error))


def media(job_id,offset):
    s=w.read(job_id);m=s['multishot']
    if m['phase'] not in ('ready','uploading','uploaded','creating-node','backfilled') or offset<0:
        raise ValueError('Second video not ready')
    with (w.job_dir(job_id)/'multishot-video.mp4').open('rb') as handle:
        handle.seek(offset);data=handle.read(65536)
    return {'offset':offset,'length':len(data),'base64':base64.b64encode(data).decode()}
