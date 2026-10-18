import copy
import json
import subprocess
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from seko_flow_job import validate_capture, collect


class CaptureContractTest(unittest.TestCase):
    def setUp(self):
        self.capture={'canvasId':'123','referenceNodeId':'456','jobs':[{
            'jobId':'job','state':'captured','actualProvider':'flow','actualModelFamily':'omni_flash',
            'nativeRoute':'seko-canvas/v1/canvas-node/gen-video','nativeRequest':{
                'canvasId':'123','firstFrameNodeId':'456','lastFrameNodeId':'',
                'selectedVideoDuration':8,'visionRatioId':1,'resolutionType':1,
                'videoPrompt':'action','processedPrompt':'action'}}]}

    def test_accepts_exact_native_contract(self):
        self.assertEqual(validate_capture(self.capture,'job')['jobId'],'job')

    def test_rejects_other_ratio_resolution_duration_or_reference(self):
        for field,value in [('visionRatioId',2),('resolutionType',2),('selectedVideoDuration',5),
                            ('firstFrameNodeId','789'),('canvasId','789'),('lastFrameNodeId','789'),
                            ('refNodeIds',['789']),('videoPrompt',''),('processedPrompt','changed')]:
            with self.subTest(field=field):
                capture=copy.deepcopy(self.capture);capture['jobs'][0]['nativeRequest'][field]=value
                with self.assertRaises(ValueError): validate_capture(capture,'job')

    def test_rejects_processed_or_native_provider_job(self):
        for field,value in [('state','submitted'),('actualProvider','seko'),('actualModelFamily','other'),
                            ('nativeRoute','different')]:
            capture=copy.deepcopy(self.capture);capture['jobs'][0][field]=value
            with self.assertRaises(ValueError): validate_capture(capture,'job')

    def test_rejects_missing_and_duplicate_job(self):
        with self.assertRaises(ValueError): validate_capture(self.capture,'missing')
        self.capture['jobs'].append(copy.deepcopy(self.capture['jobs'][0]))
        with self.assertRaises(ValueError): validate_capture(self.capture,'job')


class DownloadBoundaryTest(unittest.TestCase):
    def test_failed_download_preserves_submitted_state_and_redacts_signed_url(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'flow.json'
            state={'phase':'submitted','request_id':'request','scene_id':'scene'}
            path.write_text(json.dumps(state))
            responses=[{'status':'COMPLETED'},{'horizontal_video_status':'COMPLETED',
                'horizontal_video_media_id':'24efdcc2-dfd8-48c2-940d-c17bc03845d3',
                'horizontal_video_url':'https://example.com/media?secret=PRIVATE'}]
            with patch('seko_flow_job.api',side_effect=responses), patch('seko_flow_job.subprocess.run',
                side_effect=subprocess.CalledProcessError(28,['curl','PRIVATE'])):
                with self.assertRaisesRegex(ValueError,'Only collect may be retried') as raised:
                    collect(SimpleNamespace(),path)
            self.assertNotIn('PRIVATE',str(raised.exception))
            self.assertEqual(json.loads(path.read_text()),state)
            self.assertFalse(path.with_suffix('.mp4').exists())

    def test_downloaded_receipt_does_not_regenerate_or_redownload(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'flow.json'
            path.write_text(json.dumps({'phase':'downloaded','media_id':'id','media_sha256':'hash','media_path':'path'}))
            with patch('seko_flow_job.api') as api, patch('seko_flow_job.subprocess.run') as process:
                self.assertEqual(collect(SimpleNamespace(),path)['phase'],'downloaded')
                api.assert_not_called();process.assert_not_called()

if __name__=='__main__': unittest.main()
