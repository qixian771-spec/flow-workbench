import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from agent.services import seko_local_workflow as w
from agent.services import seko_local_assembly as a

JOB='eedacf2c-49c2-4b6f-9f02-652d60834930'


class AssemblyTest(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        root=patch.object(w,'ROOT',Path(temp.name));root.start();self.addCleanup(root.stop)
        w.job_dir(JOB).mkdir(parents=True)
        (w.ROOT/'config.json').write_text(json.dumps({'ffprobe':'/bin/echo','ffmpeg':'/bin/echo'}))
        (w.job_dir(JOB)/'flow-video.mp4').write_bytes(b'original')
        sha=hashlib.sha256(b'original').hexdigest()
        video={'phase':'complete','route':a.v.ROUTE,'mediaId':'video','sha256':sha,'upload':{'path':'STS/original.mp4'},
               'receipt':{'nodeId':'100'},'nextStep':{'next_step':'assembly_ready_gate'},
               'editManifest':{'run_id':JOB,'gate':'assembly_ready_gate','exported':False,
                'clips':[{'media_id':'video','seko_node_id':'100','sha256':sha,'in_s':0,'out_s':8,'source_image_media_id':'image'}]}}
        self.s={'jobId':JOB,'canvasId':'10','storyId':'20','phase':'complete','history':[],
                'mediaId':'image','video':video,'textModel':'gpt-6.1-sol','imageModel':'BELUGA'}
        w.save(self.s)
        validate=patch.object(a.v,'validate_receipt');validate.start();self.addCleanup(validate.stop)

    def start(self): return a.start(JOB,a.input_contract(self.s))
    def cp(self,s,phase,**fields):return a.checkpoint(JOB,{'stepId':a.STEP,'expectedPhase':s['assembly']['phase'],'phase':phase,**fields})
    def timeline(self,s,trim=False):
        return {'storyId':'30','shotId':'400','nodeId':'200','filePath':'STS/original.mp4','status':'GENERATING_COMPLETED',
                'seq':1,'start':1 if trim else 0,'end':7 if trim else 8,'duration':6 if trim else 8,'bindAudioSync':False}
    def target(self,s):return {'canvasId':'11','nodeId':'200','nodeGenId':'201','filePath':'STS/original.mp4','readbackSha256':s['video']['sha256']}
    def prepared(self):
        s=self.cp(self.start(),'creating-canvas');s=self.cp(s,'canvas-ready',target=self.target(s))
        s=self.cp(s,'adding');s=self.cp(s,'timeline-ready',timeline=self.timeline(s))
        s=self.cp(s,'trimming');s=self.cp(s,'trimmed',timeline=self.timeline(s,True))
        s=self.cp(s,'rendering');return self.cp(s,'render-submitted',render={'id':'500','renderVideoStatus':'INITIALIZATION','splitFlag':0,'subtitleFlag':1,'watermarkFlag':1})

    def test_same_run_start_is_idempotent_and_calls_no_models(self):
        with patch.object(w,'text_call') as text,patch.object(w,'api') as api:
            first=self.start();second=self.start()
        self.assertEqual(first,second);self.assertEqual(first['jobId'],JOB)
        api.assert_not_called();text.assert_not_called()

    def test_wrong_source_or_manifest_rejected_before_write(self):
        for key in ('videoMediaId','videoNodeId','editManifest','in_s'):
            body=a.input_contract(self.s);body[key]='changed'
            with self.assertRaises(ValueError):a.start(JOB,body)
        self.assertNotIn('assembly',w.read(JOB))

    def test_changed_bytes_fail_before_creation(self):
        (w.job_dir(JOB)/'flow-video.mp4').write_bytes(b'changed')
        with self.assertRaises(ValueError):self.start()

    def test_fixed_upstream_and_editing_routes_cannot_change(self):
        changed=copy.deepcopy(self.s);changed['video']['route']['model']='other';w.save(changed)
        with self.assertRaises(ValueError):self.start()
        w.save(self.s);s=self.start();s['assembly']['route']['in_s']=0;w.save(s)
        with self.assertRaises(ValueError):self.cp(s,'creating-canvas')

    def test_unknown_write_stops_and_start_never_replays(self):
        s=self.cp(self.start(),'creating-canvas');s=self.cp(s,'needs-inspection',error='timeout')
        self.assertEqual(self.start(),s)
        with self.assertRaises(ValueError):self.cp(s,'creating-canvas')

    def test_source_canvas_or_wrong_target_bytes_rejected(self):
        s=self.cp(self.start(),'creating-canvas')
        for key,value in [('canvasId','10'),('nodeId','100'),('readbackSha256','x'),('filePath','STS/wrong.mp4')]:
            target=self.target(s);target[key]=value
            with self.assertRaises(ValueError):self.cp(s,'canvas-ready',target=target)

    def test_wrong_trim_and_wrong_story_refused(self):
        s=self.cp(self.start(),'creating-canvas');s=self.cp(s,'canvas-ready',target=self.target(s));s=self.cp(s,'adding')
        p=self.timeline(s);p['storyId']='20'
        with self.assertRaises(ValueError):self.cp(s,'timeline-ready',timeline=p)
        s=self.cp(s,'timeline-ready',timeline=self.timeline(s));s=self.cp(s,'trimming')
        for key,value in [('start',0),('end',8),('shotId','401'),('filePath','STS/other.mp4'),('bindAudioSync',True)]:
            p=self.timeline(s,True);p[key]=value
            with self.assertRaises(ValueError):self.cp(s,'trimmed',timeline=p)

    def test_render_status_requires_exact_task_and_completed(self):
        s=self.prepared()
        for id_,status in [('other','GENERATING_COMPLETED'),('500','GENERATING')]:
            with self.assertRaises(ValueError):self.cp(s,'render-ready',renderStatus={'id':id_,'renderVideoStatus':status,'videoUrl':'https://seko-resource.sensetime.com/export.mp4'})

    def test_duplicate_checkpoint_and_skip_guard(self):
        s=self.start();body={'stepId':a.STEP,'expectedPhase':'reserved','phase':'creating-canvas'}
        first=a.checkpoint(JOB,body);self.assertEqual(a.checkpoint(JOB,body),first)
        with self.assertRaises(ValueError):self.cp(first,'rendering')

    def test_unexpected_media_origin_rejected(self):
        for uri in ['http://seko-resource.sensetime.com/a','https://other.example/a','https://user@seko-resource.sensetime.com/a']:
            with self.assertRaises(ValueError):a.validate_export_url(uri)

    def collection(self,duration=6.041667,ssim=.99):
        s=self.prepared();s=self.cp(s,'render-ready',renderStatus={'id':'500','renderVideoStatus':'GENERATING_COMPLETED','videoUrl':'https://seko-resource.sensetime.com/export.mp4'})
        meta={'streams':[{'codec_type':'video','width':1280,'height':720}],'format':{'duration':str(duration)}}
        def run(cmd,**kwargs):
            if cmd[0]=='/usr/bin/curl':(w.job_dir(JOB)/'seko-export.mp4').write_bytes(b'actual-render')
            return SimpleNamespace(stdout=json.dumps(meta),stderr='All:'+str(ssim))
        with patch.object(a.subprocess,'run',side_effect=run):return a.collect(JOB)

    def test_real_export_identity_advances_same_task(self):
        s=self.collection();self.assertEqual(s['currentGate'],'export_complete')
        self.assertEqual(s['assembly']['nextStep']['run_id'],JOB)
        self.assertNotEqual(s['assembly']['sha256'],s['video']['sha256'])
        with patch.object(a.subprocess,'run') as run:self.assertEqual(a.collect(JOB),s)
        run.assert_not_called()

    def test_wrong_duration_or_source_never_passes(self):
        s=self.collection(duration=8);self.assertEqual(s['assembly']['phase'],'needs-inspection')
        with patch.object(a.subprocess,'run') as run:self.assertEqual(a.collect(JOB),s)
        run.assert_not_called()

    def test_wrong_frame_similarity_is_not_replaced_or_rendered(self):
        s=self.collection(ssim=.4);self.assertEqual(s['assembly']['phase'],'needs-inspection')
        self.assertNotIn('nextStep',s['assembly']);self.assertEqual(s['assembly']['failedPhase'],'collecting')

    def test_only_media_collection_can_be_rechecked(self):
        s=self.cp(self.start(),'creating-canvas');self.cp(s,'needs-inspection',error='unknown')
        with self.assertRaises(ValueError):a.collect(JOB,recheck=True)


if __name__=='__main__':unittest.main()
