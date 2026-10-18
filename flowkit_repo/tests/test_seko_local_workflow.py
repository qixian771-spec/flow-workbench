import asyncio
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from agent.services import seko_local_workflow as w

JOB='2b063465-a2e7-4b6a-b8f8-cad0f23c6e41'
SCENE='6164f76f-a2e7-4b6a-b8f8-cad0f23c6e41'
MEDIA='80dbf33e-a2e7-4b6a-b8f8-cad0f23c6e41'
PLAN=dict(title='雨后茶馆',synopsis='雨滴落下',art_direction='静谧',image_prompt='Rain falls outside an empty tea house.',video_prompt='0-3s: Rain. 3-6s: Steam. 6-8s: Hold.',dialogue='')


class LocalTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=patch.object(w,'ROOT',Path(self.temp.name));self.root.start()
        self.addCleanup(self.root.stop);self.addCleanup(self.temp.cleanup)
        self.body={'workflow':w.WORKFLOW,'jobId':JOB,'canvasId':'123','storyId':'456',
                   'flowProject':MEDIA,'prompt':'虚构故事，雨后空茶馆，桌上蓝伞。'}
        self.responses=[{'extension_connected':True},{'video_model_family':'omni_flash'},
                        {'id':MEDIA},{'id':SCENE},[{'id':MEDIA,'scene_id':SCENE,'provider':'flow'}]]

    def create(self):
        with patch.object(w,'api',side_effect=self.responses),patch.object(w,'text_call',return_value=PLAN):
            return w.create(self.body)

    def backfill_state(self):
        state=self.create();state.update(sha256='a'*64,mediaId=MEDIA,size=4,upload={'path':'STS/test.png'})
        return w.save(state,'creating-node')

    def receipt(self,state):
        r={k:state[k] for k in ('jobId','stepId','requestId','mediaId','sha256','canvasId','storyId')}
        return dict(r,nodeId='789',nodeGenId='790',nodeStatus='GENERATING_COMPLETED',
                    readbackSha256='a'*64,filePath='STS/test.png')

    def test_text_route_requires_explicit_fixed_configuration(self):
        directory=Path(self.temp.name)
        with patch.object(w.subprocess,'run') as run:
            with self.assertRaises(ValueError):w.text_call(directory,'test','prompt',w.PLAN_SCHEMA)
            (directory/'config.json').write_text(json.dumps({'provider':'codex-cli','model':'wrong','codex_binary':'/bin/echo'}))
            with self.assertRaises(ValueError):w.text_call(directory,'test','prompt',w.PLAN_SCHEMA)
            run.assert_not_called()

    def test_duplicate_input_and_restart_never_resubmit(self):
        first=self.create()
        with patch.object(w,'api') as api,patch.object(w,'text_call') as text:
            self.assertEqual(w.create(self.body),first)
            other=dict(self.body,jobId='9711c802-a2e7-4b6a-b8f8-cad0f23c6e41')
            self.assertEqual(w.create(other)['jobId'],JOB)
            api.assert_not_called();text.assert_not_called()

    def test_same_job_different_prompt_rejected(self):
        self.create()
        with self.assertRaises(ValueError):w.create(dict(self.body,prompt='different'))

    def test_unknown_batch_write_stops_without_replay(self):
        with patch.object(w,'api',side_effect=self.responses[:-1]+[TimeoutError('unknown')]),patch.object(w,'text_call',return_value=PLAN):
            state=w.create(self.body)
        self.assertEqual(state['phase'],'needs-inspection')
        self.assertEqual(state['failedPhase'],'submitting')
        with patch.object(w,'api') as api:
            w.create(self.body);w.collect(JOB);api.assert_not_called()

    def test_text_failure_never_submits_media(self):
        with patch.object(w,'api',side_effect=self.responses[:2]) as api,patch.object(w,'text_call',side_effect=ValueError('failed')):
            state=w.create(self.body)
        self.assertEqual(state['phase'],'needs-inspection');self.assertEqual(api.call_count,2)

    def test_fixed_route_rejects_changed_provider_model_input(self):
        self.create();scene={'id':SCENE,'_project_id':MEDIA,'prompt':PLAN['image_prompt']}
        self.assertEqual(w.guard_scene(scene,'HORIZONTAL','flow'),'BELUGA')
        styled=dict(scene,prompt='Style prefix '+scene['prompt'],image_prompt=scene['prompt'])
        self.assertEqual(w.guard_scene(styled,'HORIZONTAL','flow'),'BELUGA')
        with self.assertRaises(ValueError):w.guard_scene(dict(styled,image_prompt='changed'),'HORIZONTAL','flow')
        for s,o,p in [(scene,'VERTICAL','flow'),(scene,'HORIZONTAL','assistant'),
                      (dict(scene,prompt='changed'),'HORIZONTAL','flow')]:
            with self.assertRaises(ValueError):w.guard_scene(s,o,p)

    def test_other_workflows_are_not_bound_by_local_contract(self):
        self.assertIsNone(w.binding_for('existing-test-scene'))

    def test_invalid_backfills_cannot_complete_or_advance(self):
        state=self.backfill_state();receipt=self.receipt(state)
        for field in ('jobId','stepId','requestId','mediaId','sha256','canvasId','storyId','readbackSha256','nodeStatus','filePath','nodeGenId'):
            bad=dict(receipt);bad[field]='wrong'
            with self.subTest(field=field),self.assertRaises(ValueError):w.validate_receipt(state,bad)
        with self.assertRaises(ValueError):w.validate_receipt(state,{'nodeId':'789'})
        with patch.object(w,'text_call') as call:
            with self.assertRaises(ValueError):w.checkpoint(JOB,{'expectedPhase':'creating-node','stepId':w.STEP,'phase':'complete'})
            call.assert_not_called()

    def test_same_run_continues_after_verified_receipt_and_replay_is_idempotent(self):
        state=self.backfill_state();body={'expectedPhase':'creating-node','stepId':w.STEP,'phase':'backfilled','receipt':self.receipt(state)}
        result={'run_id':JOB,'consumed_node_id':'789','consumed_media_id':MEDIA,
                'next_step':'video_ready_gate','video_prompt':PLAN['video_prompt']}
        with patch.object(w,'text_call',return_value=result) as call:
            after=w.checkpoint(JOB,body);again=w.checkpoint(JOB,body)
        self.assertEqual(after,again);self.assertEqual(call.call_count,1)
        self.assertEqual(after['phase'],'complete');self.assertFalse(after['nextRoute']['dispatched'])
        self.assertIn('789',call.call_args.args[2]);self.assertIn(MEDIA,call.call_args.args[2])

    def test_wrong_downstream_identity_holds_run(self):
        state=self.backfill_state()
        result={'run_id':'wrong','consumed_node_id':'789','consumed_media_id':MEDIA,'next_step':'video_ready_gate','video_prompt':'x'}
        with patch.object(w,'text_call',return_value=result):
            after=w.checkpoint(JOB,{'expectedPhase':'creating-node','stepId':w.STEP,'phase':'backfilled','receipt':self.receipt(state)})
        self.assertEqual(after['phase'],'needs-inspection')

    def test_local_failure_does_not_enter_worker_retry_or_recovery(self):
        self.create()
        from agent.worker import processor
        with patch.object(processor.crud,'update_request',new_callable=AsyncMock) as update,\
             patch.object(processor,'_recover_entity_not_found',new_callable=AsyncMock) as recover:
            asyncio.run(processor._handle_failure(MEDIA,{'scene_id':SCENE},{'error':'entity not found'}))
        recover.assert_not_called();self.assertEqual(update.call_args.kwargs['status'],'FAILED')

    def test_png_jpeg_headers_and_reject_nonimage(self):
        png=b'\x89PNG\r\n\x1a\n'+b'\x00'*8+(1376).to_bytes(4,'big')+(768).to_bytes(4,'big')
        jpeg=b'\xff\xd8\xff\xc0\x00\x08\x08'+(768).to_bytes(2,'big')+(1376).to_bytes(2,'big')+b'\x01'
        self.assertEqual(w.image_metadata(png),('image/png',1376,768))
        self.assertEqual(w.image_metadata(jpeg),('image/jpeg',1376,768))
        for bad in [b'html',b'\xff\xd8',jpeg[:8]]:
            with self.assertRaises(ValueError):w.image_metadata(bad)

    def test_explicit_collection_recovery_never_resubmits_generation(self):
        state=self.create();w.save(state,'needs-inspection',failedPhase='submitted',error='format')
        receipt={'status':'COMPLETED','media_id':MEDIA,'scene_id':SCENE,'provider':'flow','retry_count':0}
        with patch.object(w,'api',return_value=receipt) as api:
            recovered=w.recheck_completed_media(JOB)
        self.assertEqual(recovered['phase'],'submitted')
        self.assertEqual(api.call_count,1)
        self.assertEqual(api.call_args.args,('/api/requests/'+MEDIA,))
        self.assertEqual(recovered['inspections'][0]['error'],'format')
        w.save(recovered,'needs-inspection',failedPhase='submitted',error='format')
        with patch.object(w,'api',return_value=dict(receipt,status='FAILED')):
            with self.assertRaises(ValueError):w.recheck_completed_media(JOB)

    def test_source_and_text_contract(self):
        self.assertEqual(w.source_identity()['commit'],'f20eeb886c10cdd04e6f3bfef40a563bc9bd8628')
        self.assertEqual(w.TEXT_MODEL,'gpt-6.1-sol')
        with self.assertRaises(ValueError):w.validate_text({'image_prompt':'x'},w.PLAN_SCHEMA)
        with self.assertRaises(ValueError):w.job_dir('../../escape')

    def test_strict_flow_route_stops_transient_error_and_disables_profile_switch(self):
        from agent.services.flow_client import FlowClient
        from agent.services import flow_batch as fb
        client=FlowClient()
        with patch.object(client,'_batch_payload',new_callable=AsyncMock,side_effect=fb.RpcError(fb.RPC_GEN_IMAGE,[8])) as payload:
            result=asyncio.run(client.generate_images('rain',MEDIA,image_model='BELUGA',strict_route=True))
        self.assertEqual(payload.await_count,1)
        self.assertFalse(payload.call_args.kwargs['allow_failover'])
        self.assertNotEqual(result.get('status'),200)

    def test_strict_send_does_not_try_second_connected_profile(self):
        from agent.services.flow_client import FlowClient
        from unittest.mock import Mock
        client=FlowClient();first=Mock();second=Mock()
        async def respond(message):
            ident=json.loads(message)['id']
            client._pending[ident].set_result({'error':'NO_FLOW_TAB'})
        first.send=AsyncMock(side_effect=respond);second.send=AsyncMock()
        client._extensions={first:{},second:{}};client._extension_ws=first
        result=asyncio.run(client._send('batch_rpc',{},allow_failover=False))
        self.assertEqual(result,{'error':'NO_FLOW_TAB'})
        first.send.assert_awaited_once();second.send.assert_not_awaited()

    def test_unbound_flow_image_keeps_existing_call_contract(self):
        from agent.sdk.services.flow_provider import FlowProvider
        from types import SimpleNamespace
        client=SimpleNamespace(generate_images=AsyncMock(return_value={'ok':True}))
        asyncio.run(FlowProvider(client)._run_image(SimpleNamespace(extra={},prompt='rain')))
        self.assertNotIn('strict_route',client.generate_images.call_args.kwargs)
        self.assertNotIn('image_model',client.generate_images.call_args.kwargs)

    def test_strict_transport_reaches_send(self):
        from agent.services.flow_client import FlowClient
        from agent.services import flow_batch as fb
        client=FlowClient()
        with patch.object(client,'_send',new_callable=AsyncMock,return_value={'error':'stop'}) as send:
            with self.assertRaises(fb.FlowBatchError):
                asyncio.run(client._batch_payload(fb.RPC_GEN_IMAGE,'body',fb.CAPTCHA_IMAGE,allow_failover=False))
        self.assertEqual(send.await_count,1)
        self.assertFalse(send.call_args.kwargs['allow_failover'])

    def test_flow_provider_sends_explicit_model(self):
        from agent.sdk.services.flow_provider import FlowProvider
        from types import SimpleNamespace
        client=SimpleNamespace(generate_images=AsyncMock(return_value={'ok':True}))
        provider=FlowProvider(client)
        job=SimpleNamespace(extra={'image_model':'BELUGA'},prompt='rain')
        asyncio.run(provider._run_image(job))
        self.assertEqual(client.generate_images.call_args.kwargs['image_model'],'BELUGA')
        self.assertTrue(client.generate_images.call_args.kwargs['strict_route'])


if __name__=='__main__':unittest.main()
