import asyncio
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace
from agent.services import seko_local_video as v
from agent.services import seko_local_workflow as w

JOB='eedacf2c-49c2-4b6f-9f02-652d60834930'
IMAGE='b587a425-a9dc-4759-921b-6c3eadba7e55'
SCENE='3306f96e-cea6-4acf-aa86-1bc5bdf6b387'
REQUEST='315a918c-3051-4da0-b814-5a2179a1d817'
VIDEO='6164f76f-a2e7-4b6a-b8f8-cad0f23c6e41'
PROMPT='0-3s: Match the first frame, gently push in. 3-6s: Steam and rain move. 6-8s: Settle. Silent, no speech, no music.'


class VideoTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=patch.object(w,'ROOT',Path(self.temp.name));self.root.start();self.addCleanup(self.root.stop)
        (w.ROOT/'config.json').write_text(json.dumps({'ffprobe':'/bin/echo','ffmpeg':'/bin/echo'}))
        w.job_dir(JOB).mkdir(parents=True)
        self.state={'jobId':JOB,'phase':'complete','history':[], 'stepId':w.STEP,'requestId':IMAGE,
            'mediaId':IMAGE,'sha256':'a'*64,'canvasId':'123','storyId':'456','sceneId':SCENE,
            'videoId':VIDEO,'flowProject':VIDEO,'upload':{'path':'STS/image.jpg'},
            'nextStep':{'next_step':'video_ready_gate','video_prompt':'Gentle push in over 8 seconds.'}}
        self.state['receipt']={k:self.state[k] for k in ('jobId','stepId','requestId','mediaId','sha256','canvasId','storyId')}
        self.state['receipt'].update(nodeId='789',nodeGenId='790',nodeStatus='GENERATING_COMPLETED',
            readbackSha256='a'*64,filePath='STS/image.jpg')
        w.save(self.state)
        self.plan={'run_id':JOB,'source_image_media_id':IMAGE,'source_image_node_id':'789','prompt':PROMPT}
        self.project={'video_model_family':'omni_flash','allow_voice':False,'allow_music':False}
        self.scene={'id':SCENE,'_project_id':VIDEO,'horizontal_image_media_id':IMAGE,
            'horizontal_image_status':'COMPLETED','video_prompt':PROMPT,'duration':8}
        self.responses=[self.project,{'extension_connected':True},self.scene,{},
            [{'id':REQUEST,'scene_id':SCENE,'provider':'flow'}]]
        index=w.index_path(SCENE);index.parent.mkdir(parents=True);index.write_text(json.dumps({'jobId':JOB,'stepId':w.STEP}))

    def start(self):
        with patch.object(w,'api',side_effect=self.responses),patch.object(w,'text_call',return_value=self.plan):
            return v.start(JOB,v.input_contract(self.state))

    def filled(self):
        state=self.start();state['video'].update(mediaId=VIDEO,sha256='b'*64,upload={'path':'STS/video.mp4'})
        v.save(state,'creating-node');return state

    def receipt(self,state):
        video=state['video'];r={k:state[k] for k in ('jobId','canvasId','storyId')}
        r.update({k:video[k] for k in ('stepId','requestId','mediaId','sha256','sourceImageMediaId','sourceImageNodeId')})
        r.update(nodeId='900',nodeGenId='901',nodeStatus='GENERATING_COMPLETED',nodeType='VIDEO',
            filePath='STS/video.mp4',readbackSha256='b'*64,duration=8,width=1280,height=720)
        return r

    def test_start_uses_same_scene_and_run_and_duplicate_does_not_generate(self):
        with patch.object(w,'api',side_effect=self.responses) as api,patch.object(w,'text_call',return_value=self.plan) as text:
            first=v.start(JOB,v.input_contract(self.state));second=v.start(JOB,v.input_contract(self.state))
        self.assertEqual(first,second);self.assertEqual(text.call_count,1);self.assertEqual(api.call_count,5)
        submit=api.call_args.args[1]['requests'][0]
        self.assertEqual(submit['scene_id'],SCENE);self.assertEqual(submit['type'],'GENERATE_VIDEO')
        self.assertEqual(first['mediaId'],IMAGE);self.assertEqual(first['video']['route'],v.ROUTE)
        self.assertEqual(api.call_args_list[3].kwargs,{'method':'PATCH'})

    def test_wrong_input_identity_stops_before_model_or_media(self):
        for key in ('imageMediaId','imageNodeId','sourcePromptHash','stepId'):
            body=v.input_contract(self.state);body[key]='wrong'
            with patch.object(w,'api') as api,self.assertRaises(ValueError):v.start(JOB,body)
            api.assert_not_called()

    def test_unknown_submission_is_not_replayed(self):
        with patch.object(w,'api',side_effect=self.responses[:-1]+[TimeoutError('unknown')]),patch.object(w,'text_call',return_value=self.plan):
            result=v.start(JOB,v.input_contract(self.state))
        self.assertEqual(result['video']['phase'],'needs-inspection')
        self.assertEqual(result['video']['failedPhase'],'submitting')
        with patch.object(w,'api') as api:
            v.start(JOB,v.input_contract(self.state));v.collect(JOB);api.assert_not_called()

    def test_changed_route_or_first_frame_rejected(self):
        self.start();self.assertEqual(v.guard(self.scene,'HORIZONTAL','flow',self.project),v.ROUTE)
        for scene,orient,provider,project in [
            (dict(self.scene,horizontal_image_media_id=VIDEO),'HORIZONTAL','flow',self.project),
            (dict(self.scene,duration=6),'HORIZONTAL','flow',self.project),
            (dict(self.scene,horizontal_end_scene_media_id=VIDEO),'HORIZONTAL','flow',self.project),
            (dict(self.scene,video_prompt='altered'),'HORIZONTAL','flow',self.project),
            (self.scene,'VERTICAL','flow',self.project),(self.scene,'HORIZONTAL','assistant',self.project),
            (self.scene,'HORIZONTAL','flow',dict(self.project,video_model_family='veo'))]:
            with self.assertRaises(ValueError):v.guard(scene,orient,provider,project)
        self.assertIsNone(v.guard({'id':'legacy'},'HORIZONTAL','flow',{}))

    def test_prompt_execution_instructions_and_timing_are_rejected(self):
        for prompt in ['do not generate '+PROMPT,PROMPT.replace('3-6s:','3-7s:'),PROMPT.replace('silent','sound').replace('Silent','Sound')]:
            with self.assertRaises(ValueError):v.validate_plan(dict(self.plan,prompt=prompt),self.state)

    def test_actual_submit_model_and_operation_are_bound(self):
        self.start();response={'data':{'model':'abra_i2v_8s','duration_s':8,'resolution':'720p',
            'operations':[{'operation':{'name':VIDEO}}]}}
        v.record_submit(SCENE,REQUEST,response)
        self.assertEqual(w.read(JOB)['video']['submitReceipt']['operationId'],VIDEO)
        bad=copy.deepcopy(response);bad['data']['model']='veo'
        with self.assertRaises(ValueError):v.record_submit(SCENE,REQUEST,bad)

    def test_video_metadata_rejects_wrong_duration_or_resolution(self):
        good={'streams':[{'codec_type':'video','width':1280,'height':720}], 'format':{'duration':'8'}}
        v.validate_media(good)
        for bad in [dict(good,format={'duration':'6'}),dict(good,streams=[{'codec_type':'video','width':720,'height':1280}])]:
            with self.assertRaises(ValueError):v.validate_media(bad)

    def test_forged_video_receipt_does_not_advance(self):
        state=self.filled();r=self.receipt(state)
        for key in ('jobId','stepId','mediaId','requestId','sourceImageMediaId','sourceImageNodeId','sha256','nodeStatus','nodeType','filePath','readbackSha256'):
            bad=dict(r);bad[key]='wrong'
            with self.subTest(key=key),self.assertRaises(ValueError):v.validate_receipt(state,bad)
        with self.assertRaises(ValueError):v.validate_receipt(state,dict(r,nodeId='789'))
        with patch.object(w,'text_call') as text:
            with self.assertRaises(ValueError):v.checkpoint(JOB,{'stepId':v.STEP,'expectedPhase':'creating-node','phase':'complete'})
            text.assert_not_called()

    def test_same_run_video_continuation_and_idempotent_checkpoint(self):
        state=self.filled();r=self.receipt(state);body={'stepId':v.STEP,'expectedPhase':'creating-node','phase':'backfilled','receipt':r}
        result={'run_id':JOB,'consumed_video_media_id':VIDEO,'consumed_video_node_id':'900',
            'source_image_media_id':IMAGE,'next_step':'assembly_ready_gate','edit_plan':'Keep the entire 8s clip.'}
        with patch.object(w,'text_call',return_value=result) as text:
            final=v.checkpoint(JOB,body);again=v.checkpoint(JOB,body)
        self.assertEqual(final,again);self.assertEqual(text.call_count,1)
        self.assertEqual(final['currentGate'],'assembly_ready_gate')
        self.assertEqual(final['video']['editManifest']['clips'][0]['media_id'],VIDEO)
        self.assertFalse(final['video']['editManifest']['exported'])
        self.assertIn('900',text.call_args.args[2])

    def test_wrong_continuation_identity_stops(self):
        state=self.filled();result={'run_id':JOB,'consumed_video_media_id':IMAGE,'consumed_video_node_id':'900',
            'source_image_media_id':IMAGE,'next_step':'assembly_ready_gate','edit_plan':'Keep.'}
        with patch.object(w,'text_call',return_value=result):
            after=v.checkpoint(JOB,{'stepId':v.STEP,'expectedPhase':'creating-node','phase':'backfilled','receipt':self.receipt(state)})
        self.assertEqual(after['video']['phase'],'needs-inspection')

    def test_strict_omni_wire_route_disables_profile_switch(self):
        from agent.services import omni_flash as omni
        client=SimpleNamespace(_batch_project_id=lambda p:p,_batch_payload=AsyncMock(return_value=[]),_remember_operation=lambda *args:None)
        with patch.object(omni,'get_flow_client',return_value=client),patch.object(omni.fb,'read_operation',return_value=SimpleNamespace(operation_id=VIDEO)):
            result=asyncio.run(omni.generate_omni_flash_first_frame_video(IMAGE,PROMPT,VIDEO,
                duration_s=8,resolution='720p',aspect_ratio='VIDEO_ASPECT_RATIO_LANDSCAPE',strict_route=True))
        self.assertFalse(client._batch_payload.call_args.kwargs['allow_failover'])
        self.assertIn('abra_i2v_8s',client._batch_payload.call_args.args[1]);self.assertEqual(client._batch_payload.await_count,1)
        self.assertEqual(result['data']['model'],'abra_i2v_8s')
        with self.assertRaises(ValueError):asyncio.run(omni.generate_omni_flash_first_frame_video(IMAGE,PROMPT,VIDEO,duration_s=6,strict_route=True))


if __name__=='__main__':unittest.main()
