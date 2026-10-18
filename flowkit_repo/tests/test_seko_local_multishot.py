import copy
import hashlib
import json
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from tests import test_seko_local_assembly as assembly_tests
JOB=assembly_tests.JOB
from agent.services import seko_local_multishot as m
from agent.services import seko_local_workflow as w
from agent.services import seko_local_video as v

SCENE='3306f96e-cea6-4acf-aa86-1bc5bdf6b387'
REQUEST='315a918c-3051-4da0-b814-5a2179a1d817'
MEDIA='6164f76f-a2e7-4b6a-b8f8-cad0f23c6e41'
PROMPT='0-3s: Match the first frame and dolly right. 3-6s: Continue right. 6-8s: Hold. Silent, no speech, no music.'

class MultiTest(unittest.TestCase):
    def setUp(self):
        assembly_tests.AssemblyTest.setUp(self)
        self.s.update(flowProject=MEDIA,videoId=MEDIA,sceneId=SCENE,receipt={'nodeId':'900'},plan={'image_prompt':'teahouse'})
        self.s['video'].update(plan={'prompt':'first prompt'},submitReceipt={'operationId':SCENE})
        self.s['assembly']={'phase':'complete','route':copy.deepcopy(m.a.ROUTE),'render':{'id':'500'},
            'timeline':{'storyId':'30'},'target':{'canvasId':'11'}}
        w.save(self.s)
        (w.ROOT/'scene-index').mkdir()
        self.plan={'run_id':JOB,'source_image_media_id':'image','source_image_node_id':'900','prompt':PROMPT}
        self.project={'video_model_family':'omni_flash','allow_voice':False,'allow_music':False}
        self.responses=[self.project,{'extension_connected':True},
            {'horizontal_image_media_id':'image','horizontal_image_status':'COMPLETED','horizontal_image_url':'https://example/image'},
            {'id':SCENE},{},[{'id':REQUEST,'scene_id':SCENE,'provider':'flow'}]]

    def start(self):
        with patch.object(w,'api',side_effect=self.responses),patch.object(w,'text_call',return_value=self.plan):
            return m.start(JOB,m.contract(self.s))

    def filled(self):
        s=self.start();s['multishot'].update(mediaId=MEDIA,sha256=hashlib.sha256(b'second').hexdigest(),
            upload={'path':'STS/second.mp4'},receipt=self.node('200','STS/second.mp4',hashlib.sha256(b'second').hexdigest()),
            canvasId='12',nodes=[self.node('300','STS/original.mp4',s['video']['sha256']),self.node('400','STS/second.mp4',hashlib.sha256(b'second').hexdigest())])
        (w.job_dir(JOB)/'multishot-video.mp4').write_bytes(b'second')
        return m.save(s,'adding-timeline')

    def node(self,id,path,sha):return {'nodeId':id,'nodeGenId':str(int(id)+1),'filePath':path,'readbackSha256':sha,'duration':8,'status':'GENERATING_COMPLETED'}
    def timeline(self,s,trims):
        return {'storyId':'40','clips':[{'shotId':str(600+i),'nodeId':s['multishot']['nodes'][i]['nodeId'],
            'filePath':src['path'],'seq':i+1,'start':m.ROUTE['clips'][i]['in_s'] if i<trims else 0,
            'end':m.ROUTE['clips'][i]['out_s'] if i<trims else 8,'duration':4 if i<trims else 8,
            'status':'GENERATING_COMPLETED','bindAudioSync':False} for i,src in enumerate(m.sources(s))]}
    def cp(self,s,phase,**fields):return m.checkpoint(JOB,{'stepId':m.STEP,'expectedPhase':s['multishot']['phase'],'phase':phase,**fields})

    def test_start_same_run_has_one_text_and_one_batch_and_is_idempotent(self):
        with patch.object(w,'api',side_effect=self.responses) as api,patch.object(w,'text_call',return_value=self.plan) as text:
            s=m.start(JOB,m.contract(self.s));again=m.start(JOB,m.contract(self.s))
        self.assertEqual(s,again);self.assertEqual(text.call_count,1);self.assertEqual(api.call_count,6)
        self.assertEqual(api.call_args.args[1]['requests'][0]['provider'],'flow')
        self.assertEqual(w.binding_for(SCENE)['stepId'],m.STEP)
        s['multishot']['route']['video']['model']='other';self.assertEqual(m.ROUTE['video']['model'],'abra_i2v_8s')

    def test_unknown_submit_stops_without_replay(self):
        with patch.object(w,'api',side_effect=self.responses[:-1]+[TimeoutError('unknown')]),patch.object(w,'text_call',return_value=self.plan):
            s=m.start(JOB,m.contract(self.s))
        self.assertEqual(s['multishot']['failedPhase'],'submitting')
        with patch.object(w,'api') as api:self.assertEqual(m.start(JOB,m.contract(self.s)),s);api.assert_not_called()

    def test_input_and_reference_route_changes_stop(self):
        body=m.contract(self.s);body['sourceImageMediaId']='other'
        with self.assertRaises(ValueError):m.start(JOB,body)
        self.start()
        scene={'id':SCENE,'_project_id':MEDIA,'horizontal_image_media_id':'image','horizontal_image_status':'COMPLETED','video_prompt':PROMPT,'duration':8}
        self.assertEqual(v.guard(scene,'HORIZONTAL','flow',self.project),v.ROUTE)
        for key,val in [('duration',6),('horizontal_image_media_id','wrong'),('video_prompt','wrong')]:
            with self.assertRaises(ValueError):v.guard(dict(scene,**{key:val}),'HORIZONTAL','flow',self.project)
        with self.assertRaises(ValueError):v.guard(scene,'HORIZONTAL','assistant',self.project)

    def test_actual_submit_operation_and_model_cannot_repeat(self):
        self.start();r={'data':{'model':'abra_i2v_8s','duration_s':8,'resolution':'720p','operations':[{'operation':{'name':MEDIA}}]}}
        v.record_submit(SCENE,REQUEST,r);self.assertEqual(w.read(JOB)['multishot']['submitReceipt']['operationId'],MEDIA)
        for data in [dict(r['data'],model='veo'),dict(r['data'],operations=[{'operation':{'name':SCENE}}])]:
            with self.assertRaises(ValueError):v.record_submit(SCENE,REQUEST,{'data':data})

    def test_order_duplicates_wrong_source_and_trim_rejected(self):
        s=self.filled();p=self.timeline(s,0);m.validate_timeline(s,p,0)
        for change in ['reverse','duplicate','path','trim','story','node']:
            q=copy.deepcopy(p)
            if change=='reverse':q['clips'].reverse()
            if change=='duplicate':q['clips'][1]=q['clips'][0]
            if change=='path':q['clips'][1]['filePath']=q['clips'][0]['filePath']
            if change=='trim':q['clips'][0]['start']=1
            if change=='story':q['storyId']='20'
            if change=='node':q['clips'][1]['nodeId']='300'
            with self.subTest(change=change),self.assertRaises(ValueError):m.validate_timeline(s,q,0)

    def test_both_trims_are_required_before_render(self):
        s=self.filled();s=self.cp(s,'timeline-ready',timeline=self.timeline(s,0))
        with self.assertRaises(ValueError):self.cp(s,'rendering')
        s=self.cp(s,'trimming-first');s=self.cp(s,'first-trimmed',timeline=self.timeline(s,1))
        s=self.cp(s,'trimming-second');s=self.cp(s,'trimmed',timeline=self.timeline(s,2));s=self.cp(s,'rendering')
        self.assertEqual(s['multishot']['phase'],'rendering')

    def test_stale_checkpoint_and_foreign_render_rejected(self):
        s=self.filled();s=self.cp(s,'timeline-ready',timeline=self.timeline(s,0))
        with self.assertRaises(ValueError):m.checkpoint(JOB,{'stepId':m.STEP,'expectedPhase':'ready','phase':'uploading'})
        s['multishot'].update(phase='render-submitted',render={'id':'700'});w.save(s)
        r={'id':'701','renderVideoStatus':'GENERATING_COMPLETED','splitFlag':0,'subtitleFlag':1,'watermarkFlag':1,'videoUrl':'https://seko-resource.sensetime.com/a'}
        with self.assertRaises(ValueError):self.cp(s,'render-ready',render=r)
        r['id']='700';r['renderVideoStatus']='GENERATING'
        with self.assertRaises(ValueError):self.cp(s,'render-ready',render=r)

    def test_render_collection_advances_same_job_and_is_readonly_on_replay(self):
        s=self.filled();s['multishot'].update(timeline=self.timeline(s,0),render={'id':'700'},
            renderStatus={'id':'700','videoUrl':'https://seko-resource.sensetime.com/a'});m.save(s,'render-ready')
        def download(uri,path):path.write_bytes(b'new actual render')
        with patch.object(m,'download',side_effect=download),patch.object(m,'inspect',return_value={'format':{'duration':'8.04'}}),patch.object(m,'compare_export',return_value=[{'seq':1},{'seq':2}]):s=m.collect(JOB)
        self.assertEqual(s['currentGate'],'multishot_export_complete');self.assertEqual(s['multishot']['nextStep']['run_id'],JOB)
        self.assertEqual([x['mediaId'] for x in s['multishot']['nextStep']['clips']],['video',MEDIA])
        with patch.object(m,'download') as download:self.assertEqual(m.collect(JOB),s);download.assert_not_called()

    def test_bad_second_segment_similarity_never_passes(self):
        s=self.filled();count=0
        def run(*args,**kwargs):
            nonlocal count
            count+=1;return SimpleNamespace(stderr='All:'+('.99' if count<=3 else '.40'))
        with patch.object(m.subprocess,'run',side_effect=run),self.assertRaises(ValueError):m.compare_export(s,w.job_dir(JOB)/'output.mp4')

    def test_duplicate_second_video_completion_rejected(self):
        s=self.start();s['multishot']['submitReceipt']={'operationId':MEDIA};w.save(s)
        request={'status':'COMPLETED','provider':'flow','retry_count':0,'scene_id':SCENE,'request_id':MEDIA,'media_id':'video'}
        scene={'horizontal_image_media_id':'image','horizontal_video_status':'COMPLETED','horizontal_video_media_id':'video'}
        with patch.object(w,'api',side_effect=[request,scene]),patch.object(m,'download') as download:s=m.collect(JOB)
        download.assert_not_called();self.assertEqual(s['multishot']['phase'],'needs-inspection')

if __name__=='__main__':unittest.main()
