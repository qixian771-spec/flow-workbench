import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from tests import test_toonflow_jobs as image_tests
from tests.test_toonflow_jobs import JOB, SCENE, PROJECT, VIDEO, REQUEST, MEDIA
from agent.services import toonflow_jobs as w, toonflow_video as v

CHILD='70f00f00-1111-2222-3333-444444444444'
CHILDSCENE='80f00f00-1111-2222-3333-444444444444'
OP='90f00f00-1111-2222-3333-444444444444'

class VideoTests(unittest.TestCase):
    def setUp(self):
        self.base=image_tests.ToonflowTests();self.base.setUp();self.addCleanup(self.base.doCleanups)
        parent=self.base.create();raw=b'first frame'
        (w.directory(JOB)/'image.bin').write_bytes(raw)
        parent.update(sha256=hashlib.sha256(raw).hexdigest(),mediaId=MEDIA);w.save(parent,'complete')
        self.body=dict(job_id=CHILD,model='abra_i2v_8s',prompt='Slow push in',ratio='16:9',duration=8,resolution='720p',source_image_sha256=parent['sha256'])
        self.project=dict(video_model_family='omni_flash',allow_voice=False,allow_music=False)
        self.responses=[self.project,dict(horizontal_image_media_id=MEDIA,horizontal_image_status='COMPLETED',horizontal_image_url='https://example.org/first'),dict(extension_connected=True),dict(id=CHILDSCENE),{},[dict(id=REQUEST,scene_id=CHILDSCENE,provider='flow')]]
    def create(self):
        with patch.object(w,'api',side_effect=self.responses):return v.create(self.body)
    def test_source_bytes_and_unknown_source_rejected(self):
        with self.assertRaises(ValueError):v.source_image('0'*64)
        (w.directory(JOB)/'image.bin').write_bytes(b'changed')
        with self.assertRaises(ValueError):v.source_image(self.body['source_image_sha256'])
    def test_root_identity_and_duplicate_no_replay(self):
        first=self.create();self.assertEqual(first['rootJobId'],JOB);self.assertEqual(first['videoId'],VIDEO)
        with patch.object(w,'api') as api:self.assertEqual(v.create(self.body),first);api.assert_not_called()
        with self.assertRaises(ValueError):v.create(dict(self.body,prompt='different'))
    def test_bad_routes_do_not_submit(self):
        for fields in [dict(model='veo'),dict(ratio='9:16'),dict(duration=6),dict(resolution='1080p')]:
            with patch.object(w,'api') as api,self.assertRaises(ValueError):v.create(dict(self.body,**fields));api.assert_not_called()
    def test_unknown_submit_pauses(self):
        with patch.object(w,'api',side_effect=self.responses[:-1]+[TimeoutError('unknown')]):state=v.create(self.body)
        self.assertEqual(state['phase'],'needs-inspection')
        with patch.object(w,'api') as api:v.create(self.body);v.refresh(CHILD);api.assert_not_called()
    def test_first_frame_and_route_guard(self):
        self.create();scene=dict(id=CHILDSCENE,_project_id=PROJECT,video_id=VIDEO,horizontal_image_media_id=MEDIA,horizontal_image_status='COMPLETED',duration=8,video_prompt='Slow push in')
        self.assertEqual(v.guard(scene,'HORIZONTAL','flow',self.project),v.ROUTE)
        for fields in [dict(horizontal_image_media_id=JOB),dict(duration=6),dict(video_prompt='changed'),dict(horizontal_end_scene_media_id=MEDIA)]:
            with self.assertRaises(ValueError):v.guard(dict(scene,**fields),'HORIZONTAL','flow',self.project)
        with self.assertRaises(ValueError):v.guard(scene,'VERTICAL','flow',self.project)
        with self.assertRaises(ValueError):v.guard(scene,'HORIZONTAL','assistant',self.project)
    def test_actual_submit_receipt_checked(self):
        self.create();data=dict(model='abra_i2v_8s',duration_s=8,resolution='720p',operations=[dict(operation=dict(name=OP))])
        for fields in [dict(model='wrong'),dict(duration_s=4),dict(resolution='1080p'),dict(operations=[])]:
            with self.assertRaises(ValueError):v.record_submit(CHILDSCENE,REQUEST,dict(data=dict(data,**fields)))
        v.record_submit(CHILDSCENE,REQUEST,dict(data=data))
        self.assertEqual(w.read(CHILD)['submitReceipt']['operationId'],OP)

    def test_complete_parent_repair_and_hash_mismatch(self):
        state=self.create();raw=b'\x00\x00\x00\x18ftypmp42video'
        (w.directory(CHILD)/'video.mp4').write_bytes(raw)
        state.update(sha256=hashlib.sha256(raw).hexdigest());w.save(state,'complete')
        with patch.object(w,'api') as api:
            v.refresh(CHILD);api.assert_not_called()
        self.assertEqual(w.read(JOB)['videoJobs'][CHILD],'complete')
        self.assertEqual(w.read(JOB)['nextStep'],'assembly-ready')
        (w.directory(CHILD)/'video.mp4').write_bytes(b'changed')
        with self.assertRaises(ValueError):v.refresh(CHILD)
    def test_failed_request_stays_visible_without_retry(self):
        self.create();req=dict(self.base.receipt,scene_id=CHILDSCENE,type='GENERATE_VIDEO',status='FAILED',error_message='provider error')
        with patch.object(w,'api',return_value=req):state=v.refresh(CHILD)
        self.assertEqual(state['phase'],'needs-inspection')
        with patch.object(w,'api') as api:v.refresh(CHILD);api.assert_not_called()

if __name__=='__main__':unittest.main()
