# Phase 1 缺口计划索引

本轮只规划，未执行任务、未安装、未生成；计划经独立审查后由父流程提交。旧3份计划/7卡不改。新增3份计划/7卡，顺序Wave4→5→6，当前main，parallelization=false。所有新计划gap_closure=true。

| 计划 | 卡片 | 依赖 | 实际结果门 |
|---|---|---|---|
| 01-04 | 01真实控制tracer；02双候选门与输入 | 已执行01-03 | 前置未派发＋外部接受/恢复证明，才允许候选启动 |
| 01-05 | 01官方run；02创作者run；03比较选择 | 01-04 | 两个同稿同参考run，完整流程/人工次数真实可核对 |
| 01-06 | 01实际步骤/九类路由；02清单/四指标 | 01-05 | selected run→required steps→接入项→真实可行性 |

各task≤5修改文件。共享证据/检查器依赖强制顺序，无同wave文件冲突。第一卡是type=tracer，直接追真实协议到可运行验收，后续扩展候选与覆盖。无独立基础设施大层。

## 缺口映射

| 01-VERIFICATION缺口 | 覆盖卡 |
|---|---|
| 先取得生成前挂起/恢复协议或当次已有踪迹 | 01-04-01/02 |
| 同稿官方/创作者实际输出、人工动作，选择真实候选 | 01-05-01/02/03 |
| 实际逐步执行方、请求、状态与控制 | 01-06-01（01-04/05提供运行来源） |
| 接入项绑定selected required流程与充分可行性 | 01-06-02 |
| 资料不足与真实技术阻断分开，不自动进Phase2 | 全卡停止规则、01-06-02四指标 |

有界取证不保证成功：6模块/2跳/一次定向REA与一次窗口补采是单次调查边界；边界耗尽仍缺证据就保留gap，不能将“查完”签成完成。确有技术阻断直接带证据上报上游；不执行依赖它的候选，不要求用户代选技术实现。当前生产桥不修；已有协议通道须完整实际证明才可作为后续实现依据。

## 多来源覆盖审计

COVERED仅表示计划有明确任务，不表示已实现或已验收。

| SOURCE | ID/内容 | Plan/card | Status |
|---|---|---|---|
| GOAL | 选中成熟流程真实链、边界、版本、可执行清单 | 04～06全部 | COVERED |
| REQ | BASE-01三家入口矩阵及历史反例 | 旧01-01已交付，06-02复核保留 | COVERED |
| REQ | BASE-02真实选中流程/执行方/控制 | 04-01～06-01 | COVERED |
| REQ | BASE-03当前构建与失配 | 04-01/02，06-02 | COVERED |
| REQ | BASE-04真实可行性/阻断/清单 | 04-01，06-02 | COVERED |
| RESEARCH | 分层证据、hash、时间、当前/缓存/归档 | 04-01，06-01/02 | COVERED |
| RESEARCH | 原桥范围、全局保护与保留服务影响 | 04-01/02，06-01 | COVERED |
| RESEARCH | 官方/创作者来源、同输入、完整度/人工成本 | 04-02，05全部 | COVERED |
| RESEARCH | 逐步合同、真正执行层前置控制/恢复 | 04全部，05运行，06-01 | COVERED |
| RESEARCH | 来源只读、现有REA有界追踪、零安装 | 04-01/02及各卡 | COVERED |
| RESEARCH | 接入责任分层、后续阶段归属 | 06-02 | COVERED |
| RESEARCH | 标准库反例/真实证据双验收、ASVS1 | 全部verify及threat_model | COVERED |
| CONTEXT | D-01原站Skill/Seko主线 | 04-01，05-01，06-01 | COVERED |
| CONTEXT | D-02图/视频Flow与真实回填 | 04-01，05-01/02单次取证，06-02后续责任 | COVERED |
| CONTEXT | D-03保留厂家编剧/拆镜/声音/剪辑 | 05-02，06-01/02 | COVERED |
| CONTEXT | D-04禁止兜底及真实边界 | 全部 | COVERED |
| CONTEXT | D-05官方与玩家比较 | 04-02，05全部 | COVERED |
| CONTEXT | D-06先完整流程再人工少 | 05-02/03 | COVERED |
| CONTEXT | D-07画风开放 | 04-02，05-01/03 | COVERED |
| CONTEXT | D-08不假设用户剧本格式 | 04-02，05-01/03 | COVERED |
| CONTEXT | D-09同模型最多2次质量重做 | 06-02只交接，执行归后续 | COVERED |
| CONTEXT | D-10失败依赖暂停/独立继续/全合格出片 | 06-02只交接 | COVERED |
| CONTEXT | D-11不提前实现质量调度 | 06-02 | COVERED |
| CONTEXT | D-12范围决定一道可点击题/自由说明 | 06-02；仅真实产品未决，已有授权不重问 | COVERED |
| CONTEXT | D-13沿用收口需求 | 04-01，06-02 | COVERED |
| CONTEXT | D-14方案→卡→测试验收提交/零安装 | 全部卡 | COVERED |

排除项：统一工作台、生产替换/持久恢复/质量调度、声音口型与整集验收属于明确后续阶段；没有移除任何Phase1证据目标。PROJECT记录的历史付费生成授权沿用于未来执行，无需重复索取已有授权；本轮最新请求仅授权规划与计划审查，不执行取证。未来执行仍受01-04前置证明和单次预算约束：先证明厂家未派发及外部恢复能力，不能变成盲跑或生产实现。

## 来源与新增符号

现有已跟踪：scripts/workflow_evidence_probe.py、tests/test_workflow_evidence_probe.py、agent/models.json、agent/providers.json、agent/services/flow_batch.py、agent/api/requests.py、agent/api/seko.py、scripts/seko_flow_job.py、extension/seko_page.js、原两JSON及两报告。output目录只读引用，不是修改目标。项目无.codex/skills/.agents/skills目录；采用现有skills中对应操作说明，无新包。graphify禁用，不启用。发现级别0：复用现有研究/CLI/代码模式，没有新增外部依赖、Web研究或新服务。

| creates任务 | 新文件或符号 |
|---|---|
| 01-04-01 | gap-evidence.json、gap-current-build.json、docs/SEKO-GAP-CONTROL-PROOF.md |
| 01-04-01 | CLI --require-gap-closure；stage gate；validate_evidence的可选require_gap_closure参数；validate_gap_gate |
| 01-04-01 | gap_profile/schema_version/source_audit_id/purpose/test_input_sha256/reference_set/expected_candidate_ids/protocol_trials/execution_channel/candidate_runs；输出gap.tracer_complete/control_gate_complete |
| 01-05-01 | docs/SEKO-SAME-INPUT-COMPARISON.md；stage comparison；validate_gap_comparison；gap.completed_candidate_ids |
| 01-06-01/02 | 强化现有control/coverage/retained_media/model运行绑定；现有validate_final增加已证协议通道分支（原完整性门全部保留） |

本轮规划已新建01-04/05/06-PLAN、01-GAP-VALIDATION、此索引；执行时每计划创建对应SUMMARY。没有计划新的生产端点、模型或自动化调度符号。新命令必须由creates卡先实现；可执行既有基线和后续精确命令见GAP-VALIDATION与每卡verify。

estimate-calibration实际结果：factor=1、sample_count=0、confidence=low。三计划raw/calibrated分别30000/34000/28000，2/3/2卡；未自评置信度。新威胁T-01-12～20唯一连续，SC保留。七旧禁止项descriptor-less与四条unclassified/unresolved/verification:null假设不自动销项。

plan-pre贡献：复用已完成研究/PATTERNS；本阶段无新UI、AI生产系统或ORM，不生成UI/AI-SPEC/迁移任务；assumption-delta detected=false。外部能力取证范围已写当前能力/调用点与停止条件，无新生产API集成；已有COVERAGE由父流程维护，本计划不擅改。旧审计和验证文件不改，新增计划后独立重验必需。


## 规划检查记录

- 独立检查：两处WARNING已修订并复查通过；原始发现与闭环保留在01-GAP-PLAN-CHECK.md。规划通过不等于运行验收。
- 决策覆盖：D-01～14全部有计划引用；BASE-01～04均有旧计划/缺口卡承接。
- 开发代理路由：gsd-planner继承当前会话、effort=xhigh；gsd-plan-checker继承当前会话、effort=low；resolver未返回具体模型ID，不推测型号。产品九类路由见01-06，二者分开。
- 初始化提示静态代理配置可能需重新安装；本轮遵循用户零安装要求，没有安装或更新。实际派发采用会话继承与resolver返回的effort，无模型覆盖需求。
- 新计划和修改后的规划状态不证明旧验收缺口已闭合；执行后必须重新独立验证。


## 2026-10-15 本地编排范围修订

当前执行变更：用户已选择本地编排。01-04-01 的旧云端目标未完成并停止作为当前验收目标；新本地门尚未实现。0/7。旧七卡中的后六卡仍挂起，修订后再执行。

修订依据：[01-LOCAL-REVISION.md](01-LOCAL-REVISION.md)。


## 2026-10-15 执行更新（优先于历史未实现状态）

用户授权公开工作流本地适配后，01-04-01 按 `01-04-01-LOCAL-TASKS.md` 完成实现、测试和真实验收，详见 `01-04-01-SUMMARY.md`。当前 1/7；同 run 新生成、回填和续行已证。旧云端恢复不通过的结论保留。后六卡未启动，须先修订；Phase 1 未完成。


## 2026-10-15 用户授权第二卡修订

01-04-02 当前改为同一本地 run 的 Omni 视频生成、Seko 回填和续行，合同见 `01-04-02-LOCAL-TASKS.md`。旧双候选启动门和同稿比较仍是未满足需求，移入后续重排，不能因本地两卡成功关闭。

第二卡本地视频链已真实验收：2/7；01-04-03 至其余五卡尚未启动，先按本地执行归属修订。原双候选比较移后但未通过。完整见 01-04-02-SUMMARY.md。

## 第三卡修订与执行（当前有效）

用户要求优先本地剪辑和自动出片。原七卡第三张为 01-05-01，现按 01-05-01-LOCAL-TASKS.md 完成本地原生裁剪导出，3/7。历史“01-04-03”编号应读为第三卡 01-05-01。旧官方／创作者同稿比较仍未完成；其余四卡未启动，须先按本地方案重排。新视频原件 → 独立 Seko 时间线 → 原生裁剪 → 原生导出 → 同 run export_complete 已真实验收，不升级为多镜整集。

## 第四卡修订与执行（当前有效）

按用户要求，01-05-02 改为同一本地 run 的双镜衔接与原生自动出片，合同见 01-05-02-LOCAL-TASKS.md；现已真实通过，4/7。A 为上一张已验收 Omni 原片，B 为本卡 Sol 新策划并由 Omni 新生成、同字节回填的独立视频。双镜各取4秒，Seko 原生硬切导出8.041667秒，重开不重复写入。剩余三卡仍须按用户优先级修订；官方／创作者同稿比较依然未满足，整集、声音口型及常驻不因本卡通过而关闭。
