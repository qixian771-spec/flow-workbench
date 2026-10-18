import copy
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from seko_probe import audit, media_identity


class SekoProbeTest(unittest.TestCase):
    def setUp(self):
        import json
        path = ROOT / 'docs/benchmarks/seko-20261013'
        self.before = json.loads((path / 'a.json').read_text())
        self.after = json.loads((path / 'b-both-shots.json').read_text())
        self.stale = json.loads((path / 'node-update-probe.json').read_text())

    def test_real_replacement_passes(self):
        self.assertTrue(all(c['passed'] for c in audit(self.before, self.after)))

    def test_real_stale_shot_fails(self):
        c = {c['check']: c['passed'] for c in audit(self.before, self.stale)}
        self.assertFalse(c['all_affected_shots_updated'])
        self.assertFalse(c['no_stale_shot_media'])

    def test_trim_change_fails(self):
        self.after['shots'][0]['shotVideoStartTime'] = 1
        self.assertFalse(all(c['passed'] for c in audit(self.before, self.after)))

    def test_missing_shot_fails(self):
        self.after['shots'].pop()
        self.assertFalse(all(c['passed'] for c in audit(self.before, self.after)))

    def test_duplicate_ids_rejected(self):
        self.after['shots'].append(copy.deepcopy(self.after['shots'][0]))
        with self.assertRaises(ValueError):
            audit(self.before, self.after)

    def test_signed_query_rotation_is_not_replacement(self):
        self.assertEqual(media_identity('https://example.com/a?token=1'),
                         media_identity('https://example.com/a?token=2'))

    def test_empty_media_rejected(self):
        with self.assertRaises(ValueError):
            media_identity('')


if __name__ == '__main__':
    unittest.main()
