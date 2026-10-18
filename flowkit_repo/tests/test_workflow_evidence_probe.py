"""Synthetic fixtures exercise the contract, never the live evidence index."""
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("workflow_evidence_probe", ROOT / "scripts/workflow_evidence_probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class WorkflowEvidenceProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "archive.json").write_bytes(b'{"synthetic":true}')
        self.now = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
        self.doc = {
            "schema_version": 1,
            "audit": {"id": "audit", "started_at": "2026-10-15T10:00:00Z", "code_rev": "a" * 40},
            "evidence": [{"id": "ev", "platform": "seko", "surface": "canvas",
                "kind": "historical_runtime", "observed_at": "2026-10-13",
                "audit_id": "audit", "code_rev": "a" * 40,
                "source_locator": "archive.json", "artifact_path": "archive.json", "sample": None,
                "sha256": hashlib.sha256((self.root / "archive.json").read_bytes()).hexdigest(),
                "limitations": ["Synthetic unit fixture; day precision only"],
                "supported_capabilities": ["node_replacement"]}],
            "claims": [{"id": "claim", "platform": "seko", "surface": "canvas",
                "capability": "node_replacement", "status": "tested", "temporal_scope": "historical",
                "evidence_ids": ["ev"], "limitations": ["Not a complete workflow"], "blocker": None}],
            "candidates": [], "selection": {}, "steps": [], "integration_items": [], "handoff": {},
        }

    def result(self, stage="tracer"):
        return probe.validate_evidence(self.doc, self.root, stage, self.now, getattr(self, "build", None))

    def rejected(self, name, stage="tracer"):
        result = self.result(stage)
        checks = {c["name"]: c["passed"] for c in result["checks"]}
        self.assertIn(name, checks)
        self.assertFalse(checks[name])
        self.assertFalse(result["contract_valid"])

    def test_real_file_and_matching_claim_pass(self):
        result = self.result()
        self.assertTrue(result["contract_valid"])
        self.assertGreater(result["counts"]["evidence"], 0)
        self.assertTrue(result["checks"])
        self.assertEqual(result["feasibility"], "unassessed")

    def test_gap_entrypoints_required(self):
        self.assertIn("gate", probe.STAGES)
        self.assertTrue(callable(getattr(probe, "validate_gap_gate", None)))

    def test_gap_forced_profile_cannot_be_omitted(self):
        if not callable(getattr(probe, "validate_gap_gate", None)):
            self.fail("Missing required gap gate")
        result = probe.validate_evidence(self.doc, self.root, "tracer", self.now,
                                         require_gap_closure=True)
        self.assertFalse(result["contract_valid"])

    def test_gap_roundtrip_bound_and_incomplete_rejected(self):
        if not callable(getattr(probe, "validate_gap_gate", None)):
            self.fail("Missing required gap gate")
        trial = {"id": "trial", "candidate_id": "official", "existing_run_id": "run",
            "request_id": "request", "step_id": "image", "audit_id": "audit",
            "build_module_ids": ["module"], "window": {"complete": True,
                "start": "2026-10-15T11:00:00Z", "end": "2026-10-15T11:05:00Z"},
            "method": "POST", "path": "/observed-only", "event": "ToolCallCompleted",
            "dispatch_authority": "execution_layer", "authority_source": "execution trace",
            "timing": "pre_dispatch", "waiting_identity": "request",
            "vendor_task_state": "observed_not_created",
            "external_artifact": {"identity": "media", "sha256": "a" * 64},
            "replacement": {"pending_tool_call_id": "image", "accepted_tool_call_id": "image",
                "acceptance_kind": "generation_result", "output_node_ids": ["media"]},
            "acceptance_receipt": "receipt", "resume_input_identity": "request",
            "resume_output_identity": "result", "next_gate": "next-request",
            "timestamps": ["2026-10-15T11:01:00Z", "2026-10-15T11:02:00Z", "2026-10-15T11:03:00Z"],
            "evidence_ids": ["proof"], "conclusion": "proven", "limitations": ["Synthetic; protocol_only"]}
        profile = {"schema_version": 1, "source_audit_id": "old", "purpose": "phase1_boundary_evidence",
            "test_input_sha256": "b" * 64, "reference_set": [], "expected_candidate_ids": ["official"],
            "protocol_trials": [trial], "candidate_runs": [],
            "execution_channel": {"kind": "existing_native_protocol", "source_locator": "source",
                "actual_entrypoint": "/observed-only", "capability_scope": ["image"],
                "protocol_trial_ids": ["trial"]}}
        self.doc["gap_profile"] = profile
        self.doc["candidates"] = [{"id": "official"}]
        self.doc["selection"] = {"test_input": {"sha256": "b" * 64}}
        build = {"audit_id": "audit", "modules": [{"id": "module", "origin_kind": "current"}]}
        ev = {"kind": "current_runtime", "audit_id": "audit", "observed_at": "2026-10-15T11:05:00Z",
              "sample": {"protocol_trial": copy.deepcopy(trial), "server_observation": {
                  "source": "server_run_detail", "run_id": "run", "tool_call_id": "image",
                  "event": "ToolCallCompleted", "output_node_ids": ["media"],
                  "next_gate": "next-request"}}}
        def gate(t=trial, evidence=ev):
            profile["protocol_trials"] = [t]
            return probe.validate_gap_gate(self.doc, build, {"proof": evidence}, self.now, lambda *args: None)
        self.assertTrue(gate()["tracer_complete"])
        # The actual client emits external_tool.completed before its transport
        # rejects external_tool_result. HTTP 200 stream replay also leaves the
        # same pending tool unchanged. Neither is a server acceptance receipt.
        for observation in [None, {},
                dict(ev["sample"]["server_observation"], source="client_event"),
                dict(ev["sample"]["server_observation"], event="external_tool.completed"),
                dict(ev["sample"]["server_observation"], event="RunPaused"),
                dict(ev["sample"]["server_observation"], run_id="other"),
                dict(ev["sample"]["server_observation"], tool_call_id="other"),
                dict(ev["sample"]["server_observation"], output_node_ids=["other"]),
                dict(ev["sample"]["server_observation"], next_gate="request")]:
            with self.subTest(server_observation=observation):
                changed_ev = copy.deepcopy(ev)
                changed_ev["sample"]["server_observation"] = observation
                self.assertFalse(gate(trial, changed_ev)["tracer_complete"])
        # A real paused questionnaire can read an uploaded node and pause again.
        # Even a fully bound record of that event is not replacement of a media tool.
        for replacement in [None, {},
                {"pending_tool_call_id": "image", "accepted_tool_call_id": "image",
                 "acceptance_kind": "reference_only", "output_node_ids": ["media"]},
                {"pending_tool_call_id": "image", "accepted_tool_call_id": "node-reader",
                 "acceptance_kind": "generation_result", "output_node_ids": ["media"]},
                {"pending_tool_call_id": "image", "accepted_tool_call_id": "image",
                 "acceptance_kind": "generation_result", "output_node_ids": []}]:
            with self.subTest(replacement=replacement):
                changed = copy.deepcopy(trial)
                changed["replacement"] = replacement
                matched_ev = copy.deepcopy(ev)
                matched_ev["sample"]["protocol_trial"] = copy.deepcopy(changed)
                self.assertFalse(gate(changed, matched_ev)["tracer_complete"])
        mutations = {"audit_id": "old", "existing_run_id": "other", "step_id": "other",
            "build_module_ids": ["old"], "dispatch_authority": "browser",
            "timing": "post_dispatch", "vendor_task_state": "unknown", "acceptance_receipt": None,
            "next_gate": None, "window": {"complete": False}, "resume_output_identity": None}
        for key, value in mutations.items():
            with self.subTest(key=key):
                changed = copy.deepcopy(trial)
                changed[key] = value
                self.assertFalse(gate(changed)["tracer_complete"])
        for field, value in [("kind", "source"), ("audit_id", "old"), ("observed_at", "2026-10-14T11:05:00Z")]:
            with self.subTest(evidence_field=field):
                changed = copy.deepcopy(ev)
                changed[field] = value
                self.assertFalse(gate(trial, changed)["tracer_complete"])
        profile["protocol_trials"] = []
        profile["execution_channel"]["ready"] = True
        result = probe.validate_gap_gate(self.doc, build, {}, self.now, lambda *args: None)
        self.assertFalse(result["tracer_complete"])
        self.assertFalse(result["control_gate_complete"])

    def test_missing_file_rejected_without_sample_substitution(self):
        (self.root / "archive.json").unlink()
        self.rejected("evidence.ev.artifact_readable")

    def test_empty_evidence_rejected(self):
        self.doc["evidence"] = []
        self.rejected("evidence_nonempty")

    def test_duplicate_id_rejected(self):
        self.doc["evidence"].append(copy.deepcopy(self.doc["evidence"][0]))
        self.rejected("unique_ids")

    def test_dangling_evidence_rejected(self):
        self.doc["claims"][0]["evidence_ids"] = ["missing"]
        self.rejected("claim.claim.references")

    def test_wrong_hash_rejected(self):
        self.doc["evidence"][0]["sha256"] = "0" * 64
        self.rejected("evidence.ev.sha256")

    def test_broader_capability_rejected(self):
        self.doc["claims"][0]["capability"] = "complete_workflow"
        self.rejected("claim.claim.scope")

    def test_wrong_surface_rejected(self):
        self.doc["claims"][0]["surface"] = "agent_skill"
        self.rejected("claim.claim.scope")

    def test_static_cannot_be_tested(self):
        self.doc["evidence"][0]["kind"] = "static"
        self.rejected("claim.claim.runtime_support")

    def test_historical_cannot_be_current(self):
        self.doc["claims"][0]["temporal_scope"] = "current"
        self.rejected("claim.claim.temporal_scope")

    def test_future_observation_rejected(self):
        self.doc["evidence"][0]["observed_at"] = "2026-10-16"
        self.rejected("evidence.ev.observed_at")

    def test_sample_hash_is_canonical_utf8(self):
        ev = self.doc["evidence"][0]
        ev["artifact_path"] = None
        ev["sample"] = {"synthetic": True, "说明": "采样"}
        ev["sha256"] = hashlib.sha256(json.dumps(ev["sample"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        self.assertTrue(self.result()["contract_valid"])

    def test_file_and_sample_are_exclusive(self):
        self.doc["evidence"][0]["sample"] = {"synthetic": True}
        self.rejected("evidence.ev.payload")

    def test_absolute_or_escape_path_rejected(self):
        for path in ["/etc/passwd", "../archive.json"]:
            self.doc["evidence"][0]["artifact_path"] = path
            self.rejected("evidence.ev.artifact_readable")

    def test_unknown_stage_rejected(self):
        self.rejected("stage_supported", "invented")

    def test_missing_required_field_rejected(self):
        del self.doc["evidence"][0]["limitations"]
        self.rejected("evidence.ev.fields")

    def test_unknown_claim_requires_evidence(self):
        self.doc["claims"][0].update(status="unknown", evidence_ids=[])
        self.rejected("claim.claim.references")

    def test_cli_exit_codes_and_read_only_input(self):
        path = self.root / "evidence.json"
        path.write_text(json.dumps(self.doc))
        before = path.read_bytes()
        command = ["python3", str(ROOT / "scripts/workflow_evidence_probe.py"), "--evidence", str(path), "--stage", "tracer"]
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(path.read_bytes(), before)
        self.doc["evidence"][0]["sha256"] = "0" * 64
        path.write_text(json.dumps(self.doc))
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["contract_valid"])
        path.write_text("{broken")
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("error", json.loads(result.stdout))
        result = subprocess.run(command[:-1] + ["unknown"], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("error", json.loads(result.stdout))

    def matrix(self):
        ev, claim = copy.deepcopy(self.doc["evidence"][0]), copy.deepcopy(self.doc["claims"][0])
        self.doc["evidence"], self.doc["claims"] = [], []
        for platform in ["libtv", "oiioii", "seko"]:
            for surface in ["canvas", "editor", "agent_skill"]:
                cid = platform + "-" + surface
                capability = "bounded_observation"
                if (platform, surface) == ("seko", "canvas"):
                    capability = "node_update_leaves_stale_shot"
                if (platform, surface) == ("oiioii", "editor"):
                    capability = "clips_updated_source_reference_stale"
                self.doc["evidence"].append(dict(ev, id="ev-" + cid, platform=platform, surface=surface, supported_capabilities=[capability]))
                self.doc["claims"].append(dict(claim, id=cid, platform=platform, surface=surface, capability=capability, evidence_ids=["ev-" + cid]))
        self.report()

    def report(self):
        path = self.root / probe.REPORT_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("| claim_id | evidence_ids |\n| --- | --- |\n" + "\n".join(
            "| `claim_id:" + c["id"] + "` | " + ", ".join(c["evidence_ids"]) + " |" for c in self.doc["claims"]))

    def test_matrix_all_nine_scopes_pass(self):
        self.matrix()
        result = self.result("matrix")
        self.assertTrue(result["contract_valid"], result["checks"])
        self.assertEqual(len(result["counts"]["coverage"]), 9)
        self.assertEqual(result["feasibility"], "unassessed")

    def test_matrix_missing_surface_rejected(self):
        self.matrix()
        self.doc["claims"].pop()
        self.report()
        self.rejected("matrix.coverage", "matrix")

    def test_matrix_report_missing_row_rejected(self):
        self.matrix()
        path = self.root / probe.REPORT_PATH
        path.write_text(path.read_text().rsplit("\n", 1)[0])
        self.rejected("matrix.report_claim_ids", "matrix")

    def test_matrix_report_wrong_evidence_rejected(self):
        self.matrix()
        path = self.root / probe.REPORT_PATH
        path.write_text(path.read_text().replace("ev-seko-canvas", "ev-unknown"))
        self.rejected("matrix.report_evidence_ids", "matrix")

    def test_matrix_seko_counterexample_cannot_be_complete_replacement(self):
        self.matrix()
        self.doc["claims"][6]["capability"] = "complete_replacement"
        self.rejected("matrix.seko_counterexample", "matrix")

    def test_matrix_oiioii_counterexample_cannot_be_removed(self):
        self.matrix()
        self.doc["claims"][4]["capability"] = "complete_replacement"
        self.rejected("matrix.oiioii_counterexample", "matrix")

    def test_matrix_static_discovery_cannot_be_tested(self):
        self.matrix()
        self.doc["evidence"][-1]["kind"] = "static"
        self.rejected("claim.seko-agent_skill.runtime_support", "matrix")

    def build_fixture(self):
        ev = dict(self.doc["evidence"][0], id="ev-build", kind="current_runtime",
                  observed_at="2026-10-15T11:00:00Z", artifact_path=None,
                  sample={"synthetic": True, "body_sha256": "b" * 64},
                  supported_capabilities=["module_contract"])
        ev["sha256"] = hashlib.sha256(json.dumps(ev["sample"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.doc["evidence"].append(ev)
        self.build = {"audit_id": "audit", "observed_at": ev["observed_at"],
                      "page_locator": "https://example.test/", "context": {
                          "login_observed": True, "project_observed": True, "health_evidence_ids": ["ev-build"]},
                      "modules": [], "bridge": {"code_rev": "a" * 40, "status": "blocked",
                          "evidence_ids": ["ev-build"], "reason": "Synthetic import failure"}}
        for name, exports in [("LoginContext-CFHyujin.js", ["Y", "g", "k"]),
                              ("canvas-BZat8bJg.js", ["an", "D", "b"]),
                              ("useOSSUploader-BaPQIV7u.js", ["m"])]:
            self.build["modules"].append({"id": name, "origin_kind": "current",
                "locator": "https://example.test/assets/" + name, "observed_at": ev["observed_at"],
                "http_status": 200, "content_type": "application/javascript", "body_sha256": "b" * 64,
                "required_exports": exports, "observed_exports": exports,
                "evidence_ids": ["ev-build"], "compatibility": "matched", "reason": "Synthetic fixture"})
            module = self.build["modules"][-1]
            module_ev = copy.deepcopy(ev)
            module_ev["id"] = "ev-module-" + name
            module_ev["sample"].update({k: module[k] for k in
                ["locator", "http_status", "content_type", "observed_exports"]})
            self.rehash(module_ev)
            self.doc["evidence"].insert(-1, module_ev)
            module["evidence_ids"] = [module_ev["id"]]

    def test_build_valid_matched_modules_blocked_bridge(self):
        self.build_fixture()
        result = self.result("build")
        self.assertTrue(result["contract_valid"], result["checks"])
        self.assertEqual(result["counts"]["modules"], 3)

    def test_build_empty_modules_rejected(self):
        self.build_fixture()
        self.build["modules"] = []
        self.rejected("build.modules_nonempty", "build")

    def test_build_wrong_audit_rejected(self):
        self.build_fixture()
        self.build["audit_id"] = "old"
        self.rejected("build.audit", "build")

    def test_build_stale_or_future_current_sample_rejected(self):
        self.build_fixture()
        for value in ["2026-10-13T11:00:00Z", "2026-10-16T11:00:00Z"]:
            self.build["modules"][0]["observed_at"] = value
            self.rejected("build.module.LoginContext-CFHyujin.js.fresh", "build")

    def test_build_current_cannot_link_cached_evidence(self):
        self.build_fixture()
        self.doc["evidence"][-4]["kind"] = "historical_runtime"
        self.rejected("build.module.LoginContext-CFHyujin.js.fresh", "build")

    def test_build_html_or_missing_exports_not_matched(self):
        self.build_fixture()
        self.build["modules"][0]["content_type"] = "text/html"
        self.rejected("build.module.LoginContext-CFHyujin.js.matched", "build")
        self.build["modules"][0]["content_type"] = "application/javascript"
        self.build["modules"][0]["observed_exports"] = []
        self.rejected("build.module.LoginContext-CFHyujin.js.matched", "build")

    def test_build_hash_must_match_sample(self):
        self.build_fixture()
        self.build["modules"][0]["body_sha256"] = "c" * 64
        self.rejected("build.module.LoginContext-CFHyujin.js.hash_link", "build")

    def test_build_real_mismatch_and_unknown_are_valid(self):
        self.build_fixture()
        self.build["modules"][0].update(compatibility="mismatched", http_status=404,
                                       content_type="text/html", observed_exports=[])
        self.doc["evidence"][-4]["sample"].update(http_status=404, content_type="text/html", observed_exports=[])
        self.rehash(self.doc["evidence"][-4])
        self.build["modules"][1].update(compatibility="unknown")
        self.assertTrue(self.result("build")["contract_valid"])

    def test_build_ready_requires_runtime_startup_evidence(self):
        self.build_fixture()
        self.build["bridge"]["status"] = "ready"
        self.rejected("build.bridge_ready", "build")

    def test_build_response_fields_must_match_hashed_observation(self):
        for field, value in [("http_status", 404), ("content_type", "text/plain"),
                             ("locator", "https://example.test/other.js"),
                             ("observed_exports", [])]:
            with self.subTest(field=field):
                self.setUp()
                self.build_fixture()
                ev = self.doc["evidence"][-4]
                ev["sample"][field] = value
                self.rehash(ev)
                self.rejected("build.module.LoginContext-CFHyujin.js.response_binding", "build")

    def test_build_missing_response_metadata_requires_unknown(self):
        self.build_fixture()
        ev = self.doc["evidence"][-4]
        del ev["sample"]["locator"]
        self.rehash(ev)
        self.rejected("build.module.LoginContext-CFHyujin.js.response_binding", "build")
        self.build["modules"][0]["compatibility"] = "unknown"
        self.assertTrue(self.result("build")["contract_valid"])

    def test_build_content_type_normalization(self):
        self.build_fixture()
        self.build["modules"][0]["content_type"] = " Application/JavaScript ; charset=utf-8"
        self.assertTrue(self.result("build")["contract_valid"])

    def test_actual_404_samples_cannot_support_forged_matched_rows(self):
        root = Path(__file__).resolve().parents[1]
        doc = json.loads((root / "docs/benchmarks/workflow-boundaries/evidence.json").read_text())
        build = json.loads((root / "docs/benchmarks/workflow-boundaries/current-build.json").read_text())
        # This is a historical 404 audit, not a certificate for today's bridge.
        # Preserve its exact source bytes from its recorded revision when code evolves.
        historical = Path(self.tmp.name) / "historical-audit"
        for evidence in doc["evidence"]:
            relative = evidence.get("artifact_path")
            if not relative:
                continue
            raw = (root / relative).read_bytes()
            if hashlib.sha256(raw).hexdigest() != evidence["sha256"]:
                raw = subprocess.check_output(["git", "show", evidence["code_rev"] + ":" + relative], cwd=root)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), evidence["sha256"])
            target = historical / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        root = historical
        self.assertTrue(probe.validate_evidence(doc, root, "build", self.now, build)["contract_valid"])
        for module in build["modules"][:3]:
            module.update(http_status=200, content_type="application/javascript",
                          observed_exports=module["required_exports"], compatibility="matched")
        result = probe.validate_evidence(doc, root, "build", self.now, build)
        self.assertFalse(result["contract_valid"])
        failed = {c["name"] for c in result["checks"] if not c["passed"]}
        for module in build["modules"][:3]:
            self.assertIn("build.module." + module["id"] + ".response_binding", failed)

    def candidates_fixture(self, selected=False):
        self.build_fixture()
        text = "原创：两位朋友在雨后的车站告别。"
        self.doc["selection"] = {"status": "selected" if selected else "blocked",
            "candidate_id": "official" if selected else None, "compared_ids": ["official", "community"],
            "test_input": {"id": "same-input", "text": text, "sha256": hashlib.sha256(text.encode()).hexdigest(),
                           "purpose": "Synthetic comparison fixture"},
            "rationale": ["Compare observed coverage, then manual cost"],
            "blockers": [] if selected else ["Execution not observed"]}
        for origin in ["official", "community"]:
            sample = {"synthetic": True, "origin": origin, "author": origin + " author",
                "candidate_id": origin, "run_id": "run-" + origin,
                "test_input_sha256": self.doc["selection"]["test_input"]["sha256"],
                "observed_stages": ["film"] if selected else [],
                "manual_actions_observed": [{"stage": "script", "action": "confirm", "count": 1}] if selected else []}
            ev = dict(self.doc["evidence"][-1], id="ev-" + origin, sample=sample,
                      supported_capabilities=["candidate_source"])
            ev["sha256"] = hashlib.sha256(json.dumps(sample, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            self.doc["evidence"].append(ev)
            self.doc["candidates"].append({"id": origin, "origin": origin, "author": origin + " author",
                "run_id": "run-" + origin,
                "source_locator": "https://example.test/" + origin, "source_evidence_ids": [ev["id"]],
                "accessible": True, "input_contract": "One original story idea",
                "output_stages": [{"stage": "film", "kind": "observed" if selected else "advertised",
                                   "evidence_ids": [ev["id"]]}],
                "manual_actions": [{"stage": "script", "action": "confirm", "count": 1 if selected else None,
                                    "evidence_ids": [ev["id"]]}],
                "generation_entrypoints": "Unknown", "assembly_path": "Unknown",
                "observations": [{"kind": "observed", "detail": "Detail page accessible", "evidence_ids": [ev["id"]]}],
                "limitations": ["Synthetic unit fixture"], "test_input_id": "same-input"})

    def rehash(self, ev):
        ev["sha256"] = hashlib.sha256(json.dumps(ev["sample"], sort_keys=True,
            separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

    def test_candidate_comparison_requires_bound_current_run(self):
        for field, value in [("kind", "static"), ("kind", "source"),
                             ("kind", "historical_runtime"),
                             ("observed_at", "2026-10-13T11:00:00Z"),
                             ("audit_id", "other-audit"),
                             ("candidate_id", "other"), ("test_input_sha256", "0" * 64),
                             ("run_id", "other-run"), ("run_id", None)]:
            with self.subTest(field=field, value=value):
                self.setUp()
                self.candidates_fixture(selected=True)
                ev = self.doc["evidence"][-2]
                target = ev if field in {"kind", "observed_at", "audit_id"} else ev["sample"]
                target[field] = value
                self.rehash(ev)
                self.rejected("candidate.official.output_stages", "candidates")
                self.rejected("candidate.official.manual_actions", "candidates")
                self.assertFalse(self.result("candidates")["comparison_complete"])

    def test_candidate_static_metadata_remains_valid_without_execution(self):
        self.candidates_fixture()
        for ev in self.doc["evidence"][-2:]:
            ev["kind"] = "static"
        self.assertTrue(self.result("candidates")["contract_valid"])
        self.assertFalse(self.result("candidates")["comparison_complete"])

    def steps_fixture(self, selected=True):
        self.matrix()
        self.candidates_fixture(selected=selected)
        ref = ["ev-official"]
        port = {"name": "prompt", "source": "unknown", "fields": ["unknown"],
                "media_identity": "unknown", "evidence_ids": ref}
        self.doc["steps"] = [{"id": "s1", "candidate_id": "official", "name": "Observed boundary",
            "stage": "image", "required": selected, "inputs": [copy.deepcopy(port)], "outputs": [copy.deepcopy(port)],
            "trigger": {"method": "unknown", "path": "unknown", "event": "unknown", "evidence_ids": ref},
            "initiator": "unknown", "executor": "unknown",
            "states": [{"value": "unknown", "evidence_ids": ref}],
            "failure_semantics": [{"value": "unknown", "evidence_ids": ref}],
            "manual_actions": [{"action": "unknown", "count": None, "evidence_ids": ref}],
            "depends_on": [], "evidence_ids": ref, "build_module_ids": [self.build["modules"][0]["id"]],
            "control": {"status": "unproven", "timing": "unknown", "mechanism": "unknown",
                "evidence_ids": ref, "dispatch_observation": {"state": "unknown", "evidence_ids": ref},
                "input_contract": "unknown", "output_contract": "unknown", "resume_contract": "unknown"},
            "blocker": {"kind": "contract_unproven", "reason": "No execution observed", "attempted": ["Read metadata"],
                "next_action": "Observe safe protocol", "evidence_ids": ref}}]

    def test_steps_selected_and_independent_records_valid(self):
        self.steps_fixture()
        self.assertTrue(self.result("steps")["contract_valid"])
        self.doc["selection"].update(status="blocked", candidate_id=None, blockers=["Unknown execution"])
        self.doc["steps"][0]["required"] = False
        self.assertTrue(self.result("steps")["contract_valid"])

    def test_steps_empty_selected_rejected(self):
        self.steps_fixture()
        self.doc["steps"] = []
        self.rejected("steps.selection", "steps")

    def test_steps_orphan_candidate_or_build_rejected(self):
        self.steps_fixture()
        self.doc["steps"][0]["candidate_id"] = "missing"
        self.rejected("step.s1.candidate", "steps")
        self.doc["steps"][0]["build_module_ids"] = ["missing"]
        self.rejected("step.s1.build", "steps")

    def test_steps_missing_or_cyclic_dependency_rejected(self):
        self.steps_fixture()
        for dep in ["missing", "s1"]:
            self.doc["steps"][0]["depends_on"] = [dep]
            self.rejected("steps.dependencies", "steps")

    def test_steps_disconnected_port_source_rejected(self):
        self.steps_fixture()
        self.doc["steps"][0]["inputs"][0]["source"] = "step:missing"
        self.rejected("step.s1.ports", "steps")

    def test_steps_unknown_executor_not_defaulted(self):
        self.steps_fixture()
        del self.doc["steps"][0]["executor"]
        self.rejected("step.s1.fields", "steps")

    def controls_fixture(self, status="proven"):
        self.steps_fixture()
        s = self.doc["steps"][0]
        s["executor"] = "vendor"
        s["control"].update(status=status, timing="pre_dispatch", mechanism="Synthetic external-tool gate",
            input_contract="prompt fields", output_contract="media ID receipt", resume_contract="resume by task ID")
        s["control"]["dispatch_observation"]["state"] = "observed_not_created"
        obs = {"step_id": "s1", "executor": "vendor", "timing": "pre_dispatch",
            "dispatch_state": "observed_not_created", "dispatch_authority": "execution_layer",
            "mechanism": s["control"]["mechanism"], "input_contract": "prompt fields",
            "output_contract": "media ID receipt", "resume_contract": "resume by task ID",
            "build_module_ids": s["build_module_ids"], "outcome": status,
            "reason": "Explicit protocol rejects external outputs" if status == "blocked" else "Gate observed"}
        ev = self.doc["evidence"][-2]
        ev["sample"]["control_observation"] = obs
        ev["sha256"] = hashlib.sha256(json.dumps(ev["sample"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if status == "blocked":
            s["blocker"]["kind"] = "unsupported"
        else:
            s["blocker"] = None

    def test_controls_current_execution_proof_passes(self):
        self.controls_fixture()
        self.assertTrue(self.result("controls")["contract_valid"])

    def test_controls_post_dispatch_or_unknown_executor_rejected(self):
        self.controls_fixture()
        self.doc["steps"][0]["control"]["timing"] = "post_dispatch"
        self.rejected("control.s1.proven", "controls")
        self.doc["steps"][0]["control"]["timing"] = "pre_dispatch"
        self.doc["steps"][0]["executor"] = "unknown"
        self.rejected("control.s1.proven", "controls")

    def test_controls_browser_silence_not_server_proof(self):
        self.controls_fixture()
        self.doc["evidence"][-2]["sample"]["control_observation"]["dispatch_authority"] = "browser_network"
        self.rejected("control.s1.proven", "controls")

    def test_controls_missing_contract_or_old_evidence_rejected(self):
        self.controls_fixture()
        self.doc["steps"][0]["control"]["resume_contract"] = "unknown"
        self.rejected("control.s1.proven", "controls")
        self.controls_fixture()
        self.doc["evidence"][-2]["kind"] = "historical_runtime"
        self.rejected("control.s1.proven", "controls")

    def test_controls_real_blocked_valid_but_missing_access_not_technical(self):
        self.controls_fixture("blocked")
        self.assertTrue(self.result("controls")["contract_valid"])
        self.doc["steps"][0]["blocker"]["kind"] = "missing_access"
        self.rejected("control.s1.blocked", "controls")

    def test_controls_retained_vendor_requires_separate_media_impact(self):
        self.steps_fixture()
        s = self.doc["steps"][0]
        s.update(stage="lipsync", executor="vendor")
        s["control"].update(status="not_applicable", timing="not_applicable")
        self.rejected("control.s1.retained_media", "controls")
        s["retained_media"] = {"status": "unknown", "media_source_effect": "unknown",
            "protection_impact": "unknown", "evidence_ids": ["ev-official"]}
        self.assertTrue(self.result("controls")["contract_valid"])

    def final_fixture(self, status="unassessed"):
        self.controls_fixture("blocked" if status == "blocked" else "proven")
        s = self.doc["steps"][0]
        for port in s["inputs"] + s["outputs"]:
            port.update(source="user", fields=["prompt"], media_identity="text")
        s["trigger"].update(method="POST", path="/synthetic", event="dispatch")
        s["initiator"] = "server"
        s["states"][0]["value"] = "paused"
        s["failure_semantics"][0]["value"] = "explicit rejection"
        s["manual_actions"][0].update(action="confirm", count=1)
        ev = self.doc["evidence"][-2]
        ev["sample"]["manual_actions_observed"].append({"stage": "image", "action": "confirm", "count": 1})
        ev["sample"]["workflow_coverage"] = {"candidate_id": "official", "step_ids": ["s1"], "complete": True}
        ev["sample"]["trigger_observation"] = dict(step_id="s1",
            **{k: s["trigger"][k] for k in ["method", "path", "event"]})
        ev["sha256"] = hashlib.sha256(json.dumps(ev["sample"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.doc["integration_items"] = [{"id": "i1", "step_id": "s1", "owner_phase": 2,
            "disposition": "replace_generation", "inputs": ["prompt"], "outputs": ["media ID"], "depends_on": [],
            "acceptance": ["Current execution-layer proof"], "evidence_ids": ["ev-official"], "blocker": s["blocker"]}]
        self.doc["model_routes"] = [{"id": "r1", "step_id": "s1", "task_type": "image",
            "candidate_ids": ["official"], "current_provider": "vendor", "current_model_key": "unknown",
            "target_provider": "Flow", "target_model_key": "unknown", "parameters": {},
            "execution_level": "synthetic", "evidence_ids": ["ev-official"], "automatic_substitution": False,
            "notes": "Synthetic unit fixture"}]
        self.doc["handoff"] = {"decision_ids": ["D-02", "D-03", "D-04", "D-09", "D-10", "D-11", "D-12", "D-14"],
            "quality_retry_limit": 2, "retry_model_policy": "same_model", "unknown_submit_policy": "reconcile_before_resubmit",
            "pause_policy": "failed_scene_and_dependents", "independent_policy": "continue", "final_export_policy": "all_scenes_passed",
            "owner_phases": {"generation": [2], "backfill": [3], "scheduling": [3, 4], "voice_acceptance": [5], "overall_acceptance": [6]},
            "feasibility": status, "evidence_complete": status != "unassessed", "comparison_complete": True,
            "unresolved": [] if status == "feasible" else ["Current gap"],
            "scope_decision": {"status": "not_needed" if status == "feasible" else "requires_decision" if status == "blocked" else "pending_evidence",
                "affected_scope": ["generation"], "required_evidence": ["execution proof"],
                "candidate_adjustments": ["No automatic scope change"]}}
        if status == "unassessed":
            self.doc["selection"].update(status="blocked", candidate_id=None, blockers=["Actual comparison incomplete"])
            for c in self.doc["candidates"]:
                c["manual_actions"][0]["count"] = None
            s["required"] = False
            s["control"].update(status="unproven", timing="unknown")
            s["blocker"] = {"kind": "contract_unproven", "reason": "Unknown control", "attempted": ["Read-only audit"],
                "next_action": "Observe execution", "evidence_ids": ["ev-official"]}
            self.doc["handoff"]["comparison_complete"] = False

    def test_final_incomplete_never_ready_or_complete(self):
        self.final_fixture()
        r = self.result("final")
        self.assertTrue(r["contract_valid"], r["checks"])
        self.assertFalse(r["report_complete"])
        self.assertFalse(r["ready_for_phase2"])
        self.assertEqual(r["feasibility"], "unassessed")

    def test_final_sufficient_blocked_report_valid_not_ready(self):
        self.final_fixture("blocked")
        r = self.result("final")
        self.assertTrue(r["contract_valid"], r["checks"])
        self.assertTrue(r["report_complete"])
        self.assertFalse(r["ready_for_phase2"])
        self.assertEqual(r["feasibility"], "blocked")

    def ready_final_fixture(self, status):
        self.final_fixture(status)
        if status == "feasible":
            self.build["bridge"]["status"] = "ready"
            ev = next(e for e in self.doc["evidence"] if e["id"] == "ev-build")
            ev["sample"]["bridge_phase"] = "ready"
            self.rehash(ev)

    def test_final_known_trigger_proof_allows_complete_branches(self):
        for status in ["blocked", "feasible"]:
            self.setUp()
            self.ready_final_fixture(status)
            result = self.result("final")
            self.assertTrue(result["contract_valid"], result["checks"])
            self.assertTrue(result["report_complete"])
            self.assertEqual(result["ready_for_phase2"], status == "feasible")

    def test_final_unknown_trigger_blocks_both_complete_conclusions(self):
        for status in ["blocked", "feasible"]:
            for field in ["method", "path", "event"]:
                with self.subTest(status=status, field=field):
                    self.setUp()
                    self.ready_final_fixture(status)
                    self.doc["steps"][0]["trigger"][field] = "unknown"
                    self.rejected("final.conclusion", "final")
                    self.assertFalse(self.result("final")["report_complete"])
                    self.doc["handoff"].update(feasibility="unassessed", evidence_complete=False,
                        unresolved=["Trigger unknown"])
                    self.doc["handoff"]["scope_decision"]["status"] = "pending_evidence"
                    result = self.result("final")
                    self.assertTrue(result["contract_valid"])
                    self.assertFalse(result["report_complete"])
                    self.assertFalse(result["ready_for_phase2"])
                    self.assertEqual(result["feasibility"], "unassessed")

    def test_final_trigger_requires_matching_execution_observation(self):
        for field, value in [("step_id", "other"), ("method", "GET"),
                             ("path", "/other"), ("event", "other")]:
            with self.subTest(field=field):
                self.setUp()
                self.ready_final_fixture("feasible")
                ev = self.doc["evidence"][-2]
                ev["sample"]["trigger_observation"][field] = value
                self.rehash(ev)
                self.rejected("final.conclusion", "final")
                self.assertFalse(self.result("final")["ready_for_phase2"])

    def test_final_missing_mapping_or_orphan_rejected(self):
        self.final_fixture("blocked")
        self.doc["integration_items"] = []
        self.rejected("final.integration_coverage", "final")
        self.doc["integration_items"] = [{"id": "bad", "step_id": "missing"}]
        self.rejected("integration.bad.fields", "final")

    def test_final_unknown_control_cannot_claim_feasible(self):
        self.final_fixture()
        self.doc["handoff"]["feasibility"] = "feasible"
        self.rejected("final.conclusion", "final")

    def test_final_retry_or_pause_policy_missing_rejected(self):
        self.final_fixture()
        self.doc["handoff"]["quality_retry_limit"] = 3
        self.rejected("final.policy", "final")
        self.doc["handoff"]["quality_retry_limit"] = 2
        del self.doc["handoff"]["pause_policy"]
        self.rejected("final.policy", "final")

    def test_final_requires_all_previous_stages(self):
        self.final_fixture()
        self.doc["claims"].pop()
        self.rejected("matrix.coverage", "final")

    def test_final_missing_access_stays_unassessed(self):
        self.final_fixture()
        self.doc["steps"][0]["blocker"]["kind"] = "missing_access"
        self.assertFalse(self.result("final")["report_complete"])

    def test_final_model_route_not_substituted_or_orphaned(self):
        self.final_fixture()
        self.doc["model_routes"][0]["automatic_substitution"] = True
        self.rejected("route.r1.fields", "final")

    def model_route_fixture(self, task_type="video"):
        self.final_fixture("blocked")
        self.doc["steps"][0]["stage"] = task_type
        route = self.doc["model_routes"][0]
        route.update(task_type=task_type, target_model_key="abra_i2v_8s" if task_type == "video" else "BELUGA",
            parameters={"mode": "frame_to_video", "duration_seconds": 8} if task_type == "video"
            else {"configured_name": "NANO_BANANA_2_1"})
        ev = self.doc["evidence"][-2]
        ev["sample"].update(image_models={"NANO_BANANA_2_1": "BELUGA", "OTHER": "OTHER_IMAGE"},
            omni_flash_models={"frame_to_video": {"8": "abra_i2v_8s", "4": "abra_i2v_4s"},
                               "text_to_video": {"8": "abra_t2v_8s"}})
        ev["sample"]["manual_actions_observed"].append({"stage": task_type, "action": "confirm", "count": 1})
        self.rehash(ev)
        return route

    def test_model_route_exact_catalog_mapping_passes(self):
        for task in ["image", "video"]:
            self.setUp()
            self.model_route_fixture(task)
            self.assertTrue(self.result("final")["contract_valid"])

    def test_model_route_cross_type_mode_duration_and_alias_rejected(self):
        for task, key, parameters in [
            ("video", "BELUGA", {"mode": "frame_to_video", "duration_seconds": 8}),
            ("video", "abra_t2v_8s", {"mode": "frame_to_video", "duration_seconds": 8}),
            ("video", "abra_i2v_4s", {"mode": "frame_to_video", "duration_seconds": 8}),
            ("video", "abra_i2v_8s", {"mode": "unknown", "duration_seconds": 8}),
            ("video", "abra_i2v_8s", {"mode": "frame_to_video", "duration_seconds": "8"}),
            ("image", "BELUGA", {"configured_name": "OTHER"}),
            ("image", "abra_i2v_8s", {"configured_name": "NANO_BANANA_2_1"})]:
            with self.subTest(task=task, key=key, parameters=parameters):
                self.setUp()
                route = self.model_route_fixture(task)
                route.update(target_model_key=key, parameters=parameters)
                self.rejected("route.r1.model_source", "final")

    def test_model_route_unknown_key_preserves_pending_contract(self):
        self.final_fixture()
        self.doc["model_routes"][0]["parameters"] = {"configured_name": "unknown"}
        result = self.result("final")
        self.assertTrue(result["contract_valid"])
        self.assertFalse(result["ready_for_phase2"])

    def test_candidates_metadata_only_blocked_is_valid(self):
        self.candidates_fixture()
        result = self.result("candidates")
        self.assertTrue(result["contract_valid"], result["checks"])
        self.assertFalse(result["comparison_complete"])
        self.assertEqual(result["counts"]["candidates"], 2)

    def test_candidates_selected_requires_both_real_origins(self):
        self.candidates_fixture(selected=True)
        self.assertTrue(self.result("candidates")["contract_valid"])
        self.doc["candidates"].pop()
        self.rejected("candidates.selection", "candidates")

    def test_candidates_mixed_inputs_rejected(self):
        self.candidates_fixture()
        self.doc["candidates"][-1]["test_input_id"] = "different"
        self.rejected("candidate.community.input", "candidates")

    def test_candidates_wrong_input_hash_rejected(self):
        self.candidates_fixture()
        self.doc["selection"]["test_input"]["sha256"] = "0" * 64
        self.rejected("candidates.test_input", "candidates")

    def test_candidates_unknown_actions_cannot_be_zero(self):
        self.candidates_fixture()
        self.doc["candidates"][0]["manual_actions"][0]["count"] = 0
        self.rejected("candidate.official.manual_actions", "candidates")

    def test_candidates_advertised_cannot_be_observed(self):
        self.candidates_fixture()
        self.doc["candidates"][0]["output_stages"][0]["kind"] = "observed"
        self.rejected("candidate.official.output_stages", "candidates")

    def test_candidates_author_origin_must_match_source(self):
        self.candidates_fixture()
        self.doc["candidates"][1]["author"] = "invented player"
        self.rejected("candidate.community.source", "candidates")

    def test_candidates_only_official_requires_documented_search_blocker(self):
        self.candidates_fixture()
        self.doc["candidates"].pop()
        self.doc["selection"]["compared_ids"] = ["official"]
        self.assertTrue(self.result("candidates")["contract_valid"])
        self.doc["selection"]["blockers"] = []
        self.rejected("candidates.selection", "candidates")


if __name__ == "__main__":
    unittest.main()
