"""Audit packaged-extension startup using real refresh/reopen/reconnect evidence."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from datetime import datetime,timezone
if __package__:
    from .verify_seko_extension_build import require_build
else:
    from verify_seko_extension_build import require_build


def require(ok,message):
    if not ok:raise ValueError(message)
def read(path):return json.loads(path.read_text())


def audit(job,evidence):
    before=read(evidence/'state-before.json');after=read(job/'state.json')
    require(before==after,'Completed task was changed during resident startup')
    require(after['currentGate']=='multishot_export_complete' and after['multishot']['phase']=='complete','Original completed task missing')
    pre=read(evidence/'preflight.json')
    require(pre['permissions_unchanged'] and pre['host_permissions_unchanged'] and pre['version']=='0.5.2','Extension privileges changed')
    require(hashlib.sha256((job/'seko-multishot-export.mp4').read_bytes()).hexdigest()==pre['export_sha256']==after['multishot']['exportSha256'],'Output changed')
    cases=[]
    for case in ['refresh','new-tab','reconnect']:
        proof=read(evidence/(case+'.json'));status=proof['status']
        require_build(proof['loaded_build'], Path(__file__).resolve().parents[1]/'extension', pre['extension_id'])
        require(status['source']=='packaged-extension' and status['phase']=='ready' and not status['error'],'Packaged startup not ready: '+case)
        require(status['autoResumes']==[] and len(status['jobs'])==1 and status['jobs'][0]==after,'Completed task was replayed or replaced')
        require(proof['business_code_injected'] is False,'Manual injection is not resident startup')
        require(any(x.endswith('/seko_local_bundle.js') and x.startswith('chrome-extension://') for x in proof['loaded_scripts']),'Packaged script not observed')
        require(proof['panel_visible'] and proof['output_href']==f"https://seko.sensetime.com/creation?id={after['multishot']['timeline']['storyId']}&tab=editor&canvasId={after['multishot']['canvasId']}",'Wrong result UI/link')
        cases.append({'case':case,'at':proof['at'],'job_id':after['jobId'],'packaged_source_seen':True})
    disconnected=read(evidence/'disconnected.json')
    require(disconnected['status']['phase']=='disconnected' and disconnected['status']['error'],'Actual outage not observed')
    net=read(evidence/'network.json');require(net['complete'] and not net['truncated'],'Incomplete network observation')
    for event in net['events']:
        if event['verb'] in ('GET','OPTIONS'):continue
        url=urlsplit(event['url'])
        if url.hostname=='seko.sensetime.com' and url.path!='/web_logs':raise ValueError('Unexpected native write during completed-task resume')
        if event['verb']=='PUT' and url.path.startswith('/STS/'):raise ValueError('Repeated upload')
    require(read(evidence/'generation-after.json')==read(evidence/'generation-before.json'),'Generation ledger changed')
    return {'schema_version':1,'card':'01-05-03','verdict':'pass_packaged_completed_task_resident',
        'accepted_at':datetime.now(timezone.utc).isoformat(),'job_id':after['jobId'],'cases':cases,
        'permissions_changed':False,'new_installation':False,'business_code_injected':False,
        'actual_model_calls':0,'native_mutations':0,'task_unchanged':True,'export_sha256':pre['export_sha256'],
        'route':{'text':'gpt-6.1-sol','image':'BELUGA','video':'abra_i2v_8s','editing':'seko-native','resident':'local_deterministic'},
        'active_generation_interruption_real_verified':False,'unknown_write_replay_allowed':False,'full_episode_verified':False}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['job','evidence','out']:p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();r=audit(args.job,args.evidence);args.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(r['verdict'])
