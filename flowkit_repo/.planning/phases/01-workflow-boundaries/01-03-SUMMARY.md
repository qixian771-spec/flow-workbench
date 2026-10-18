---
phase: 01-workflow-boundaries
plan: "03"
subsystem: testing
tags: [workflow-boundaries, provenance, model-routing, handoff]
requires:
  - phase: 01-02
    provides: 当次构建证据与候选选择阻断
provides:
  - steps/controls/final离线契约检查与保守推进门槛
  - 九类独立调查事实和模型来源路由
  - 十九项后续接入责任与明确未完成报告
affects: [BASE-02, BASE-04, Phase-2]
tech-stack:
  added: []
  patterns: [standard-library-only, current-execution-proof, explicit-unknown]
key-files:
  created: []
  modified:
    - scripts/workflow_evidence_probe.py
    - tests/test_workflow_evidence_probe.py
    - docs/benchmarks/workflow-boundaries/evidence.json
    - docs/SEKO-WORKFLOW-BOUNDARIES.md
    - .planning/phases/01-workflow-boundaries/01-VALIDATION.md
key-decisions:
  - "selection=blocked时仅记录非required独立事实，禁止空required集合认证阶段完成。"
  - "当前执行层派发证明与配置/历史/静态事实分开；缺证据是unassessed，不是技术不可能。"
  - "图片目标BELUGA、首帧8秒Omni目标abra_i2v_8s只经配置核验，未宣称候选真实调用。"
requirements-completed: []
requirements-pending: [BASE-02, BASE-04]
actuals:
  tokens: 26209
  tasks: 3
  commits: 3
commits: 3
plan_head_before: a263ab72f94c7e2b55d5588c345c35695585def1
plan_head_after: 9414da6d586e9599ec272c2691a7c9654ac18825
duration: 12min
started: 2026-10-15T11:25:05Z
completed: 2026-10-15
status: complete
phase_goal_status: pending-evidence
---

# Phase 1 Plan 03: 可追溯步骤、控制门槛与模型路由 Summary

**九类独立调查记录、十九项后续责任和模型来源表已交付；真实final合同有效，但完整流程报告未完成，禁止推进Phase2。**

status=complete仅代表计划允许的独立事实/明确blocked记录和三张调查任务卡交付；不是BASE-02/04或Phase1目标完成。用户获得精确证据缺口与后续责任，没有伪造选中流程。实际tokens按三个任务diff的104835字符/4向上取整；commits从持久ledger实测3，不包含本摘要的metadata提交。

## Task Commits

| 卡片 | 交付 | 提交 |
| --- | --- | --- |
| 01-03-01 | 步骤合同、独立事实与九类模型路由 | 51a3622 |
| 01-03-02 | 当前执行层前置控制证明门槛、保留服务影响 | cc60a64 |
| 01-03-03 | final完整度/可行性/推进门槛及19项交接 | 9414da6 |

每卡RED→GREEN→来源验收→提交，正常hook，未跳过检查。父流程拥有阶段独立代码审查与验收。

## 测试与来源验收

完整单测命令：`python3 -m unittest tests.test_workflow_evidence_probe -v`（另以-q汇总运行）。真实证据命令前缀：`python3 scripts/workflow_evidence_probe.py --evidence docs/benchmarks/workflow-boundaries/evidence.json --build docs/benchmarks/workflow-boundaries/current-build.json`，三卡分别加`--stage steps`、`--stage controls`、`--stage final`。

| 卡片 | RED（退出1） | GREEN（退出0） | 实际证据验收 |
| --- | --- | --- | --- |
| 01-03-01 | test_steps_selected_and_independent_records_valid目标断言失败：未实现steps | 48 tests | steps true，9独立记录，选择仍blocked；对照当前UI、候选metadata、桥代码与配置 |
| 01-03-02 | test_controls_current_execution_proof_passes目标断言失败：未实现controls | 54 tests | controls true；所有真实control仍unproven，dispatch unknown；历史口型媒体变化独立标识 |
| 01-03-03 | test_final_incomplete_never_ready_or_complete目标断言失败：未实现final | 62 tests | final true；report_complete=false、feasibility=unassessed、ready_for_phase2=false、comparison_complete=false |

三个真实RED记录位于`output/workflow-boundaries-01-03/task1-red.json`、`task2-red.json`、`task3-red.json`，均由`node /Users/niuniu/.codex/gsd-core/bin/gsd-tools.cjs check tdd-red-evidence <path> --raw`分类为RED_EVIDENCE_OK。目标确实执行并因期望契约行为断言失败，没有加载/fixture错误。用户明确禁止提交未通过RED，因此只提交GREEN后的原子卡片。

最终回归：`python3 -m unittest tests.test_workflow_evidence_probe tests.test_seko_probe tests.test_seko_flow_job tests.test_platform_probe -q`退出0，95 tests；`node --test tests/test_seko_generation_hook.cjs tests/test_seko_resident_page.cjs tests/test_seko_native_backfill.cjs`退出0，16 pass/0 fail/0 skip。`git diff --check`通过；新文档/证据无Bearer或签名参数匹配。未声称全仓测试通过。

验收人为执行器，逐字段读取来源；没有冒充用户本人签收：

- CUA读取现有Seko工程DOM：GMLM 3 Flash、5完成/1待检查、新版本提示；保留旧页面未刷新。这是当前显示，不升级为当前生成成功。没有Skill.use/生成/上传/时间线写入。
- 读取`ev-model-flow-catalog`原始保存样本：NANO_BANANA_2_1映射BELUGA，Omni frame_to_video 8映射abra_i2v_8s；配置不是真实请求。官方14原归档preferModel=gmlm-3-flash，不能移植为29实际模型或媒体模型。
- 历史TTS输入toneId42/30、speedRatio1；SekoTalk服务选择sensetime，首帧重新生成不保留Flow动作。精确模型未暴露，当前候选执行仍unknown。
- 读取agent/providers.json：video_review配置claude、model=null/effort=null；仅目录事实，没有执行外部cross-AI。开发代理继承会话，resolver未返回具体型号，不猜测。
- 复核本地桥只转交画布首帧路径，编辑器shots生成与Agent drama-script入口独立；全局fetch保护正则不等于实际误伤证据，保留服务当前影响unknown。

## Decisions / Deviations

1. 按计划明确允许的selection=blocked分支交付9个required=false调查记录；不推导厂商九步顺序，不用空集合把报告标完整。
2. 用户模型路由补充要求增加model_routes，关联step与来源；review能力实际存在所以纳入，未扩张生产实现。
3. 为防止“只填少数已知步骤就认证完整”，final需要当前执行来源的workflow_coverage绑定候选及全部step_ids；这是防止虚假完整的必要校验。真实证据没有该证明，所以保持unassessed。
4. 用户优先规定RED不提交；无需重问已确认偏好。沿用授权main、配置允许默认分支提交；根目录/分支每次提交前检查，无worktree、无推送。

实现期一次测试fixture纠正：充分技术blocked报告必须scope_decision=requires_decision，原fixture写pending_evidence，被检查正确拒绝；修正fixture后62项通过。没有生产代码改动或新增依赖。

## Deferred Evidence / Next Readiness

BASE-02：官方14和创作者29同稿实际输出、人工次数、完整步骤及前置控制未观察。BASE-04：责任清单已保存，但真实可行性未评定，完整边界报告验收未通过。当前旧资源404与新标签桥失败由01-02证实，只能证明局部当前失配，不证明整个Seko技术不可能。

下一项需要执行层能在厂家派发前挂起并注入/恢复外部结果的真实协议或已有任务踪迹，然后才能安全比较两候选。当前不触发盲目付费生成；生产桥修复、质量调度/恢复、声音验收与整集分别属于后续阶段。Phase2自动推进明确禁止；不把缺证据变成产品范围选择。

## Known Stubs / Threat Review

没有代码stub、跳过单测或未运行自动verify。unknown/null为计划要求的真实未观测事实，不是伪造占位实现。实际候选执行/控制验收未满足，已在VALIDATION保留pending；四条假设与descriptor-less禁止项未自动销项。工具仅离线读取证据，无新增网络端点/鉴权/外部写入；私有归档仍留本机，未提交第三方完整源码、凭据或签名媒体URL。

## Self-Check: PASSED

五个交付文件及SUMMARY存在；51a3622、cc60a64、9414da6均为HEAD祖先；任务提交无删除。真实final与全部指定自动检查已通过；父代理config/执行说明及extension.crx/extension.pem未纳入任务提交。
