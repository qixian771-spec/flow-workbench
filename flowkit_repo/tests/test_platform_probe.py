import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("platform_probe", Path(__file__).parents[1] / "scripts/platform_probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ReplacementAuditTest(unittest.TestCase):
    def setUp(self):
        self.assets_a = [{"id": "asset", "uri": "old"}]
        self.assets_b = [{"id": "asset", "uri": "new"}]
        self.before = {"id": "timeline", "duration_ms": 16000, "aspect_ratio": "16:9",
                       "source_uris": ["old"], "clips": [
                           {"id": str(i), "uri": "old", "start_ms": i * 8000,
                            "end_ms": (i + 1) * 8000, "trim_start_ms": 0,
                            "trim_end_ms": 8000, "volume": 1} for i in range(2)]}
        self.after = copy.deepcopy(self.before)
        self.after["source_uris"] = ["new"]
        for clip in self.after["clips"]:
            clip["uri"] = "new"

    def checks(self):
        return {c["check"]: c["passed"] for c in probe.audit_replacement(
            self.assets_a, self.assets_b, self.before, self.after, "asset")}

    def test_complete_replacement_passes(self):
        self.assertTrue(all(self.checks().values()))

    def test_canvas_only_change_fails(self):
        self.after = copy.deepcopy(self.before)
        self.assertFalse(self.checks()["affected_clips_updated"])
        self.assertFalse(self.checks()["no_stale_source_reference"])

    def test_one_stale_clip_fails(self):
        self.after["clips"][1]["uri"] = "old"
        self.assertFalse(self.checks()["affected_clips_updated"])

    def test_missing_clip_fails(self):
        self.after["clips"].pop()
        self.assertFalse(self.checks()["same_clip_ids"])

    def test_changed_timing_fails(self):
        self.after["clips"][0]["end_ms"] = 7900
        self.assertFalse(self.checks()["timing_and_audio_preserved"])

    def test_new_asset_instead_of_replacement_fails(self):
        self.assets_b[0]["id"] = "other"
        with self.assertRaises(KeyError):
            self.checks()

    def test_duplicate_ids_rejected(self):
        self.after["clips"][1]["id"] = "0"
        with self.assertRaises(ValueError):
            self.checks()

    def test_no_target_reference_rejected(self):
        self.assets_a[0]["uri"] = "unrelated"
        with self.assertRaises(ValueError):
            self.checks()

    def test_failed_provider_response_rejected(self):
        with self.assertRaises(ValueError):
            probe.normalize_assets({"ok": False}, "oiioii")
        with self.assertRaises(ValueError):
            probe.normalize_timeline({"code": "ERROR"}, "oiioii")

    def test_invalid_duration_rejected_before_decode(self):
        for duration in [0, -1, float("nan"), float("inf")]:
            with self.assertRaises(ValueError):
                probe.inspect_media("unused.mp4", duration, (1280, 720))

    def test_real_oiioii_snapshots_detect_both_stale_layers(self):
        root = Path(__file__).parents[1] / "docs/benchmarks/oiioii-replacement-20261013"
        before_assets = probe.normalize_assets(probe.load(root / "assets-before.json"), "oiioii")
        after_assets = probe.normalize_assets(probe.load(root / "assets-after.json"), "oiioii")
        before = probe.normalize_timeline(probe.load(root / "timeline-before.json"), "oiioii")
        for filename, clips_updated in [("timeline-stale.json", False), ("timeline-clips-fixed.json", True)]:
            after = probe.normalize_timeline(probe.load(root / filename), "oiioii")
            checks = {c["check"]: c["passed"] for c in probe.audit_replacement(
                before_assets, after_assets, before, after, "71fd09da-bdb1-45d1-a8b6-245093051112")}
            self.assertEqual(checks["affected_clips_updated"], clips_updated)
            self.assertFalse(checks["no_stale_source_reference"])

    def test_changed_volume_fails(self):
        self.after["clips"][1]["volume"] = 0
        self.assertFalse(self.checks()["timing_and_audio_preserved"])

    def test_unrelated_clip_cannot_change(self):
        clip = dict(self.before["clips"][0], id="unrelated", uri="other")
        self.before["clips"].append(clip)
        self.after["clips"].append(dict(clip, uri="new"))
        self.assertFalse(self.checks()["unaffected_clips_preserved"])

    def test_crop_shift_cannot_pass_as_same_duration(self):
        self.before["crop_start_ms"] = 0
        self.after["crop_start_ms"] = 1000
        self.assertFalse(self.checks()["duration_and_aspect_preserved"])


class LibTVSnapshotTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parents[1] / "docs/benchmarks/libtv-20261013"
        self.a = probe.load(self.root / "snapshot-a.json")
        self.b = probe.load(self.root / "snapshot-b.json")

    def audit(self, after):
        return {c["check"]: c["passed"] for c in probe.audit_replacement(
            probe.normalize_assets(self.a, "libtv"), probe.normalize_assets(after, "libtv"),
            probe.normalize_timeline(self.a, "libtv"), probe.normalize_timeline(after, "libtv"),
            "63c0c869-437f-4359-b18f-099c23588829")}

    def test_real_refreshed_snapshot_passes(self):
        self.assertTrue(all(self.audit(self.b).values()))

    def test_live_resolution_does_not_hide_stale_cache(self):
        checks = self.audit(probe.load(self.root / "snapshot-b-stale.json"))
        self.assertTrue(checks["affected_clips_updated"])
        self.assertFalse(checks["no_stale_source_reference"])

    def test_broken_source_binding_rejected(self):
        self.b["timeline"]["data"]["clipTimelineData"]["videoSourceNodeIds"] = []
        with self.assertRaises(ValueError):
            self.audit(self.b)

    def test_incomplete_cache_rejected(self):
        self.b["timeline"]["data"]["params"]["videoList"] = []
        with self.assertRaises(ValueError):
            self.audit(self.b)

    def test_multiple_source_outputs_rejected(self):
        self.b["nodes"][0]["data"]["url"].append("ambiguous")
        with self.assertRaises(ValueError):
            self.audit(self.b)

    def test_muted_track_not_reported_as_preserved(self):
        self.b["timeline"]["data"]["clipTimelineData"]["videoAudioMuted"] = True
        self.assertFalse(self.audit(self.b)["timing_and_audio_preserved"])


if __name__ == "__main__":
    unittest.main()
