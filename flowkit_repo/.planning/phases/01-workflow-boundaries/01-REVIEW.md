---
phase: 01-workflow-boundaries
reviewed: 2026-10-15T11:44:30Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - scripts/workflow_evidence_probe.py
  - tests/test_workflow_evidence_probe.py
  - docs/benchmarks/workflow-boundaries/evidence.json
  - docs/benchmarks/workflow-boundaries/current-build.json
  - docs/THREE-PLATFORM-LIVE-RESULTS.md
  - docs/SEKO-BUILD-COMPATIBILITY.md
  - docs/SEKO-WORKFLOW-BOUNDARIES.md
findings:
  critical: 4
  warning: 0
  info: 0
  total: 4
status: issues_found
---

# Phase 1: Code Review Report

**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

审查范围严格采用编排器提供的上述 7 文件。scope resolver 的已知状态为 `degraded / no-task-commit-rows`；没有据此扩大为任意 Git 范围。基线为 `d41d1455e5c951984f4eb9816f4979d8d299a76b`。三个 PLAN、三个 SUMMARY、CONTEXT 与 AGENTS.md 作为约束读取，不计入源文件范围。没有结构化 fallow 输入。

真实输入在注入时间 `2026-10-15T12:00:00Z` 的离线验证中保持 `contract_valid=true / report_complete=false / feasibility=unassessed / ready_for_phase2=false`，文档也保留了未执行及待证边界。本次不把缺少后续生产接入实现当作缺陷。以下四项都是检查器可重复的错误放行；真实记录当前没有因此被修改为通过。

`python3 -m unittest tests.test_workflow_evidence_probe -q`：62 tests，OK。额外反例使用已有测试 fixture 或实际 JSON 的内存副本，未修改源文件、证据、模型或线上状态；无安装、无网络请求、无提交。复现中的固定 `now` 只用于函数测试，不是 CLI 参数或重新采样声明。

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: 静态或不属于本候选同稿运行的样本可认证实际比较完成

**Classification:** BLOCKER
**File:** `/Users/niuniu/Desktop/flow cli/flowkit_repo/scripts/workflow_evidence_probe.py:486-498`

**Issue:** `samples()` 去掉证据层级，只提取 sample；observed 输出和数字人工次数只检查数组里存在同名阶段/动作。没有要求运行证据，也没有把运行记录绑定到候选身份与 `test_input` 哈希。`test_input_id` 相等只检查候选声明之间相等，不能证明被引用的运行使用了该输入。因此静态采样、其他候选或其他输入的历史结果可支撑 `comparison_complete=true` 与 selected，绕过本轮同稿实际比较门槛。

**Reproduction:** 导入 `WorkflowEvidenceProbeTests`，调用 `setUp(); candidates_fixture(selected=True)`；仅将 `ev-official` 和 `ev-community` 的 `kind` 改为 `static`（sample 与哈希不变）；调用 `result("candidates")`。实测返回 `contract_valid=true, comparison_complete=true`。这些样本原本也没有 candidate/run/input hash 绑定。

**Fix:** 为实际输出/人工计数建立明确运行证明，校验 runtime kind、适用审计时间、候选 ID、同稿 SHA-256 及运行 ID；宣传/来源样本继续允许 static，但不能用于实际比较完成。增加 static/source、错候选、错输入、过期运行的拒绝测试。不要仅改最外层布尔字段。

### CR-02: 构建行可与其已哈希的 404 证据矛盾而判 matched

**Classification:** BLOCKER
**File:** `/Users/niuniu/Desktop/flow cli/flowkit_repo/scripts/workflow_evidence_probe.py:568-577`

**Issue:** `hash_link` 只绑定 `body_sha256`，`matched` 却读取未与样本核对的 module 行 `http_status/content_type/observed_exports`。即使引用样本明确记录 404、text/plain、无导出，行上改写成 200、JavaScript、所需导出就能通过；定位 URL 也未参与同一响应绑定。哈希正确没有保证结论来自对应响应，破坏 BASE-03 的兼容证据门槛。

**Reproduction:** 读取实际 evidence/current-build JSON 到内存。将 `build["modules"][:3]` 各自改为 `http_status=200, content_type="application/javascript", observed_exports=required_exports, compatibility="matched"`，保留 evidence、原 404 内容哈希、引用与时间不变。以固定 now 调用 `validate_evidence(..., "build", now, build)`，实测 `contract_valid=true`；三个 `ev-build-http-*` 样本仍明确为 404。

**Fix:** 对同一个已哈希样本同时核对 locator、HTTP status、规范化 content type、body digest 与 observed exports；从绑定后的响应推导 matched。缺字段时保持 unknown，矛盾时拒绝。增加真实 404 样本配伪造 200 行、错 URL、错导出的测试。

### CR-03: 图片模型及错误视频模式/时长可通过视频路由校验

**Classification:** BLOCKER
**File:** `/Users/niuniu/Desktop/flow cli/flowkit_repo/scripts/workflow_evidence_probe.py:388-396`

**Issue:** 校验将所有图片 key 和所有 Omni 模式/时长 key 合并成一个集合，只检查 key 是否出现。`task_type`、`configured_name`、`mode`、`duration_seconds` 没有参与目录查找。因此视频可以指向 BELUGA，8 秒首帧任务也可以指向其他模式/时长，而仍被认证为有来源的精确路由。这违背明确模型/模式匹配且不得自动替换的交接约束。

**Reproduction:** 用实际 JSON 的内存副本，只把 `model_routes` 中 `task_type="video"` 的 `target_model_key` 从 `abra_i2v_8s` 改为 `BELUGA`，其余证据/参数不变。固定 now 下 final 实测仍 `contract_valid=true`。

**Fix:** 图片按 `image_models[configured_name]` 核对；视频按 `omni_flash_models[mode][str(duration_seconds)]` 精确核对，任务类型与目录必须匹配。未知参数可以保留待证，但不能认证精确映射。增加跨类型、错模式、错时长及图片别名与 key 不一致的反例。

### CR-04: 完整度判定遗漏未知触发合同，可错误解锁 Phase 2

**Classification:** BLOCKER
**File:** `/Users/niuniu/Desktop/flow cli/flowkit_repo/scripts/workflow_evidence_probe.py:409-424`

**Issue:** steps 的 trigger 校验只要求非空字符串，允许调查状态的 `unknown`；`fully_observed()` 没有在 final 完整度中补查 trigger。结果即使必需生成步骤的 method/path/event 全部未知，仍可 `report_complete=true`，并在其余门槛满足时 `ready_for_phase2=true`。有控制描述不能替代选中流程实际触发入口与时序合同。

**Reproduction:** 已有 `final_fixture("blocked")` 的 trigger 三项改为 `unknown`，得到 `contract_valid=true, report_complete=true, feasibility=blocked`。再用 `final_fixture("feasible")`，将 build.bridge.status 设置 ready，并在其引用的 `ev-build.sample` 加 `bridge_phase="ready"` 后重算规范化 sample 哈希；同样将 trigger 三项改 unknown，实测得到 `contract_valid=true, report_complete=true, feasibility=feasible, ready_for_phase2=true`。后者是合成正向基线的单字段组缺失测试，不是线上可行性声明。

**Fix:** 在完整度判定中要求所有 required 步骤的 trigger method/path/event 已知并有对应运行/协议证明；unknown 仍允许保存调查合同，但必须保持 incomplete/unassessed/ready=false。增加已完整正向 fixture 的未知 trigger 回归测试，同时验证 blocked 与 feasible 两条结论分支。

---

_Reviewer: gsd-code-reviewer_
_Review only; no source edits or commit._
