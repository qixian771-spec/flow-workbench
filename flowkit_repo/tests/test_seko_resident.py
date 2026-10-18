import asyncio
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException
from starlette.requests import Request
from types import SimpleNamespace
from agent.api import seko


class ResidentTest(unittest.TestCase):
    def setUp(self):
        self.cfg={'enabled':True,'projects':[{'canvasId':'123','storyId':'789','flowProject':'flow',
                  'references':{'456':{'sceneId':'scene'}}}]}
        self.body={'jobId':'f5a19810-70a4-4491-a8e7-87d949c00973','nativeRequest':{
            'canvasId':'123','firstFrameNodeId':'456','selectedVideoDuration':8,'visionRatioId':1,
            'resolutionType':1,'videoPrompt':'action','processedPrompt':'action'}}

    def test_explicit_mapping(self):
        self.assertEqual(seko.validate(self.body,self.cfg)[1]['sceneId'],'scene')
        for key,value in [('canvasId','1'),('firstFrameNodeId','2'),('selectedVideoDuration',5),
                          ('processedPrompt','changed'),('lastFrameNodeId','3')]:
            body=copy.deepcopy(self.body);body['nativeRequest'][key]=value
            with self.assertRaises(ValueError):seko.validate(body,self.cfg)

    def test_checkpoint_compare_and_set(self):
        state={'phase':'ready','history':[]}
        seko.transition(state,{'expectedPhase':'ready','phase':'uploading'})
        with self.assertRaises(ValueError):seko.transition(state,{'expectedPhase':'ready','phase':'uploading'})
        with self.assertRaises(ValueError):seko.transition(state,{'expectedPhase':'uploading','phase':'complete'})
        self.assertEqual(state['phase'],'uploading')

    def test_existing_extension_secret_required(self):
        for secret,ok in [('secret',True),('',False),('different',False)]:
            req=Request({'type':'http','headers':[(b'x-flowkit-seko',secret.encode())],
                         'app':SimpleNamespace(state=SimpleNamespace(seko_bridge_secret='secret'))})
            if ok:asyncio.run(seko.authorize(req))
            else:
                with self.assertRaises(HTTPException):asyncio.run(seko.authorize(req))

    def test_duplicate_after_restart_never_resubmits(self):
        async def exercise():
            first=await seko.create_job(self.body)
            second=await seko.create_job(self.body)
            self.assertEqual(first,second)
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(seko,'ROOT',Path(temp)),patch.object(seko,'config',return_value=self.cfg),\
                 patch.object(seko,'invoke',return_value={'phase':'submitted','request_id':'real'}) as call:
                asyncio.run(exercise());self.assertEqual(call.call_count,1)

    def test_unknown_submit_is_persisted_without_retry(self):
        async def exercise():
            first=await seko.create_job(self.body)
            self.assertEqual(first['phase'],'failed')
            self.assertEqual((await seko.create_job(self.body))['phase'],'failed')
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(seko,'ROOT',Path(temp)),patch.object(seko,'config',return_value=self.cfg),\
                 patch.object(seko,'invoke',side_effect=TimeoutError('unknown')) as call:
                asyncio.run(exercise());self.assertEqual(call.call_count,1)

    def test_double_click_with_new_uuid_reuses_active_request(self):
        async def exercise():
            first=await seko.create_job(self.body)
            body=copy.deepcopy(self.body);body['jobId']='e867dc9a-708b-4f84-9bd9-68f5dfd2580d'
            second=await seko.create_job(body)
            self.assertEqual(first['jobId'],second['jobId'])
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(seko,'ROOT',Path(temp)),patch.object(seko,'config',return_value=self.cfg),\
                 patch.object(seko,'invoke',return_value={'phase':'submitted'}) as call:
                asyncio.run(exercise());self.assertEqual(call.call_count,1)

    def test_uuid_path_cannot_escape(self):
        with self.assertRaises(ValueError):seko.job_dir('../../config')


if __name__=='__main__':unittest.main()
