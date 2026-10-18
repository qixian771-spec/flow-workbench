---
phase: 01-workflow-boundaries
fixed_at: 2026-10-15T11:51:19Z
review_path: .planning/phases/01-workflow-boundaries/01-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 1: Code Review Fix Report

**Source review:** `.planning/phases/01-workflow-boundaries/01-REVIEW.md`
**Iteration:** 1

| Finding | Disposition | RED | GREEN before final commit | Commit |
|---|---|---|---|---|
| CR-01 | fixed: requires human verification | 1 test, 9 failing subcases | 64 workflow tests | bd375ef |
| CR-02 | fixed: requires human verification | 2 tests, 5 failing subcases | 68 workflow tests | 5740ba6 |
| CR-03 | fixed: requires human verification | 1 test, 7 failing subcases | 71 workflow tests | 4dd0d79 |
| CR-04 | fixed: requires human verification | 2 tests, 10 failing subcases | 74 workflow tests | ecdad55 |

Four findings fixed; none skipped. All four concern decision logic: targeted regression tests verify the reported counterexamples, while human source/provenance verification remains required. Passing synthetic fixtures are not runtime observations.

## Fixed Issues

### CR-01: Candidate execution must belong to this audit and same-input run

**Files modified:** `scripts/workflow_evidence_probe.py`, `tests/test_workflow_evidence_probe.py`
**Commit:** bd375ef
**Status:** fixed: requires human verification

Observed outputs and numeric manual-action counts now require `current_runtime` evidence within the current audit and 24-hour window. The hashed sample must bind `candidate_id`, `run_id`, and `test_input_sha256`; its run must match the candidate's explicit `run_id`. Static/source metadata still supports candidate discovery, but cannot establish execution or complete comparison. Regression subcases cover static/source/historical evidence, stale time, wrong audit, candidate, input and missing/wrong run IDs.

### CR-02: Build compatibility must agree with the hashed response

**Files modified:** `scripts/workflow_evidence_probe.py`, `tests/test_workflow_evidence_probe.py`, `docs/benchmarks/workflow-boundaries/evidence.json`
**Commit:** 5740ba6
**Status:** fixed: requires human verification

One response sample must bind locator, HTTP status, normalized content type, body digest and observed exports before the module can claim matched or mismatched. Contradictory recorded fields fail `response_binding`; incomplete metadata only permits unknown. Matched additionally requires 200 JavaScript with the required exports.

Six existing HTTP samples were normalized by copying each already-recorded `source_locator` into `sample.locator` and recalculating the canonical sample SHA-256. No observation timestamp, body digest, status, export, or runtime conclusion was changed. Cached/archive samples keep their missing response metadata and unknown compatibility. This is a representation change, not a new observation or historical re-sampling.

Tests include status/type/URL/export contradictions, absent URL metadata, MIME normalization and the actual three 404 samples paired in memory with forged 200/matched module rows. Actual JSON is read-only in those tests.

### CR-03: Model routes require exact task-specific catalog lookup

**Files modified:** `scripts/workflow_evidence_probe.py`, `tests/test_workflow_evidence_probe.py`
**Commit:** 4dd0d79
**Status:** fixed: requires human verification

Image keys resolve exclusively through `image_models[configured_name]`. Video keys resolve exclusively through `omni_flash_models[mode][str(duration_seconds)]`, requiring an integer duration. Cross-type keys, wrong mode/duration, alias mismatches and unknown mode with a claimed exact key fail. An explicitly unknown target remains a valid pending record; there is no model substitution.

Execution deviation: the initial GREEN run exposed a synthetic video fixture whose manual-action evidence still said image. A tool-call sequencing error allowed the initial commit despite that failed run. The fixture was corrected, all 71 tests plus the real final-contract acceptance passed, and the unshared commit was amended to the final SHA above. No failing state remains at that commit. This deviation is recorded rather than claiming the initial commit followed a successful gate.

### CR-04: Unknown or unproven triggers prevent final completeness

**Files modified:** `scripts/workflow_evidence_probe.py`, `tests/test_workflow_evidence_probe.py`
**Commit:** ecdad55
**Status:** fixed: requires human verification

Every required step must have known trigger method/path/event and an exact `trigger_observation` containing those fields and the step ID, linked through trigger evidence to current same-candidate/same-input/same-run proof. Unknown trigger contracts remain saveable when handoff is honestly pending. Both blocked and feasible complete synthetic baselines are covered; unknown fields and mismatched trigger observations cannot establish completeness or Phase 2 readiness.

## Verification and Acceptance

All gates ran in the **main checkout** `/Users/niuniu/Desktop/flow cli/flowkit_repo`, as `workflow.use_worktrees=false`. No worktree or cleanup sentinel was created. Repository-root checks were used before commits. Only the explicitly owned files were staged; unrelated config, execution notes, review and extension files were preserved.

- Per-finding verification: re-read changed sections; `git diff --check`; `python3 -m py_compile scripts/workflow_evidence_probe.py tests/test_workflow_evidence_probe.py`; workflow unit tests as counted above.
- Final scoped Python regression: `python3 -m unittest tests.test_workflow_evidence_probe tests.test_seko_probe tests.test_seko_flow_job tests.test_platform_probe -q` — **107 tests, OK**.
- Final scoped Node regression: `node --test tests/test_seko_generation_hook.cjs tests/test_seko_resident_page.cjs tests/test_seko_native_backfill.cjs` — **16 tests passed, 0 failed, 0 skipped**.
- Real acceptance before each final finding commit: `python3 scripts/workflow_evidence_probe.py --evidence docs/benchmarks/workflow-boundaries/evidence.json --build docs/benchmarks/workflow-boundaries/current-build.json --stage final` using the actual clock, with parsed assertions: **contract_valid=true, report_complete=false, feasibility=unassessed, ready_for_phase2=false**.

No installs, network requests, native generation, production implementation, or new runtime evidence. No source edits remain uncommitted. This report is intentionally uncommitted for the parent workflow to commit separately. All four findings have an atomic final fix commit; actual workflow evidence remains pending.

_Fixer: gsd-code-fixer; iteration 1._
