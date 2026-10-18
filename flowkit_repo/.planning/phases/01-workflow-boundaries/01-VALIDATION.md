---
phase: "01"
slug: "workflow-boundaries"
status: validated
validation_result: partial
phase_goal_status: pending-evidence
nyquist_compliant: false
wave_0_complete: true
created: "2026-10-15"
---

# Phase 1 — 验证策略

本文件记录2026-10-15实际执行。七张调查卡按计划顺序完成允许的有据事实/阻断交付，自动检查通过；完整候选步骤与前置控制证据不足，Phase1验收仍pending。执行器来源阅读不是用户本人验收。

## Test Infrastructure

- 已有 Python unittest、Node 内置 test；不新增安装。
- Quick: `python3 -m unittest tests.test_seko_probe tests.test_seko_flow_job tests.test_platform_probe -v`
- Scoped full: Quick 后执行 `node --test tests/test_seko_generation_hook.cjs tests/test_seko_resident_page.cjs tests/test_seko_native_backfill.cjs`。
- 研究阶段实际通过 33 项 Python + 16 项 Node 检查；只验证离线审计和模拟逻辑，不证明当前站点或 Skill 接管。
- 全仓测试未运行；当前 python3 无 pytest/fastapi。

## Sampling Rate

每张任务卡运行相关自动检查并核对真实证据；每个计划完成跑 scoped full 和新证据检查；阶段验收核对 BASE-01～04 后提交。目标本地反馈不超过60秒；线上观察独立记录时长。

## Per-Task Verification Map

新验收器已由01-01-01创建并顺序扩展至final。所有命令cwd为仓库根，每条下列自动命令退出0；完整输出与RED记录保存在忽略的本机output/workflow-boundaries-01-01、01-02、01-03目录，来源与提交详见各SUMMARY。

| 任务 ID | 需求 | 自动检查（test_type） | 真实/人工验收 | 状态 |
|---|---|---|---|---|
| 01-01-01 | BASE-01 | 18 unittest；tracer，退出0 | ev-seko-stale-shot真实旧引用反例阅读 | 调查passed；574f589 |
| 01-01-02 | BASE-01 | 52 scoped Python；matrix，退出0 | 三家九入口、15来源哈希/范围复核 | 调查passed；13ca819 |
| 01-02-01 | BASE-03 | 34 unittest；build，退出0 | 当次3旧模块404、新标签桥失败，10模块记录 | 调查passed；dbe5b93 |
| 01-02-02 | BASE-02 | 42 unittest；candidates，退出0 | 14/29来源/同稿元数据；实际输出/人工null | 调查blocked记录通过；选择pending；7872e80 |
| 01-03-01 | BASE-02 | 48 unittest；steps，退出0 | 9独立事实、模型来源逐字段复核，无伪造选中序列 | 调查记录passed；步骤验收pending；51a3622 |
| 01-03-02 | BASE-02/04 | 54 unittest；controls，退出0 | 原站UI/本地桥/历史对白；当前控制与误伤unknown | 调查记录passed；前置控制pending；cc60a64 |
| 01-03-03 | BASE-04 | 62 unittest；final；95 scoped Python+16 Node，退出0 | 19接入项、九类路由、D-09/10交接与四指标复核 | 调查交接passed；完整报告pending；SHA见01-03-SUMMARY |

probe 完整前缀为 `python3 scripts/workflow_evidence_probe.py --evidence docs/benchmarks/workflow-boundaries/evidence.json`；build 参数完整路径为 `docs/benchmarks/workflow-boundaries/current-build.json`；新单测命令为 `python3 -m unittest tests.test_workflow_evidence_probe -v`。检查器 stage 按任务顺序创建，不得提前声称可运行。

每卡 SUMMARY 必须记录：实际完整命令、开始/结束时间、退出码与命名检查、来源 ID、人工验收人/方式/结论、未决项、精确提交 SHA。测试与验收未完成不得标卡片通过；资料不足可提交明确的调查进度，但不能提交“完成”的假状态。

## Wave 0 Requirements

01-01-01 创建标准库证据合同检查器与 unittest 反例，与一条真实归档 tracer 同卡完成；无需独立基础设施计划、无需安装。每次新增语义先 RED 再 GREEN。

必测反例：缺来源/空集合、哈希不符、唯一 ID/引用断开、历史样本声称当前、200 HTML/导出缺失、后置事件冒充前置控制、只有浏览器无请求却断言服务器未建任务、缺玩家来源却选择完成、不同测试输入冒充同条件、步骤/接入项松散关联、未知却 feasible。充分真实阻断必须 contract_valid=true、feasibility=blocked、ready_for_phase2=false；缺登录/缺归档则 unassessed、report_complete=false。

## Manual-Only Verifications

| 行为 | 需求 | 证据要求 |
|---|---|---|
| 三家范围 | BASE-01 | 每格声明可追溯到对应平台、入口、时间和实际观察 |
| 官方/玩家 Skill 及控制点 | BASE-02 | 真实来源、输入输出、实际执行方、生成前控制证明；后置事件不算控制 |
| 当前版本 | BASE-03 | 当次页面资源和模块契约；旧缓存不算当前兼容 |
| 接入可行性 | BASE-04 | 每必需步骤有接入项或具体阻断，未知不得标可行 |

## Acceptance and Commit Gates

| 层级 | 通过条件 | 未达到时 |
|---|---|---|
| 任务卡 | 自动检查、对应真实来源复核、脱敏、高风险威胁缓解；按精确文件提交 | pending/blocked 与证据保留，禁止虚报 |
| Phase 1 | BASE-01～04 资料完整；可行性成立或有充分协议/运行证据的技术阻断；禁止项与假设显式复核 | 缺官方/玩家比较、当前观察、真实控制证据保持未完成 |
| Phase 2 推进 | report_complete=true、feasibility=feasible、ready_for_phase2=true，范围仍符合 D-02/D-03 | 技术阻断进入范围决定；访问/证据不足继续取证 |
| M1 / 整体 | Phase 1 只交接，不在此宣布后续阶段或整集通过 | 后续按 ROADMAP 分别测试、验收、提交 |

每计划末运行已有 Python quick 与 Node scoped suite；历史 33 Python + 16 Node 只为研究记录。当前解释器缺 pytest/fastapi，不安装，不标全仓测试通过。

## Flagged Assumptions — Spec-less Gate

输入为四条 unclassified/unresolved，保持 4 条且不自动销项；SPEC 两节缺失由上游 helper 确认。

| requirement_id | category | status | verification | 明确待核对 |
|---|---|---|---|---|
| BASE-01 | unclassified | unresolved | null | 三家范围是否遗漏入口/反例，人工逐格核对 |
| BASE-02 | unclassified | unresolved | null | 真实候选、实际人工操作和步骤控制未知 |
| BASE-03 | unclassified | unresolved | null | 当次构建/桥状态与旧缓存差异 |
| BASE-04 | unclassified | unresolved | null | 未观察的技术阻断形态与清单闭合 |

所有 PLAN 的 must_haves.prohibitions 保持 descriptor-less flagged-unverified，不添加虚构 check_*。单测通过不自动消除这些标记；执行验收需明确记录判断与证据。OWASP 通用凭据/注入约束归 threat_model，ASVS level 1、block_on=high。

## Validation Sign-Off

- [x] 逐卡自动验证或明确的 Wave 0 依赖齐备（仅规划结构）
- [x] 每三个连续任务至少一项自动检查（每卡都有）
- [x] 所有新增检查入口均有创建任务（现已创建并执行）
- [ ] 真实证据复核通过，不以模拟测试替代
- [ ] 执行验收完成后再更新验证状态

**Approval:** 自动覆盖审计完成；真实工作流验收仍 pending，独立阶段验收另见 VERIFICATION。

## 实际需求验收与未决项

| 需求 | 状态 | 证据与判断 |
| --- | --- | --- |
| BASE-01 | passed（待阶段独立复核） | 三家九入口有来源/时间/限制；历史反例保留，01-01-SUMMARY |
| BASE-02 | pending | 未选定候选；当前实际步骤/执行层/前置控制缺证据；不能以九类调查清单代替流程 |
| BASE-03 | passed（已证当前不兼容） | 当前旧依赖全部404与新标签桥失败；新资源符号不是语义等价证明 |
| BASE-04 | pending | 清单与后续规则已交接，report_complete=false、feasibility=unassessed、ready_for_phase2=false |

01-03三卡均实际运行RED目标断言并通过`gsd-tools check tdd-red-evidence`，再GREEN、来源验收、原子提交；用户要求不提交RED。本轮无新增安装、厂家生成/Skill.use、上传/时间线写入或生产桥修复。

来源复核人：执行器。核对官方14历史preferModel=gmlm-3-flash、现有工程UI GMLM 3 Flash、本机目录NANO_BANANA_2_1→BELUGA及abra_i2v_8s、历史音色42/30不是型号、SekoTalk/sensetime为服务、review配置claude/model=null未运行。保留服务当前误伤仍unknown，不以静态正则下运行结论。

四条flagged assumptions仍unclassified/unresolved/verification=null。所有计划descriptor-less prohibitions仍flagged-unverified：执行器阅读本次差异未见盲跑、旧素材冒充、静默替换或生产功能扩张；没有把该阅读写成自动描述符通过。当前阶段报告证据不足，独立阶段验收由父流程继续。

## 执行后覆盖审计（2026-10-15）

审计本轮7卡的测试映射、62项原始检查及代码审查新增12项反例。四处自动检查缺口CR-01～04已修复，各项实际RED/GREEN与提交见01-REVIEW-FIX.md；最新范围回归为74项证据检查+33项既有Python=107项，Node16项。未运行全仓测试。

| 需求 | 自动覆盖 | 真实验收 | 结论 |
|---|---|---|---|
| BASE-01 | 哈希、入口范围、引用闭合、旧素材反例 | 三家九入口来源已复核 | COVERED，等待独立验收复核 |
| BASE-02 | 候选身份/同稿/运行时间；步骤/控制/触发证据；模型精确匹配 | 同稿真实运行、实际步骤及前置控制仍缺 | PARTIAL，必须运行取证 |
| BASE-03 | 状态/URL/MIME/导出/哈希绑定、404反例 | 当前旧模块404及桥失败已采样 | COVERED，明确不兼容 |
| BASE-04 | 完整度、阻断与未知区分、禁止空集合或未知触发解锁 | 必需工作流尚未选定和闭合 | PARTIAL，必须补证据 |

没有用合成测试填平上述两类真实验收缺口；nyquist_compliant保留false。来源复核由执行代理完成，不冒充用户验收。CR-03曾因命令门禁顺序错误提前提交，已纠正夹具、全检通过后amend；01-REVIEW-FIX如实保留过程偏差。

## Validation Audit 2026-10-15

| Metric | Count |
|---|---|
| Gaps found | 6 |
| Resolved | 4 |
| Escalated | 2 |
