import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from agent.services import toonflow_jobs as w

JOB='10f00f00-1111-2222-3333-444444444444'
SCENE='20f00f00-1111-2222-3333-444444444444'
PROJECT='30f00f00-1111-2222-3333-444444444444'
VIDEO='40f00f00-1111-2222-3333-444444444444'
REQUEST='50f00f00-1111-2222-3333-444444444444'
MEDIA='60f00f00-1111-2222-3333-444444444444'

class ToonflowTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory(); self.addCleanup(folder.cleanup)
        root=patch.object(w,'ROOT',Path(folder.name)); root.start(); self.addCleanup(root.stop)
        self.body=dict(job_id=JOB,model='BELUGA',ratio='16:9',prompt='Rainy tea house')
        self.receipt=dict(id=REQUEST,scene_id=SCENE,video_id=VIDEO,project_id=PROJECT,provider='flow',
                          type='GENERATE_IMAGE',orientation='HORIZONTAL',retry_count=0,status='COMPLETED',media_id=MEDIA)
        self.responses=[{'extension_connected':True},{'id':PROJECT},{'id':VIDEO},{'id':SCENE},[self.receipt]]
    def create(self):
        with patch.object(w,'api',side_effect=self.responses): return w.create(self.body)
    def test_duplicate_and_restart_do_not_submit(self):
        first=self.create()
        with patch.object(w,'api') as api:
            self.assertEqual(w.create(self.body),first); api.assert_not_called()
    def test_conflicting_input_rejected(self):
        self.create()
        with self.assertRaises(ValueError): w.create(dict(self.body,prompt='different'))
    def test_unsupported_routes_never_submit(self):
        for fields in [dict(model='other'),dict(ratio='9:16'),dict(prompt=' ')]:
            with patch.object(w,'api') as api,self.assertRaises(ValueError):
                w.create(dict(self.body,**fields)); api.assert_not_called()
    def test_disconnection_never_creates_project(self):
        with patch.object(w,'api',return_value={'extension_connected':False}) as api,self.assertRaises(ValueError):
            w.create(self.body)
        self.assertEqual(api.call_args_list[0].args,('/health',)); self.assertEqual(api.call_count,1)
    def test_unknown_submission_cannot_replay(self):
        with patch.object(w,'api',side_effect=self.responses[:-1]+[TimeoutError('unknown')]): state=w.create(self.body)
        self.assertEqual(state['phase'],'needs-inspection');self.assertEqual(state['failedPhase'],'submitting')
        with patch.object(w,'api') as api:
            w.create(self.body);w.refresh(JOB);api.assert_not_called()
    def test_route_checks_project_scene_prompt_orientation_provider(self):
        self.create()
        scene=dict(id=SCENE,_project_id=PROJECT,video_id=VIDEO,image_prompt=self.body['prompt'],character_names=[])
        self.assertEqual(w.guard_image(scene,'HORIZONTAL','flow'),'BELUGA')
        for fields in [dict(_project_id=VIDEO),dict(video_id=PROJECT),dict(image_prompt='changed'),dict(parent_scene_id=MEDIA),dict(character_names=['someone'])]:
            with self.assertRaises(ValueError):w.guard_image(dict(scene,**fields),'HORIZONTAL','flow')
        for orientation,provider in [('VERTICAL','flow'),('HORIZONTAL','assistant')]:
            with self.assertRaises(ValueError):w.guard_image(scene,orientation,provider)
        self.assertIsNone(w.binding_for('legacy-not-uuid'))
    def test_foreign_and_retried_receipts_pause(self):
        for fields in [dict(scene_id=MEDIA),dict(video_id=PROJECT),dict(project_id=VIDEO),dict(type='GENERATE_VIDEO'),dict(orientation='VERTICAL'),dict(provider='assistant'),dict(retry_count=1)]:
            self.create()
            with patch.object(w,'api',return_value=dict(self.receipt,**fields)):
                self.assertEqual(w.refresh(JOB)['phase'],'needs-inspection')
            state=w.read(JOB);w.save(state,'submitted')
    def test_completed_media_hash_and_duplicate_read(self):
        self.create(); raw=b'\x89PNG\r\n\x1a\nexample'
        def download(args,**kwargs):
            Path(args[args.index('--output')+1]).write_bytes(raw)
            class Result:returncode=0
            return Result()
        with patch.object(w,'api',side_effect=[self.receipt,dict(id=SCENE,video_id=VIDEO,horizontal_image_media_id=MEDIA,horizontal_image_url='https://example.org/img')]),patch.object(w.subprocess,'run',side_effect=download):
            state=w.refresh(JOB)
        self.assertEqual(state['sha256'],hashlib.sha256(raw).hexdigest())
        with patch.object(w,'api') as api:
            self.assertEqual(w.refresh(JOB),state);api.assert_not_called()
        (w.directory(JOB)/'image.bin').write_bytes(b'changed')
        with self.assertRaises(ValueError):w.refresh(JOB)
    def test_worker_failure_has_no_retry(self):
        import asyncio
        from agent.worker import processor
        self.create()
        with patch.object(processor.crud,'update_request',new_callable=AsyncMock) as update,patch.object(processor,'_recover_entity_not_found',new_callable=AsyncMock) as recover:
            asyncio.run(processor._handle_failure(REQUEST,dict(scene_id=SCENE),dict(error='timeout')))
            self.assertEqual(update.call_args.kwargs['status'],'FAILED');recover.assert_not_called()

    def test_startup_does_not_replay_unknown_paid_submission(self):
        import asyncio
        from agent.worker import processor
        self.create()
        stale=[dict(id=REQUEST,scene_id=SCENE,type='GENERATE_IMAGE'),dict(id='legacy',scene_id='unbound',type='GENERATE_IMAGE')]
        with patch.object(processor.crud,'list_requests',new_callable=AsyncMock,return_value=stale),patch.object(processor.crud,'update_request',new_callable=AsyncMock) as update:
            asyncio.run(processor.WorkerController()._cleanup_stale_processing())
        calls=update.call_args_list
        self.assertEqual(calls[0].args,(REQUEST,));self.assertEqual(calls[0].kwargs['status'],'FAILED')
        self.assertIn('inspect original receipt',calls[0].kwargs['error_message'])
        self.assertEqual(calls[1].kwargs['status'],'PENDING')

if __name__=='__main__':unittest.main()
