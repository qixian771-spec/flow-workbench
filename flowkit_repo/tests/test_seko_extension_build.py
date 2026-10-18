import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_seko_extension_build import REQUIRED, inspect_build, require_build


class LoadedBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.extension_id = 'a' * 32
        manifest = {'version': '0.5.2', 'content_scripts': [
            {'js': list(REQUIRED), 'matches': ['https://seko.sensetime.com/*']}],
            'permissions': ['storage']}
        (self.root / 'manifest.json').write_text(json.dumps(manifest))
        self.observed = {'extension_id': self.extension_id, 'manifest': manifest, 'scripts': {}}
        for name in REQUIRED:
            body = ('// 确认实际字节 ' + name + '\n').encode()
            (self.root / name).write_bytes(body)
            self.observed['scripts'][name] = {
                'url': f'chrome-extension://{self.extension_id}/{name}',
                'sha256': hashlib.sha256(body).hexdigest()}

    def verify(self, value):
        return require_build(value, self.root, self.extension_id)

    def test_exact_observed_build_passes(self):
        self.assertTrue(self.verify(self.observed)['matches'])

    def test_same_version_old_manifest_fails(self):
        value = copy.deepcopy(self.observed)
        value['manifest']['content_scripts'][0]['js'] = ['seko_page.js']
        report = inspect_build(value, self.root, self.extension_id)
        self.assertEqual(report['expected_version'], report['actual_version'])
        self.assertFalse(report['matches'])
        with self.assertRaisesRegex(ValueError, 'manifest.content_scripts'):
            self.verify(value)

    def test_same_url_stale_script_fails(self):
        self.observed['scripts']['seko_page.js']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'seko_page.js.sha256'):
            self.verify(self.observed)

    def test_missing_bundle_fails(self):
        del self.observed['scripts']['seko_local_bundle.js']
        with self.assertRaisesRegex(ValueError, 'seko_local_bundle.js'):
            self.verify(self.observed)

    def test_injected_copy_is_not_packaged_source(self):
        self.observed['scripts']['seko_local_bundle.js']['url'] = 'https://seko.sensetime.com/bundle.js'
        with self.assertRaisesRegex(ValueError, 'seko_local_bundle.js.url'):
            self.verify(self.observed)

    def test_different_extension_fails(self):
        self.observed['extension_id'] = 'b' * 32
        with self.assertRaisesRegex(ValueError, 'extension_id'):
            self.verify(self.observed)

    def test_permission_drift_fails(self):
        value = copy.deepcopy(self.observed)
        value['manifest']['permissions'].append('debugger')
        with self.assertRaisesRegex(ValueError, 'manifest.permissions'):
            self.verify(value)


if __name__ == '__main__':
    unittest.main()
