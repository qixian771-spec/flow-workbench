import asyncio
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from seko_flow_job import submit
from seko_prompt_compare import submit_comparison
from agent.services.prompt_adaptation import compile_seko_omni, finalize_omni_prompt, record_omni_request, digest, EXPERIMENTAL_PROFILE
from agent.sdk.services.operations import _build_video_prompt

SOURCE = ('0-3s: Hold the front-facing close-up; the man lowers his eyes, lips closed. '
          '3-6s: He lifts his gaze toward his companion just beside the camera, with a reluctant small nod. '
          '6-8s: Hold a thoughtful expression. Locked camera, natural blinking, no talking, no music, no subtitles.')
MEDIA = '85966991-65ac-490e-a653-cf16b9a312cf'
PROJECT = {'video_model_family': 'omni_flash', 'allow_voice': False, 'allow_music': False}


def native():
    return {'canvasId': '123', 'firstFrameNodeId': '456', 'lastFrameNodeId': '',
            'selectedVideoDuration': 8, 'visionRatioId': 1, 'resolutionType': 1,
            'videoPrompt': SOURCE, 'processedPrompt': SOURCE, 'videoModel': 'seedance-source'}


class AdaptationTest(unittest.TestCase):
    def test_preserves_every_source_character_and_reference(self):
        r = compile_seko_omni(native(), PROJECT, MEDIA)
        self.assertTrue(r['flow_prompt'].endswith(SOURCE))
        self.assertEqual(r['source_prompt'], SOURCE)
        self.assertEqual(r['reference_media_ids'], [MEDIA])
        self.assertEqual(r['source_sha256'], digest(SOURCE))
        self.assertIn('no cuts', r['flow_prompt'])
        self.assertNotIn('closed during every segment', r['flow_prompt'])
        self.assertNotIn('Negative:', r['final_prompt'])

    def test_unsupported_intents_stop_instead_of_dropping_requirements(self):
        for replacement in [SOURCE.replace('no talking', 'says "明天一早的车。"'),
                            SOURCE.replace('Locked camera', 'Slow dolly'),
                            SOURCE.replace('3-6s', '3-7s'), SOURCE + ' Cut to her face.',
                            SOURCE.replace('no music', 'gentle music')]:
            b = native(); b.update(videoPrompt=replacement, processedPrompt=replacement)
            with self.subTest(prompt=replacement), self.assertRaises(ValueError):
                compile_seko_omni(b, PROJECT, MEDIA)

    def test_experimental_rule_requires_explicit_selection_and_source_support(self):
        r = compile_seko_omni(native(), PROJECT, MEDIA, profile=EXPERIMENTAL_PROFILE)
        self.assertIn('closed during every segment', r['flow_prompt'])
        b = native(); b.update(videoPrompt=SOURCE.replace('lips closed', 'soft expression'),
                               processedPrompt=SOURCE.replace('lips closed', 'soft expression'))
        with self.assertRaises(ValueError): compile_seko_omni(b, PROJECT, MEDIA, profile=EXPERIMENTAL_PROFILE)
        with self.assertRaises(ValueError): compile_seko_omni(native(), PROJECT, MEDIA, profile='unknown')

    def test_unsupported_settings_and_mismatched_source_stop(self):
        for key, value in [('lastFrameNodeId', '789'), ('refNodeIds', ['789']),
                           ('selectedVideoDuration', 10), ('resolutionType', 2),
                           ('visionRatioId', 2), ('processedPrompt', 'changed')]:
            b = native(); b[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                compile_seko_omni(b, PROJECT, MEDIA)
        for key, value in [('allow_voice', True), ('allow_music', True), ('video_model_family', 'veo')]:
            p = dict(PROJECT); p[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                compile_seko_omni(native(), p, MEDIA)

    def test_final_builder_uses_same_compiler_without_veo_tail(self):
        r = compile_seko_omni(native(), PROJECT, MEDIA)
        with patch('agent.sdk.services.operations.crud.get_project', new=AsyncMock(return_value=PROJECT)):
            actual = asyncio.run(_build_video_prompt(r['flow_prompt'], {}, 'project'))
        self.assertEqual(actual, r['final_prompt'])
        with self.assertRaises(ValueError):
            finalize_omni_prompt('陈舟说：“明天一早的车。”', PROJECT)

    def test_record_rejects_changed_request_and_has_no_url(self):
        with tempfile.TemporaryDirectory() as d:
            record_omni_request(d, 'request', {'prompt': SOURCE, 'start_image_media_id': MEDIA})
            record_omni_request(d, 'request', {'prompt': SOURCE, 'start_image_media_id': MEDIA})
            with self.assertRaises(ValueError):
                record_omni_request(d, 'request', {'prompt': 'changed'})
            record = json.loads(next(Path(d).rglob('*.json')).read_text())
            self.assertEqual(record['prompt_sha256'], digest(SOURCE))

    def test_resident_submit_persists_source_and_sends_compiled_prompt(self):
        with tempfile.TemporaryDirectory() as d:
            cap = Path(d) / 'capture.json'; state = Path(d) / 'state.json'
            job = {'jobId':'job', 'state':'captured', 'actualProvider':'flow', 'actualModelFamily':'omni_flash',
                   'nativeRoute':'seko-canvas/v1/canvas-node/gen-video', 'nativeRequest':native()}
            cap.write_text(json.dumps({'canvasId':'123','referenceNodeId':'456','jobs':[job]}))
            calls = []
            def fake_api(base, route, body=None, method=None):
                calls.append((route, body))
                if route == '/health': return {'extension_connected':True}
                if route == '/api/projects/project': return PROJECT
                if route == '/api/scenes/ref': return {'video_id':'ref-video','horizontal_image_status':'COMPLETED',
                    'horizontal_image_media_id': MEDIA, 'horizontal_image_url':'https://example.org/ref'}
                if route == '/api/videos/ref-video': return {'project_id':'project'}
                if route == '/api/videos': return {'id':'video'}
                if route == '/api/scenes': return {'id':'scene'}
                if route == '/api/scenes/scene': return {}
                if route == '/api/requests/batch': return [{'id':'request'}]
                raise AssertionError(route)
            args = SimpleNamespace(capture=str(cap), job_id='job', flow_project='project', reference_scene='ref')
            with patch('seko_flow_job.api', side_effect=fake_api):
                result = submit(args, state)
                with self.assertRaises(FileExistsError): submit(args, state)
            submitted = next(b for r,b in calls if r == '/api/scenes')
            self.assertEqual(submitted['prompt'], SOURCE)
            self.assertEqual(submitted['video_prompt'], result['adaptation']['flow_prompt'])
            self.assertEqual(json.loads(state.read_text())['prompt'], SOURCE)
            self.assertEqual(sum(r == '/api/requests/batch' for r,b in calls), 1)

    def test_ab_is_one_batch_same_reference_and_cannot_be_repeated(self):
        with tempfile.TemporaryDirectory() as d:
            state = Path(d) / 'comparison.json'
            adaptation = compile_seko_omni(native(), PROJECT, MEDIA)
            prepared = ({'nativeRequest': native()}, PROJECT, {'horizontal_image_url':'https://example.org/ref'}, MEDIA, adaptation)
            calls = []; scenes = []
            def fake_api(base, route, body=None, method=None):
                calls.append((route, body))
                if route == '/api/videos': return {'id':'video'}
                if route == '/api/scenes':
                    scenes.append(body); return {'id':'scene-' + str(len(scenes))}
                if route.startswith('/api/scenes/'): return {}
                if route == '/api/requests/batch':
                    return [{'id':'req-' + str(i), 'scene_id':r['scene_id']} for i,r in enumerate(body['requests'])]
                raise AssertionError(route)
            with patch('seko_prompt_compare.prepare', return_value=prepared), patch('seko_prompt_compare.api', side_effect=fake_api):
                submit_comparison(SimpleNamespace(flow_project='project'), state)
                with self.assertRaises(FileExistsError): submit_comparison(SimpleNamespace(flow_project='project'), state)
            self.assertEqual(len([r for r,b in calls if r == '/api/requests/batch']), 1)
            self.assertEqual(scenes[0]['video_prompt'], SOURCE)
            self.assertEqual(scenes[1]['video_prompt'], adaptation['flow_prompt'])
            bindings = [b for r,b in calls if r.startswith('/api/scenes/')]
            self.assertEqual(bindings[0], bindings[1])

    def test_veo_final_text_is_unchanged(self):
        with patch('agent.sdk.services.operations.crud.get_project', new=AsyncMock(return_value={'video_model_family':'veo'})):
            prompt = asyncio.run(_build_video_prompt('The man nods.', {}, 'project'))
        self.assertIn('Audio: natural ambient sounds only', prompt)
        self.assertIn('Negative:', prompt)

    def test_existing_descriptive_voice_context_is_retained_for_omni(self):
        project = dict(PROJECT, allow_voice=True)
        with patch('agent.sdk.services.operations.crud.get_project', new=AsyncMock(return_value=project)), \
             patch('agent.sdk.services.operations.crud.get_project_characters', new=AsyncMock(return_value=[
                 {'name':'Chen', 'voice_description':'A soft measured voice'}])):
            result = asyncio.run(_build_video_prompt('Chen says "明天一早的车。"', {'character_names':['Chen']}, 'project'))
        self.assertIn('明天一早的车。', result)
        self.assertIn('A soft measured voice', result)
        self.assertNotIn('Negative:', result)


if __name__ == '__main__': unittest.main()
