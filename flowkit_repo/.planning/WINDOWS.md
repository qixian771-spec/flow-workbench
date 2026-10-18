---
schema_version: 1
open_count: 2
waived_count: 0
fixed_count: 1
total_count: 3
last_updated: 2026-10-15T11:37:06.000Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 01 | deviation | scripts/workflow_evidence_probe.py |  | 为能力范围校验新增 supported_capabilities，已实现并通过反例测试。 | fixed |  | 2026-10-15T11:05:17.039Z | 2026-10-15T11:05:48.377Z |
| 2 | 01 | unmet-truth | docs/SEKO-WORKFLOW-BOUNDARIES.md |  | 双方真实执行输出与人工次数尚未观察；selection blocked，需生成前控制证据后再安全同稿验证。 | open |  | 2026-10-15T11:22:12.741Z |  |
| 3 | 01 | unmet-truth | docs/SEKO-WORKFLOW-BOUNDARIES.md |  | BASE-02/04 pending: candidate execution comparison and current pre-dispatch control not established; final unassessed and not ready. | open |  | 2026-10-15T11:37:06.000Z |  |

````json
[
  {
    "id": 1,
    "kind": "deviation",
    "phase": "01",
    "file": "scripts/workflow_evidence_probe.py",
    "line": null,
    "description": "为能力范围校验新增 supported_capabilities，已实现并通过反例测试。",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-10-15T11:05:17.039Z",
    "resolved_at": "2026-10-15T11:05:48.377Z",
    "milestone": null
  },
  {
    "id": 2,
    "kind": "unmet-truth",
    "phase": "01",
    "file": "docs/SEKO-WORKFLOW-BOUNDARIES.md",
    "line": null,
    "description": "双方真实执行输出与人工次数尚未观察；selection blocked，需生成前控制证据后再安全同稿验证。",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-15T11:22:12.741Z",
    "resolved_at": null,
    "milestone": null
  },
  {
    "id": 3,
    "kind": "unmet-truth",
    "phase": "01",
    "file": "docs/SEKO-WORKFLOW-BOUNDARIES.md",
    "line": null,
    "description": "BASE-02/04 pending: candidate execution comparison and current pre-dispatch control not established; final unassessed and not ready.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-15T11:37:06.000Z",
    "resolved_at": null,
    "milestone": null
  }
]
````
