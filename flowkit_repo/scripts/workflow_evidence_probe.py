"""Offline workflow evidence contract; no provider calls or writes.

Hashes bind bytes, not truth. supported_capabilities is the manually reviewed
scope of an observation; a successful audit never establishes feasibility.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

PLATFORMS = {"libtv", "oiioii", "seko", "local"}
SURFACES = {"canvas", "editor", "agent_skill", "media", "bridge"}
KINDS = {"historical_runtime", "current_runtime", "source", "static"}
STATUSES = {"tested", "discovered", "unimplemented", "blocked", "unknown"}
REPORT_PATH = "docs/THREE-PLATFORM-LIVE-RESULTS.md"
BRIDGE_EXPORTS = {"LoginContext-CFHyujin.js": {"Y", "g", "k"},
                  "canvas-BZat8bJg.js": {"an", "D", "b"}, "useOSSUploader-BaPQIV7u.js": {"m"}}
STAGES = {"tracer", "matrix", "build", "candidates", "steps", "controls", "final", "gate"}


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value):
    return isinstance(value, list) and bool(value) and all(nonempty(v) for v in value)


def instant(value, day_allowed=False):
    if not isinstance(value, str):
        return None
    try:
        if day_allowed and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None or result.utcoffset().total_seconds() != 0:
            return None
        return result
    except ValueError:
        return None


def validate_evidence(document, root, stage, now, build=None, require_gap_closure=False):
    """Validate a fixed stage; now is injectable for tests, never a CLI flag."""
    checks = []

    def check(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check("stage_supported", stage in STAGES, "Supported stages: " + ", ".join(sorted(STAGES)))
    check("document_object", isinstance(document, dict), "Top-level JSON object required")
    doc = document if isinstance(document, dict) else {}
    check("schema_version", type(doc.get("schema_version")) is int and doc["schema_version"] == 1, "schema_version=1")
    expected = {"audit": dict, "evidence": list, "claims": list, "candidates": list,
                "selection": dict, "steps": list, "integration_items": list, "handoff": dict}
    check("collections", all(isinstance(doc.get(k), t) for k, t in expected.items()), "All stage collections must be present with correct types")
    audit = doc.get("audit") if isinstance(doc.get("audit"), dict) else {}
    started = instant(audit.get("started_at"))
    check("audit", nonempty(audit.get("id")) and started is not None and started <= now
          and bool(re.fullmatch(r"[0-9a-f]{40}", str(audit.get("code_rev")))), "Audit ID, UTC start and full commit SHA required")
    evidence = doc.get("evidence") if isinstance(doc.get("evidence"), list) else []
    claims = doc.get("claims") if isinstance(doc.get("claims"), list) else []
    check("evidence_nonempty", bool(evidence), "At least one real observation required")
    check("claims_nonempty", bool(claims), "At least one bounded claim required")
    ids = [audit.get("id")] + [r.get("id") if isinstance(r, dict) else None for r in evidence + claims]
    check("unique_ids", all(nonempty(i) for i in ids) and len(set(map(str, ids))) == len(ids), "IDs unique across audit, evidence and claims")
    index = {}
    for position, ev in enumerate(evidence):
        if not isinstance(ev, dict):
            check(f"evidence.{position}.fields", False, "Evidence must be an object")
            continue
        eid = ev.get("id", str(position))
        prefix = f"evidence.{eid}"
        fields = {"id", "platform", "surface", "kind", "observed_at", "audit_id", "code_rev",
                  "source_locator", "artifact_path", "sample", "sha256", "limitations", "supported_capabilities"}
        check(prefix + ".fields", fields <= ev.keys() and ev.get("platform") in PLATFORMS
              and ev.get("surface") in SURFACES and ev.get("kind") in KINDS
              and nonempty(ev.get("source_locator")) and strings(ev.get("limitations"))
              and strings(ev.get("supported_capabilities")), "Required metadata, enums, limitations and reviewed capability scope")
        check(prefix + ".audit", ev.get("audit_id") == audit.get("id")
              and bool(re.fullmatch(r"[0-9a-f]{40}", str(ev.get("code_rev")))), "Evidence linked to audit with provenance commit")
        observed = instant(ev.get("observed_at"), day_allowed=ev.get("kind") != "current_runtime")
        check(prefix + ".observed_at", observed is not None and observed <= now
              and (ev.get("kind") != "current_runtime" or (started is not None and observed >= started)),
              "No future observations; current runtime must be within this audit; historical day precision remains explicit")
        path, sample = ev.get("artifact_path"), ev.get("sample")
        payload_ok = (nonempty(path) and sample is None) or (path is None and isinstance(sample, dict) and bool(sample))
        check(prefix + ".payload", payload_ok, "Exactly one readable file or nonempty redacted object")
        content = None
        if nonempty(path):
            try:
                file = (Path(root) / path).resolve()
                if Path(path).is_absolute() or not file.is_relative_to(Path(root).resolve()):
                    raise ValueError("Artifact must stay within repository root")
                content = file.read_bytes()
                check(prefix + ".artifact_readable", True, path)
            except (OSError, ValueError) as exc:
                check(prefix + ".artifact_readable", False, str(exc))
        elif path is None and isinstance(sample, dict) and sample:
            content = json.dumps(sample, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
        check(prefix + ".sha256", content is not None and hashlib.sha256(content).hexdigest() == ev.get("sha256"), "SHA-256 over exact file or canonical sample bytes")
        if nonempty(eid):
            index[eid] = ev

    for position, claim in enumerate(claims):
        if not isinstance(claim, dict):
            check(f"claim.{position}.fields", False, "Claim must be an object")
            continue
        prefix = f"claim.{claim.get('id', position)}"
        fields = {"id", "platform", "surface", "capability", "status", "temporal_scope", "evidence_ids", "limitations", "blocker"}
        check(prefix + ".fields", fields <= claim.keys() and claim.get("platform") in PLATFORMS
              and claim.get("surface") in SURFACES and claim.get("status") in STATUSES
              and claim.get("temporal_scope") in {"historical", "current"}
              and nonempty(claim.get("capability")) and strings(claim.get("limitations")), "Required claim fields, enum values and explicit limitations")
        refs = claim.get("evidence_ids")
        refs_ok = strings(refs) and all(ref in index for ref in refs)
        check(prefix + ".references", refs_ok, "Nonempty, closed evidence references required even for unknown claims")
        linked = [index[ref] for ref in refs if ref in index] if strings(refs) else []
        check(prefix + ".scope", bool(linked) and all(
            ev.get("platform") == claim.get("platform") and ev.get("surface") == claim.get("surface")
            and isinstance(ev.get("supported_capabilities"), list)
            and claim.get("capability") in ev["supported_capabilities"] for ev in linked),
            "Claim cannot exceed reviewed capability, platform or surface")
        check(prefix + ".runtime_support", claim.get("status") != "tested" or
              (bool(linked) and all(ev.get("kind") in {"historical_runtime", "current_runtime"} for ev in linked)),
              "Static/source evidence cannot establish tested behavior")
        current_ok = all(ev.get("kind") != "historical_runtime" and
                         instant(ev.get("observed_at")) is not None and started is not None and
                         instant(ev["observed_at"]) >= started for ev in linked)
        check(prefix + ".temporal_scope", claim.get("temporal_scope") != "current" or (bool(linked) and current_ok),
              "Historical observations cannot become current by updating audit date")
        blocker = claim.get("blocker")
        blocker_ok = blocker is None and claim.get("status") != "blocked"
        if isinstance(blocker, dict):
            blocker_refs = blocker.get("evidence_ids")
            blocker_ok = (blocker.get("kind") in {"missing_access", "missing_archive", "contract_unproven", "incompatible", "unsupported"}
                          and nonempty(blocker.get("reason")) and strings(blocker.get("attempted"))
                          and nonempty(blocker.get("next_action")) and strings(blocker_refs)
                          and refs_ok and set(blocker_refs) <= set(refs))
        check(prefix + ".blocker", blocker_ok, "Blockers require reason, attempted checks, evidence and next action")
    counts = {"evidence": len(evidence), "claims": len(claims)}
    if stage in {"matrix", "steps", "controls", "final"}:
        valid_claims = [c for c in claims if isinstance(c, dict)]
        coverage = sorted({f"{c.get('platform')}/{c.get('surface')}" for c in valid_claims
                           if c.get("platform") in {"libtv", "oiioii", "seko"}
                           and c.get("surface") in {"canvas", "editor", "agent_skill"}})
        counts["coverage"] = coverage
        check("matrix.coverage", len(coverage) == 9, "Three platforms × canvas/editor/agent_skill; unknowns need evidence too")
        for platform, capability in [("seko", "node_update_leaves_stale_shot"),
                                      ("oiioii", "clips_updated_source_reference_stale")]:
            check(f"matrix.{platform}_counterexample", any(c.get("platform") == platform
                  and c.get("capability") == capability and c.get("status") == "tested"
                  and c.get("temporal_scope") == "historical" for c in valid_claims),
                  "Retain observed stale references as a bounded historical counterexample")
        try:
            report = (Path(root) / REPORT_PATH).read_text(encoding="utf-8")
            check("matrix.report_readable", True, REPORT_PATH)
        except OSError as exc:
            report = ""
            check("matrix.report_readable", False, str(exc))
        rows = [line for line in report.splitlines() if line.startswith("|")
                and not re.fullmatch(r"[| :\-]+", line) and not line.startswith("| claim_id |")]
        row_ids = [re.findall(r"claim_id:([a-zA-Z0-9_-]+)", line) for line in rows]
        actual_ids = [ids[0] for ids in row_ids if len(ids) == 1]
        wanted_ids = [c.get("id") for c in valid_claims]
        check("matrix.report_claim_ids", bool(rows) and all(len(ids) == 1 for ids in row_ids)
              and len(actual_ids) == len(set(actual_ids)) and set(actual_ids) == set(wanted_ids),
              "Exactly one indexed claim per report data row; no missing or extra IDs")
        by_id = {c.get("id"): c for c in valid_claims if nonempty(c.get("id"))}
        check("matrix.report_evidence_ids", bool(rows) and all(len(ids) == 1 and ids[0] in by_id
              and set(re.findall(r"\bev-[a-zA-Z0-9_-]+", row)) == set(by_id[ids[0]].get("evidence_ids", []))
              for row, ids in zip(rows, row_ids)), "Report evidence IDs must match each indexed claim")
    comparison_complete = False
    if stage in {"build", "candidates", "steps", "controls", "final", "gate"}:
        validate_build(build, audit, index, now, check, counts)
    if stage in {"candidates", "steps", "controls", "final", "gate"}:
        comparison_complete = validate_candidates(doc, index, now, check, counts)
    if stage in {"steps", "controls", "final"}:
        validate_steps(doc, build, index, check, counts)
    if stage in {"controls", "final"}:
        validate_controls(doc, index, now, check)
    feasibility, complete = "unassessed", False
    if stage == "final":
        feasibility, complete = validate_final(doc, build, index, now, comparison_complete, check)
    gap = None
    if require_gap_closure or stage == "gate" or "gap_profile" in doc:
        gap = validate_gap_gate(doc, build, index, now, check)
    valid = all(c["passed"] for c in checks)
    if gap is not None and not valid:
        gap = dict(gap, tracer_complete=False, control_gate_complete=False, channel_ready=False)
    return {"contract_valid": valid, "stage": stage, "checks": checks, "counts": counts,
            "gap": gap,
            "comparison_complete": comparison_complete,
            "feasibility": feasibility if valid else "unassessed", "report_complete": complete and valid,
            "ready_for_phase2": valid and complete and feasibility == "feasible"}


def validate_gap_gate(doc, build, index, now, check):
    """Bind a real protocol roundtrip. Pending evidence never grants dispatch authority.

    Dual-candidate coverage remains closed until task 01-04-02 is accepted.
    Hashes and synthetic tests do not establish the truth of recorded observations.
    """
    profile = doc.get("gap_profile")
    result = {"tracer_complete": False, "control_gate_complete": False, "channel_ready": False}
    if not isinstance(profile, dict):
        check("gap.profile", False, "Required gap_profile missing")
        return result
    candidates = [c.get("id") for c in doc.get("candidates", []) if isinstance(c, dict)]
    expected = profile.get("expected_candidate_ids")
    check("gap.profile", profile.get("schema_version") == 1
          and nonempty(profile.get("source_audit_id"))
          and profile.get("purpose") == "phase1_boundary_evidence"
          and isinstance(profile.get("reference_set"), list)
          and isinstance(profile.get("candidate_runs"), list), "Explicit gap audit contract")
    check("gap.candidates", strings(expected) and len(set(expected)) == len(expected)
          and set(expected) == set(candidates), "Candidate identities cannot be borrowed")
    digest = profile.get("test_input_sha256")
    check("gap.input", isinstance(digest, str) and bool(re.fullmatch(r"[0-9a-f]{64}", digest))
          and digest == doc.get("selection", {}).get("test_input", {}).get("sha256"), "Original input hash")
    trials = profile.get("protocol_trials")
    check("gap.trials", isinstance(trials, list), "Trials must be a list; empty is pending")
    audit = doc.get("audit", {})
    started = instant(audit.get("started_at"))
    b = build if isinstance(build, dict) else {}
    modules = {m.get("id") for m in b.get("modules", []) if isinstance(m, dict) and m.get("origin_kind") == "current"}
    proven = []
    for trial in trials if isinstance(trials, list) else []:
        if not isinstance(trial, dict):
            check("gap.trial.fields", False, "Trial object required")
            continue
        name = "gap.trial." + str(trial.get("id"))
        check(name + ".identity", nonempty(trial.get("id")) and trial.get("candidate_id") in candidates
              and trial.get("conclusion") in {"proven", "pending-evidence", "technical-blocked"}
              and strings(trial.get("limitations")), "Bound candidate and honest conclusion")
        window = trial.get("window") if isinstance(trial.get("window"), dict) else {}
        first, last = instant(window.get("start")), instant(window.get("end"))
        times = [instant(t) for t in trial.get("timestamps", [])] if isinstance(trial.get("timestamps"), list) else []
        refs = trial.get("evidence_ids")
        linked = [index[r] for r in refs if r in index] if strings(refs) else []
        artifact = trial.get("external_artifact") if isinstance(trial.get("external_artifact"), dict) else {}
        replacement = trial.get("replacement") if isinstance(trial.get("replacement"), dict) else {}
        complete = (trial.get("audit_id") == audit.get("id") == b.get("audit_id")
            and strings(trial.get("build_module_ids")) and set(trial["build_module_ids"]) <= modules
            and all(nonempty(trial.get(k)) for k in ["existing_run_id", "request_id", "step_id", "method", "path", "event",
                "authority_source", "waiting_identity", "acceptance_receipt", "resume_input_identity", "resume_output_identity", "next_gate"])
            and trial.get("dispatch_authority") == "execution_layer" and trial.get("timing") == "pre_dispatch"
            and trial.get("vendor_task_state") == "observed_not_created"
            and replacement.get("acceptance_kind") == "generation_result"
            and nonempty(replacement.get("pending_tool_call_id"))
            and replacement.get("pending_tool_call_id") == replacement.get("accepted_tool_call_id") == trial.get("step_id")
            and strings(replacement.get("output_node_ids"))
            and nonempty(artifact.get("identity")) and bool(re.fullmatch(r"[0-9a-f]{64}", str(artifact.get("sha256"))))
            and window.get("complete") is True and started is not None and first is not None and last is not None
            and started <= first <= last <= now and (now - first).total_seconds() <= 86400
            and len(times) == 3 and all(t is not None for t in times)
            and first <= times[0] < times[1] < times[2] <= last
            and references(refs, index) and any(ev.get("kind") == "current_runtime"
                and ev.get("audit_id") == audit.get("id") and instant(ev.get("observed_at")) is not None
                and last <= instant(ev["observed_at"]) <= now
                and isinstance(ev.get("sample"), dict) and ev["sample"].get("protocol_trial") == trial
                and server_completion_matches(ev["sample"].get("server_observation"), trial, replacement)
                for ev in linked))
        check(name + ".proven", trial.get("conclusion") != "proven" or complete,
              "Server completion of the same tool/output and next gate required; client completion and stream replay are insufficient")
        if complete and trial.get("conclusion") == "proven":
            proven.append(trial["id"])
    result["tracer_complete"] = bool(proven)
    channel = profile.get("execution_channel")
    check("gap.channel", isinstance(channel, dict) and channel.get("kind") in {None, "existing_native_protocol", "isolated_observation"},
          "Unknown channel kind stays null; declarations do not confer readiness")
    if isinstance(channel, dict):
        refs = channel.get("protocol_trial_ids")
        result["channel_ready"] = (channel.get("kind") in {"existing_native_protocol", "isolated_observation"}
            and all(nonempty(channel.get(k)) for k in ["source_locator", "actual_entrypoint"])
            and strings(channel.get("capability_scope")) and strings(refs) and set(refs) <= set(proven))
        check("gap.channel_ready", channel.get("ready") is not True or result["channel_ready"], "Channel readiness is derived")
    return result


def server_completion_matches(observation, trial, replacement):
    """Validate normalized server evidence, not optimistic client events.

    This is an evidence contract, not a Seko request format. Its assertions must
    still be reviewed against the captured server response; no schema can make
    a fabricated observation true.
    """
    return (isinstance(observation, dict)
        and observation.get("source") in {"server_run_detail", "server_sse"}
        and observation.get("event") == "ToolCallCompleted"
        and observation.get("run_id") == trial.get("existing_run_id")
        and observation.get("tool_call_id") == replacement.get("pending_tool_call_id")
        and strings(observation.get("output_node_ids"))
        and strings(replacement.get("output_node_ids"))
        and set(observation["output_node_ids"]) == set(replacement["output_node_ids"])
        and nonempty(observation.get("next_gate"))
        and observation["next_gate"] == trial.get("next_gate")
        and observation["next_gate"] != trial.get("waiting_identity"))


def references(refs, index):
    return strings(refs) and all(r in index for r in refs)


def acyclic(records):
    graph = {r["id"]: r.get("depends_on") for r in records if isinstance(r, dict) and nonempty(r.get("id"))}
    if not all(isinstance(ds, list) and all(isinstance(d, str) and d in graph for d in ds) for ds in graph.values()):
        return False
    remaining = set(graph)
    while remaining:
        ready = {r for r in remaining if not (set(graph[r]) & remaining)}
        if not ready:
            return False
        remaining -= ready
    return True


def validate_steps(doc, build, index, check, counts):
    steps = doc.get("steps") if isinstance(doc.get("steps"), list) else []
    selection = doc.get("selection", {})
    selected = selection.get("status") == "selected"
    ids = [s.get("id") for s in steps if isinstance(s, dict)]
    candidates = {c.get("id") for c in doc.get("candidates", []) if isinstance(c, dict)}
    modules = {m.get("id") for m in (build or {}).get("modules", []) if isinstance(m, dict)}
    counts["steps"] = len(steps)
    check("steps.ids", bool(ids) and len(ids) == len(steps) and all(nonempty(i) for i in ids)
          and len(set(ids)) == len(ids), "Nonempty unique independent facts or selected steps")
    check("steps.selection", (bool(steps) and any(s.get("required") is True for s in steps)
          if selected else all(s.get("required") is False and isinstance(s.get("blocker"), dict) for s in steps)),
          "Blocked selection permits only independent, non-required investigation records")
    check("steps.dependencies", acyclic(steps), "Dependencies must exist and be acyclic")
    for s in steps:
        if not isinstance(s, dict):
            continue
        p = "step." + str(s.get("id"))
        fields = {"id", "candidate_id", "name", "stage", "required", "inputs", "outputs", "trigger", "initiator",
                  "executor", "states", "failure_semantics", "manual_actions", "depends_on", "evidence_ids",
                  "build_module_ids", "control", "blocker"}
        check(p + ".fields", fields <= s.keys() and nonempty(s.get("name")) and type(s.get("required")) is bool
              and s.get("stage") in {"writing", "storyboard", "image", "video", "voice", "lipsync", "edit", "export", "review"}
              and s.get("initiator") in {"browser", "server", "user", "unknown"}
              and s.get("executor") in {"vendor", "flow", "local", "unknown"}
              and references(s.get("evidence_ids"), index), "Explicit fields; unknown execution must not default to success")
        check(p + ".candidate", s.get("candidate_id") in candidates and
              (not selected or s.get("candidate_id") == selection.get("candidate_id")), "Real candidate; selected flow must match selection")
        check(p + ".build", strings(s.get("build_module_ids")) and
              all(m in modules for m in s["build_module_ids"]), "Closed build observation references, not compatibility proof")
        def port_ok(port):
            if not isinstance(port, dict):
                return False
            source = port.get("source")
            source_ok = source in {"unknown", "user", "vendor", "flow", "local"} if isinstance(source, str) else False
            if isinstance(source, str) and source.startswith("step:"):
                source_ok = source[5:] in s.get("depends_on", [])
            return ({"name", "source", "fields", "media_identity", "evidence_ids"} <= port.keys()
                    and nonempty(port.get("name")) and source_ok and strings(port.get("fields"))
                    and nonempty(port.get("media_identity")) and references(port.get("evidence_ids"), index))
        check(p + ".ports", all(isinstance(s.get(k), list) and bool(s[k]) and all(port_ok(x) for x in s[k])
              for k in ["inputs", "outputs"]), "Ports retain explicit unknowns or closed upstream sources")
        t = s.get("trigger") if isinstance(s.get("trigger"), dict) else {}
        check(p + ".trigger", all(nonempty(t.get(k)) for k in ["method", "path", "event"])
              and references(t.get("evidence_ids"), index), "Trigger fields and evidence required")
        check(p + ".semantics", all(isinstance(s.get(k), list) and bool(s[k]) and all(isinstance(x, dict)
              and nonempty(x.get("value")) and references(x.get("evidence_ids"), index) for x in s[k])
              for k in ["states", "failure_semantics"]), "Observed strings or explicit unknown, with provenance")
        actions = s.get("manual_actions")
        check(p + ".actions", isinstance(actions, list) and bool(actions) and all(isinstance(a, dict)
              and nonempty(a.get("action")) and references(a.get("evidence_ids"), index)
              and (a.get("count") is None or type(a.get("count")) is int and a["count"] >= 0
                   and any(isinstance(index[r].get("sample"), dict) and
                       {"stage": s.get("stage"), "action": a["action"], "count": a["count"]}
                       in index[r]["sample"].get("manual_actions_observed", []) for r in a["evidence_ids"]))
              for a in actions), "Numeric manual counts require observation; unknown remains null")
        b = s.get("blocker")
        check(p + ".blocker", b is None or isinstance(b, dict) and b.get("kind") in
              {"missing_access", "missing_archive", "contract_unproven", "incompatible", "unsupported"}
              and all(nonempty(b.get(k)) for k in ["reason", "next_action"]) and strings(b.get("attempted"))
              and references(b.get("evidence_ids"), index), "Concrete blocker with attempts and next evidence")


def known(value):
    return nonempty(value) and value.strip().lower() not in {"unknown", "unverified", "not_exposed"}


def control_proof(step, index, now, outcome):
    c = step.get("control", {})
    refs = c.get("evidence_ids", [])
    for ref in refs if isinstance(refs, list) else []:
        ev = index.get(ref, {})
        observed = instant(ev.get("observed_at"))
        sample = ev.get("sample")
        proof = sample.get("control_observation", {}) if isinstance(sample, dict) else {}
        if (ev.get("kind") == "current_runtime" and observed is not None
                and 0 <= (now - observed).total_seconds() <= 86400
                and proof.get("step_id") == step.get("id") and proof.get("executor") == step.get("executor")
                and proof.get("outcome") == outcome and known(proof.get("reason"))
                and proof.get("build_module_ids") == step.get("build_module_ids")
                and all(proof.get(k) == c.get(k) for k in
                        ["timing", "mechanism", "input_contract", "output_contract", "resume_contract"])
                and proof.get("dispatch_authority") == "execution_layer"
                and proof.get("dispatch_state") == c.get("dispatch_observation", {}).get("state")
                and ref in c.get("dispatch_observation", {}).get("evidence_ids", [])):
            return True
    return False


def validate_controls(doc, index, now, check):
    for s in doc.get("steps", []):
        if not isinstance(s, dict):
            continue
        p = "control." + str(s.get("id"))
        c = s.get("control") if isinstance(s.get("control"), dict) else {}
        d = c.get("dispatch_observation") if isinstance(c.get("dispatch_observation"), dict) else {}
        check(p + ".fields", c.get("status") in {"proven", "blocked", "unproven", "not_applicable"}
              and c.get("timing") in {"pre_dispatch", "post_dispatch", "unknown", "not_applicable"}
              and all(nonempty(c.get(k)) for k in ["mechanism", "input_contract", "output_contract", "resume_contract"])
              and references(c.get("evidence_ids"), index) and references(d.get("evidence_ids"), index)
              and d.get("state") in {"observed_not_created", "created", "unknown"}, "Explicit control and dispatch contract")
        check(p + ".proven", c.get("status") != "proven" or (
              c.get("timing") == "pre_dispatch" and d.get("state") == "observed_not_created"
              and s.get("executor") in {"vendor", "flow", "local"}
              and all(known(c.get(k)) for k in ["mechanism", "input_contract", "output_contract", "resume_contract"])
              and control_proof(s, index, now, "proven")),
              "Current execution-layer proof must bind timing, uncreated vendor task and all contracts; browser silence is insufficient")
        blocker = s.get("blocker") if isinstance(s.get("blocker"), dict) else {}
        check(p + ".blocked", c.get("status") != "blocked" or (
              blocker.get("kind") in {"incompatible", "unsupported"}
              and s.get("executor") in {"vendor", "flow", "local"} and control_proof(s, index, now, "blocked")),
              "Technical blocking requires actual protocol/execution proof, not access or evidence absence")
        check(p + ".applicability", c.get("status") != "not_applicable" or (
              s.get("stage") not in {"image", "video"} and s.get("executor") == "vendor"
              and c.get("timing") == "not_applicable"), "Retained vendor service is not automatically a replacement failure")
        if s.get("stage") not in {"image", "video"}:
            media = s.get("retained_media") if isinstance(s.get("retained_media"), dict) else {}
            check(p + ".retained_media", media.get("status") in {"observed", "unknown"}
                  and nonempty(media.get("media_source_effect")) and nonempty(media.get("protection_impact"))
                  and references(media.get("evidence_ids"), index)
                  and (media.get("status") != "observed" or any(index[r].get("kind") == "current_runtime"
                      and isinstance(index[r].get("sample"), dict)
                      and index[r]["sample"].get("retained_media_observation") == {
                          "step_id": s.get("id"), "media_source_effect": media["media_source_effect"],
                          "protection_impact": media["protection_impact"]} for r in media["evidence_ids"])),
                  "Current retained-service media effects and protection impacts need independent observations")


def validate_final(doc, build, index, now, comparison_complete, check):
    steps = {s.get("id"): s for s in doc.get("steps", []) if isinstance(s, dict) and nonempty(s.get("id"))}
    required = [s for s in steps.values() if s.get("required") is True]
    items = doc.get("integration_items", [])
    ids = [x.get("id") for x in items if isinstance(x, dict)]
    check("final.integration_ids", bool(ids) and len(ids) == len(items) and all(nonempty(i) for i in ids)
          and len(set(ids)) == len(ids), "Nonempty unique integration records")
    check("final.integration_coverage", all(any(isinstance(i, dict) and i.get("step_id") == s["id"] for i in items)
          for s in required), "Every required step mapped to an integration responsibility")
    check("final.integration_dependencies", acyclic(items), "Integration dependencies must exist and be acyclic")
    for i in items:
        if not isinstance(i, dict):
            continue
        p = "integration." + str(i.get("id"))
        check(p + ".fields", {"id", "step_id", "owner_phase", "disposition", "inputs", "outputs", "depends_on",
              "acceptance", "evidence_ids", "blocker"} <= i.keys() and i.get("step_id") in steps
              and type(i.get("owner_phase")) is int and 1 <= i["owner_phase"] <= 6
              and i.get("disposition") in {"replace_generation", "retain_vendor", "backfill", "observe", "block"}
              and all(strings(i.get(k)) for k in ["inputs", "outputs", "acceptance"])
              and references(i.get("evidence_ids"), index), "Closed step, owner, ports, acceptance and evidence")
        step = steps.get(i.get("step_id"), {})
        check(p + ".responsibility", (i.get("owner_phase") != 1 or i.get("disposition") in {"observe", "block"})
              and (i.get("disposition") != "replace_generation" or step.get("stage") in {"image", "video"}
                   and i.get("owner_phase") == 2)
              and (i.get("disposition") != "backfill" or i.get("owner_phase") == 3)
              and (i.get("disposition") != "retain_vendor" or step.get("stage") not in {"image", "video"}),
              "Investigation is Phase1; generation Phase2; backfill Phase3; preserve native services")
    for sid in steps:
        dispositions = {i.get("disposition") for i in items if isinstance(i, dict) and i.get("step_id") == sid}
        check("integration." + sid + ".consistent", not {"replace_generation", "retain_vendor"} <= dispositions,
              "Same task cannot both replace and retain generation")

    routes = doc.get("model_routes") if isinstance(doc.get("model_routes"), list) else []
    route_ids = [r.get("id") for r in routes if isinstance(r, dict)]
    check("final.routes", bool(routes) and len(route_ids) == len(routes) and all(nonempty(r) for r in route_ids)
          and len(set(route_ids)) == len(route_ids)
          and set(steps) <= {r.get("step_id") for r in routes if isinstance(r, dict)}, "Every recorded category has a model/provenance route")
    for r in routes:
        if not isinstance(r, dict):
            continue
        p = "route." + str(r.get("id"))
        check(p + ".fields", r.get("step_id") in steps and r.get("task_type") == steps.get(r.get("step_id"), {}).get("stage")
              and all(nonempty(r.get(k)) for k in ["current_provider", "current_model_key", "target_provider",
                  "target_model_key", "execution_level", "notes"])
              and isinstance(r.get("parameters"), dict) and references(r.get("evidence_ids"), index)
              and strings(r.get("candidate_ids")) and set(r["candidate_ids"]) <=
                  {c.get("id") for c in doc.get("candidates", []) if isinstance(c, dict)}
              and r.get("automatic_substitution") is False, "Exact keys or explicit unknown; no substitution; closed provenance")
        if r.get("target_provider") == "Flow" and known(r.get("target_model_key")):
            samples = [index[x].get("sample", {}) for x in r.get("evidence_ids", []) if x in index]
            keys = set()
            parameters = r.get("parameters") if isinstance(r.get("parameters"), dict) else {}
            for sample in samples:
                if isinstance(sample, dict):
                    if r.get("task_type") == "image":
                        catalog = sample.get("image_models")
                        name = parameters.get("configured_name")
                        if isinstance(catalog, dict) and known(name) and known(catalog.get(name)):
                            keys.add(catalog[name])
                    elif r.get("task_type") == "video":
                        catalog = sample.get("omni_flash_models")
                        mode, duration = parameters.get("mode"), parameters.get("duration_seconds")
                        if isinstance(catalog, dict) and known(mode) and type(duration) is int:
                            modes = catalog.get(mode)
                            if isinstance(modes, dict) and known(modes.get(str(duration))):
                                keys.add(modes[str(duration)])
            check(p + ".model_source", r.get("target_model_key") in keys,
                  "Flow key must match the task-specific configured image name or exact video mode and duration")

    h = doc.get("handoff") if isinstance(doc.get("handoff"), dict) else {}
    policies = {"quality_retry_limit": 2, "retry_model_policy": "same_model",
        "unknown_submit_policy": "reconcile_before_resubmit", "pause_policy": "failed_scene_and_dependents",
        "independent_policy": "continue", "final_export_policy": "all_scenes_passed"}
    check("final.policy", all(h.get(k) == v for k, v in policies.items())
          and type(h.get("quality_retry_limit")) is int, "Two quality retries after initial generation; unknown submissions reconcile first")
    check("final.decisions", strings(h.get("decision_ids")) and
          {"D-02", "D-03", "D-04", "D-09", "D-10", "D-11", "D-12", "D-14"} <= set(h["decision_ids"]), "Confirmed user decisions retained")
    check("final.owners", h.get("owner_phases") == {"generation": [2], "backfill": [3], "scheduling": [3, 4],
          "voice_acceptance": [5], "overall_acceptance": [6]}, "Explicit later-phase implementation ownership")

    def trigger_proven(s):
        trigger = s.get("trigger", {})
        if not all(known(trigger.get(k)) for k in ["method", "path", "event"]):
            return False
        expected = dict(step_id=s.get("id"), **{k: trigger[k] for k in ["method", "path", "event"]})
        candidate = next((c for c in doc.get("candidates", [])
                          if isinstance(c, dict) and c.get("id") == s.get("candidate_id")), {})
        audit = doc.get("audit", {})
        started = instant(audit.get("started_at"))
        for ref in trigger.get("evidence_ids", []):
            ev = index.get(ref, {})
            sample, observed = ev.get("sample"), instant(ev.get("observed_at"))
            if (ev.get("kind") == "current_runtime" and ev.get("audit_id") == audit.get("id")
                    and started is not None and observed is not None and started <= observed <= now
                    and (now - observed).total_seconds() <= 86400 and isinstance(sample, dict)
                    and sample.get("candidate_id") == candidate.get("id")
                    and nonempty(candidate.get("run_id")) and sample.get("run_id") == candidate["run_id"]
                    and sample.get("test_input_sha256") == doc.get("selection", {}).get("test_input", {}).get("sha256")
                    and sample.get("trigger_observation") == expected):
                return True
        return False

    def fully_observed(s):
        return (s.get("initiator") in {"browser", "server", "user"} and s.get("executor") in {"vendor", "flow", "local"}
            and trigger_proven(s)
            and all(known(p.get("source")) and known(p.get("media_identity")) and all(known(f) for f in p.get("fields", []))
                    for p in s.get("inputs", []) + s.get("outputs", []))
            and all(known(x.get("value")) for k in ["states", "failure_semantics"] for x in s.get(k, []))
            and all(a.get("count") is not None for a in s.get("manual_actions", [])))

    selection = doc.get("selection", {})
    coverage = {"candidate_id": selection.get("candidate_id"), "step_ids": sorted(steps), "complete": True}
    coverage_proven = any(ev.get("kind") == "current_runtime" and isinstance(ev.get("sample"), dict)
        and ev["sample"].get("workflow_coverage") == coverage and instant(ev.get("observed_at")) is not None
        and 0 <= (now - instant(ev["observed_at"])).total_seconds() <= 86400 for ev in index.values())
    generation = [s for s in required if s.get("stage") in {"image", "video"}]
    complete = (selection.get("status") == "selected" and comparison_complete and bool(required)
        and bool(generation) and coverage_proven and all(fully_observed(s) for s in required)
        and all(s.get("control", {}).get("status") in {"proven", "blocked"} for s in generation)
        and all(s.get("retained_media", {}).get("status") == "observed" for s in required
                if s.get("stage") not in {"image", "video"})
        and all(not s.get("blocker") or s["blocker"].get("kind") in {"unsupported", "incompatible"} for s in required))
    feasibility = "unassessed"
    if complete:
        if any(s["control"]["status"] == "blocked" for s in generation):
            feasibility = "blocked"
        elif isinstance(build, dict) and build.get("bridge", {}).get("status") == "ready":
            feasibility = "feasible"
        else:
            complete = False
    check("final.conclusion", h.get("feasibility") == feasibility and h.get("evidence_complete") is complete
          and h.get("comparison_complete") is comparison_complete,
          "Feasibility, evidence and comparison are derived independently; empty required sets never certify")
    scope = h.get("scope_decision") if isinstance(h.get("scope_decision"), dict) else {}
    check("final.scope", scope.get("status") in {"not_needed", "pending_evidence", "requires_decision"}
          and all(strings(scope.get(k)) for k in ["affected_scope", "required_evidence", "candidate_adjustments"])
          and isinstance(h.get("unresolved"), list)
          and (feasibility == "feasible" or strings(h.get("unresolved")))
          and (feasibility != "blocked" or scope.get("status") == "requires_decision"),
          "Technical blocking requires scope decision; incomplete evidence remains pending, never silently changes scope")
    return feasibility, complete


def validate_candidates(doc, index, now, check, counts):
    candidates = doc.get("candidates") if isinstance(doc.get("candidates"), list) else []
    selection = doc.get("selection") if isinstance(doc.get("selection"), dict) else {}
    test = selection.get("test_input") if isinstance(selection.get("test_input"), dict) else {}
    text = test.get("text")
    check("candidates.test_input", nonempty(test.get("id")) and nonempty(text) and nonempty(test.get("purpose"))
          and hashlib.sha256(text.encode()).hexdigest() == test.get("sha256") if isinstance(text, str) else False,
          "Same complete original input, purpose and UTF-8 SHA-256")
    counts["candidates"] = len(candidates)
    ids = [c.get("id") for c in candidates if isinstance(c, dict)]
    check("candidates.ids", bool(ids) and len(ids) == len(candidates) and all(nonempty(i) for i in ids)
          and len(set(ids)) == len(ids), "Nonempty unique real candidate records")

    def refs_ok(refs):
        return strings(refs) and all(r in index for r in refs)

    def samples(refs):
        return [index[r]["sample"] for r in refs if r in index and isinstance(index[r].get("sample"), dict)] if strings(refs) else []

    def run_samples(refs, candidate):
        audit = doc.get("audit", {})
        started = instant(audit.get("started_at"))
        result = []
        for ref in refs if strings(refs) else []:
            ev = index.get(ref, {})
            sample, observed = ev.get("sample"), instant(ev.get("observed_at"))
            if (ev.get("kind") == "current_runtime" and ev.get("audit_id") == audit.get("id")
                    and started is not None and observed is not None and started <= observed <= now
                    and (now - observed).total_seconds() <= 86400 and isinstance(sample, dict)
                    and sample.get("candidate_id") == candidate.get("id")
                    and nonempty(candidate.get("run_id")) and sample.get("run_id") == candidate["run_id"]
                    and sample.get("test_input_sha256") == test.get("sha256")):
                result.append(sample)
        return result

    origins, runtime_ready = set(), True
    for pos, c in enumerate(candidates):
        if not isinstance(c, dict):
            check(f"candidate.{pos}.fields", False, "Candidate object required")
            runtime_ready = False
            continue
        prefix = "candidate." + str(c.get("id", pos))
        fields = {"id", "origin", "author", "source_locator", "source_evidence_ids", "accessible", "input_contract",
                  "output_stages", "manual_actions", "generation_entrypoints", "assembly_path", "observations", "limitations", "test_input_id"}
        check(prefix + ".fields", fields <= c.keys() and c.get("origin") in {"official", "community"}
              and nonempty(c.get("author")) and nonempty(c.get("source_locator")) and type(c.get("accessible")) is bool
              and all(nonempty(c.get(k)) for k in ["input_contract", "generation_entrypoints", "assembly_path"])
              and strings(c.get("limitations")), "Explicit candidate source, author, contracts and limitations")
        source_ok = refs_ok(c.get("source_evidence_ids")) and any(s.get("origin") == c.get("origin")
            and s.get("author") == c.get("author") for s in samples(c.get("source_evidence_ids")))
        check(prefix + ".source", source_ok, "Author/origin bound to reviewed source; creator and publisher may differ")
        if source_ok and c.get("accessible") is True:
            origins.add(c.get("origin"))
        check(prefix + ".input", c.get("test_input_id") == test.get("id"), "No candidate-specific rewritten input")
        outputs = c.get("output_stages")
        outputs_ok = isinstance(outputs, list) and bool(outputs) and all(isinstance(o, dict)
            and nonempty(o.get("stage")) and o.get("kind") in {"advertised", "observed"}
            and refs_ok(o.get("evidence_ids")) and (o["kind"] != "observed" or
                any(o["stage"] in s.get("observed_stages", []) for s in run_samples(o["evidence_ids"], c))) for o in outputs)
        check(prefix + ".output_stages", outputs_ok, "Advertised outputs cannot be promoted to observed execution")
        actions = c.get("manual_actions")
        actions_ok = isinstance(actions, list) and bool(actions) and all(isinstance(a, dict)
            and nonempty(a.get("stage")) and nonempty(a.get("action")) and refs_ok(a.get("evidence_ids"))
            and (a.get("count") is None or (type(a.get("count")) is int and a["count"] >= 0
                and any({k: a[k] for k in ["stage", "action", "count"]} in s.get("manual_actions_observed", [])
                        for s in run_samples(a["evidence_ids"], c)))) for a in actions)
        check(prefix + ".manual_actions", actions_ok, "Unknown count is null; every numeric count needs actual observation, including zero")
        obs = c.get("observations")
        check(prefix + ".observations", isinstance(obs, list) and bool(obs) and all(isinstance(o, dict)
              and o.get("kind") in {"advertised", "observed"} and nonempty(o.get("detail"))
              and refs_ok(o.get("evidence_ids")) for o in obs), "Separate observed access from advertised behavior")
        runtime_ready = runtime_ready and outputs_ok and actions_ok and bool(outputs) and bool(actions)
        if outputs_ok and actions_ok:
            runtime_ready = runtime_ready and all(o["kind"] == "observed" for o in outputs) and all(a.get("count") is not None for a in actions)
    complete = origins == {"official", "community"} and runtime_ready and bool(candidates)
    status = selection.get("status")
    check("candidates.selection", status in {"selected", "blocked"} and strings(selection.get("rationale"))
          and strings(selection.get("compared_ids")) and len(set(selection["compared_ids"])) == len(selection["compared_ids"])
          and set(selection["compared_ids"]) == set(ids)
          and ((status == "selected" and complete and selection.get("candidate_id") in ids and selection.get("blockers") == [])
               or (status == "blocked" and selection.get("candidate_id") is None and strings(selection.get("blockers")))),
          "Selection needs both sources and observed same-input comparison; blocked requires concrete gaps")
    return complete


def validate_build(build, audit, index, now, check, counts):
    """Compare recorded observations; never load website modules or infer replacements."""
    b = build if isinstance(build, dict) else {}
    started, observed = instant(audit.get("started_at")), instant(b.get("observed_at"))
    check("build.audit", b.get("audit_id") == audit.get("id") and started is not None
          and observed is not None and started <= observed <= now
          and (now - observed).total_seconds() <= 86400, "Current audit and sample within 24 hours")

    def linked(refs):
        return [index[r] for r in refs if r in index] if strings(refs) else []

    def references(refs):
        return strings(refs) and all(r in index for r in refs)

    context = b.get("context") if isinstance(b.get("context"), dict) else {}
    check("build.context", nonempty(b.get("page_locator"))
          and all(type(context.get(k)) is bool for k in ["login_observed", "project_observed"])
          and references(context.get("health_evidence_ids")), "Page, observed login/project and separate health evidence")
    modules = b.get("modules") if isinstance(b.get("modules"), list) else []
    counts["modules"] = len(modules)
    check("build.modules_nonempty", bool(modules), "Nonempty modules")
    module_ids = [m.get("id") for m in modules if isinstance(m, dict)]
    check("build.module_ids", len(module_ids) == len(modules) and all(nonempty(i) for i in module_ids)
          and len(set(module_ids)) == len(module_ids), "Unique module observation IDs")
    check("build.required_modules", all(any(isinstance(m, dict) and m.get("origin_kind") == "current"
          and str(m.get("locator", "")).endswith("/" + name)
          and set(m.get("required_exports", [])) == exports for m in modules)
          for name, exports in BRIDGE_EXPORTS.items()), "Every exact hardcoded dependency sampled; no guessed alias")
    for pos, m in enumerate(modules):
        if not isinstance(m, dict):
            check(f"build.module.{pos}.fields", False, "Module object required")
            continue
        prefix = "build.module." + str(m.get("id", pos))
        refs, when = m.get("evidence_ids"), instant(m.get("observed_at"), day_allowed=True)
        required, actual = m.get("required_exports"), m.get("observed_exports")
        check(prefix + ".fields", {"id", "origin_kind", "locator", "observed_at", "http_status", "content_type",
              "body_sha256", "required_exports", "observed_exports", "evidence_ids", "compatibility", "reason"} <= m.keys()
              and m.get("origin_kind") in {"archived", "cached", "current"}
              and m.get("compatibility") in {"matched", "mismatched", "unknown"}
              and nonempty(m.get("locator")) and nonempty(m.get("reason")) and references(refs)
              and isinstance(required, list) and all(nonempty(x) for x in required)
              and isinstance(actual, list) and all(nonempty(x) for x in actual)
              and when is not None and when <= now, "Explicit source, enums, exports, references and reason")
        evs = linked(refs)
        current = m.get("origin_kind") == "current"
        check(prefix + ".fresh", not current or (started is not None and when is not None
              and started <= when <= now and (now - when).total_seconds() <= 86400
              and bool(evs) and all(ev.get("kind") == "current_runtime"
                  and ev.get("audit_id") == audit.get("id") and instant(ev.get("observed_at")) == when for ev in evs)),
              "Current cannot be historical/cached, stale, future or from another audit")
        digest = m.get("body_sha256")
        check(prefix + ".hash_link", (digest is None and m.get("compatibility") == "unknown") or
              (isinstance(digest, str) and bool(re.fullmatch(r"[0-9a-f]{64}", digest))
               and any(isinstance(ev.get("sample"), dict) and ev["sample"].get("body_sha256") == digest for ev in evs)),
              "Response digest bound to a hashed redacted observation; absent bytes remain unknown")
        def media_type(value):
            return value.split(";", 1)[0].strip().lower() if isinstance(value, str) else value

        response_fields = {"locator", "http_status", "content_type", "body_sha256", "observed_exports"}
        responses = [ev["sample"] for ev in evs if isinstance(ev.get("sample"), dict)
                     and ev["sample"].get("body_sha256") == digest]

        def agrees(sample):
            return all((media_type(sample[k]) == media_type(m.get(k)) if k == "content_type"
                        else sample[k] == m.get(k)) for k in response_fields if k in sample)

        bound = any(response_fields <= s.keys() and agrees(s) for s in responses)
        check(prefix + ".response_binding", all(agrees(s) for s in responses)
              and (bound or m.get("compatibility") == "unknown"),
              "One hashed response binds URL, status, media type, bytes and exports; missing metadata stays unknown")
        matched = (bound and m.get("http_status") == 200 and media_type(m.get("content_type"))
                   in {"application/javascript", "text/javascript"} and digest is not None
                   and isinstance(required, list) and isinstance(actual, list) and set(required) <= set(actual))
        check(prefix + ".matched", m.get("compatibility") != "matched" or matched,
              "200 HTML, missing bytes or missing exports cannot match")
    bridge = b.get("bridge") if isinstance(b.get("bridge"), dict) else {}
    check("build.bridge", bridge.get("status") in {"ready", "blocked", "unknown"}
          and nonempty(bridge.get("reason")) and references(bridge.get("evidence_ids"))
          and bool(re.fullmatch(r"[0-9a-f]{40}", str(bridge.get("code_rev")))), "Separate bridge observation")
    check("build.bridge_ready", bridge.get("status") != "ready" or (
          context.get("login_observed") is True and context.get("project_observed") is True
          and all(m.get("compatibility") == "matched" for m in modules if isinstance(m, dict) and m.get("origin_kind") == "current")
          and any(ev.get("kind") == "current_runtime" and isinstance(ev.get("sample"), dict)
                  and ev["sample"].get("bridge_phase") == "ready" for ev in linked(bridge.get("evidence_ids")))),
          "Downloadable assets do not establish runtime bridge startup")


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main(argv=None):
    parser = JsonArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--stage", required=True, choices=sorted(STAGES))
    parser.add_argument("--build")
    parser.add_argument("--require-gap-closure", action="store_true")
    try:
        args = parser.parse_args(argv)
        document = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
        build = json.loads(Path(args.build).read_text(encoding="utf-8")) if args.build else None
        result = validate_evidence(document, Path.cwd(), args.stage, datetime.now(timezone.utc), build,
                                   require_gap_closure=args.require_gap_closure)
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"contract_valid": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["contract_valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
