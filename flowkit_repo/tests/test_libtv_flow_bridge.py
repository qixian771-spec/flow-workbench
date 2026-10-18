import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("libtv_flow_bridge", Path(__file__).parents[1] / "scripts/libtv_flow_bridge.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class BridgeGuardTest(unittest.TestCase):
    def setUp(self):
        self.node = {"nodeType": "video", "data": {"url": ["old"], "params": {"prompt": "pan"}}}

    def test_unchanged_target_accepted(self):
        bridge.verify_target(self.node, "pan", "old")

    def test_concurrent_prompt_edit_rejected(self):
        with self.assertRaises(ValueError):
            bridge.verify_target(self.node, "changed", "old")

    def test_concurrent_media_edit_rejected(self):
        with self.assertRaises(ValueError):
            bridge.verify_target(self.node, "pan", "other")

    def test_non_video_rejected(self):
        self.node["nodeType"] = "image"
        with self.assertRaises(ValueError):
            bridge.verify_target(self.node, "pan", "old")

    def test_multiple_outputs_rejected(self):
        self.node["data"]["url"].append("second")
        with self.assertRaises(ValueError):
            bridge.single_uri(self.node)

    def test_zero_exit_with_api_error_rejected(self):
        from types import SimpleNamespace
        result = SimpleNamespace(returncode=0, stderr="API Request Error: 404", stdout='{"ok":true}')
        with patch.object(bridge.subprocess, "run", return_value=result):
            with self.assertRaises(RuntimeError):
                bridge.cli("libtv", "node", "test")

    def test_unsupported_node_settings_rejected(self):
        params = self.node["data"]["params"]
        params.update(settings={"duration": 8, "ratio": "16:9"}, modeType="singleImage2video", imageList=[{}])
        bridge.validate_generation_request(self.node)
        for key, bad in [("duration", 10), ("ratio", "9:16")]:
            old = params["settings"][key]
            params["settings"][key] = bad
            with self.assertRaises(ValueError):
                bridge.validate_generation_request(self.node)
            params["settings"][key] = old
        params["imageList"] = []
        with self.assertRaises(ValueError):
            bridge.validate_generation_request(self.node)

    def test_pending_never_uploads(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as d:
            state = Path(d) / "state.json"
            bridge.save(state, {"phase": "submitted", "flow_base": "http://127.0.0.1:8100", "video_id": "v"})
            with patch.object(bridge, "api", return_value={"done": False}), patch.object(bridge, "cli") as cli:
                self.assertEqual(bridge.collect(None, state), 3)
                cli.assert_not_called()

    def test_ambiguous_upload_never_repeats(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as d:
            state = Path(d) / "state.json"
            bridge.save(state, {"phase": "uploading"})
            with patch.object(bridge, "api") as api, patch.object(bridge, "cli") as cli:
                with self.assertRaises(ValueError):
                    bridge.collect(None, state)
                api.assert_not_called()
                cli.assert_not_called()

    def test_failed_generation_never_uploads(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as d:
            state = Path(d) / "state.json"
            bridge.save(state, {"phase": "submitted", "flow_base": "http://127.0.0.1:8100", "video_id": "v"})
            with patch.object(bridge, "api", return_value={"done": True, "total": 1, "all_succeeded": False}), patch.object(bridge, "cli") as cli:
                with self.assertRaises(ValueError):
                    bridge.collect(None, state)
                cli.assert_not_called()


if __name__ == "__main__":
    unittest.main()
