# Phase 1: 成熟工作流与接管边界 - Context

**Gathered:** 2026-10-14
**Status:** Ready for planning

<domain>
## Phase Boundary

按 ROADMAP.md 的 BASE-01～BASE-04，确认 Seko 候选成熟工作流的真实调用链、生成前接管边界、当前版本状态和可执行接入清单；比较官方与玩家 Skill 后选择合适的首条流程。保留三家实测矩阵，明确已验证、仅发现、未实现和受阻项。

本阶段不能以单个按钮接通代替整条 Skill 已接管，也不能用静态接口名称代替运行证据。图片/视频适配、Skill 串联、常驻恢复、对白和整集交付仍由后续阶段实现。本次完成的是需求讨论，尚未执行 Phase 1 方案。
</domain>

<decisions>
## Implementation Decisions

### 使用入口与替换边界
- **D-01:** 首版直接使用厂家现成界面和 Skill。以 Seko 为当前主线；统一工作台后续再考虑。
- **D-02:** 首版只替换图片、视频生成，调用用户自己的 Flow，并将真实素材及所需状态自动回填。
- **D-03:** 编剧、拆镜、配音、口型、剪辑暂时继续用厂家能力。它们是明确选择的服务分工；图片/视频失败后不得改回厂家生成。
- **D-04:** 禁止兜底：不静默改提供方或模型、不伪造完成、不以旧素材替代真实新生成。无法接管的步骤必须带证据明确报告。

### 选择成熟 Skill
- **D-05:** 同时比较官方和玩家的成熟短剧 Skill，再选择最合适的一条；不预先只选官方或只选玩家。
- **D-06:** 首要筛选标准是整条流程完整、剧本到成片衔接顺畅、人工操作少。创作质量与可控性仍需检查，但不是用户选择的首要排序项。
- **D-07:** 暂不限定画风，先验证流程完整、Flow 接入与自动出片。不能因测试稿风格把产品限制为某类动漫。
- **D-08:** 用户目前没有剧本，也不确定剧本输入格式。不要假设用户会提供完整台词或分镜；输入格式保持开放。

### 质量处理与后续阶段约束
- **D-09:** Flow 返回成功但画面明显不合格时，自动检查并使用同一模型最多重做 2 次；仍不合格就暂停该任务并说明原因。这里是首次生成之外最多两次质量重做，不是无限循环；不构成对未知提交结果的重发授权。
- **D-10:** 暂停失败镜头及依赖它的步骤，其他独立镜头继续；全部镜头合格后才能出最终成片。不得跳过失败镜头、拼入不合格素材或将缺失片段标为完成。
- **D-11:** D-09、D-10 是后续生成与持久调度阶段必须继承的约束，不把这些实现提前塞入 Phase 1。

### 讨论与执行方式
- **D-12:** 每次一道可点击选项题，持续澄清；用户无法选择时接受自由描述，不强迫用户代答实现细节。优先使用当前会话可用的异步选择工具，不退回正文列表要求用户手输编号。
- **D-13:** 用户已确认本阶段没有补充，要求整理成第一阶段需求说明。
- **D-14:** 继续遵循方案 → 拆解任务 → 任务卡 → 执行 → 测试 → 验收 → 提交；不新增安装。阶段讨论后按已确认方式自主推进，但本次仅结束 discuss-phase，不声称已产出或执行 PLAN。

### the agent's Discretion
- 不存在用户明确授予“任意代选产品偏好”的决定。
- 助手此前提出由自己准备统一短文戏测试稿，用于同一输入比较，沿用用户早先要求的同剧本对比方法。此为测试安排，不是用户确定的生产输入格式或画风。
- 技术分析、证据采样、REA 有限范围追踪、源码定位由研究/规划负责；不得要求用户选择底层实现方案。
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 目标、范围与已有实测
- `.planning/PROJECT.md` — 核心目标、禁止兜底、不新增安装和工作流程。
- `.planning/REQUIREMENTS.md` — BASE-01～BASE-04 及后续需求，包含本次确认的服务边界与质量规则。
- `.planning/ROADMAP.md` — 六阶段边界和依赖；本次没有扩展 Phase 1。
- `docs/THREE-PLATFORM-LIVE-RESULTS.md` — 三家共同素材实测；历史常驻描述不能替代后续证据。
- `docs/REA-INVESTIGATION.md` — REA 方法、有限覆盖与静态证据边界。
- `docs/SEKO-PERSISTENT-DIALOGUE-TASKS.md` — 后续常驻/对白实验；不是全部需求验收通过。
- `docs/SEKO-PROMPT-AB-TASKS.md` — 提示词实物对照；没有证明稳定质量提升。

### 代码地图与最新证据
- `.planning/codebase/STACK.md` — 现有工具，不新增安装。
- `.planning/codebase/ARCHITECTURE.md` — 当前桥的真实链路。
- `.planning/codebase/INTEGRATIONS.md` — 独立入口与平台限制。
- `.planning/codebase/CONCERNS.md` — 构建模块 404、服务端生成边界、引用与质量问题。
- `output/seko-interface-audit-20261014/sources.json` — 本机七模块来源与哈希；不随 Git 分发。
- `output/seko-interface-audit-20261014/rea-analysis.json` — 本机 REA 部分图；不是完整站点恢复。若文件不在当前环境，明确记录证据缺失。

没有新增外部规格文档；上述引用和本次决定共同限定研究/规划。
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `extension/seko_page.js`、`extension/seko_content.js`、`extension/seko_background.js`：既有页面接管、扩展桥和回填。
- `agent/api/seko.py`：显式映射、持久作业、摘要去重与状态迁移。
- `scripts/seko_flow_job.py`：生成提交、结果收集与媒体核验。
- `agent/services/prompt_adaptation.py`：受限静音首帧规则及提供方请求审计；不是通用 Skill 转换器。
- `scripts/seko_native_backfill.js`、`scripts/seko_dialogue_pipeline.js`：已有回填与对白编排实验。

### Established Patterns
- UUID 和显式引用映射；保存输入、任务、媒体来源及状态证据。
- 未知写入结果先检查，不重复发起付费任务。
- 静态解析、模拟测试、真实生成、成片质量分别验收。

### Integration Points
- 当前桥只接管指定画布首帧视频路由；图片、编辑器与 Agent/Skill 不能算作已覆盖。
- Agent 事件流可能来自服务端执行，须证明真正控制点是否位于厂家生成之前。
- 模块构建哈希过期时不能依赖旧页面缓存，必须核查当前版本。
- Skill 详情已发现元数据，不等于获得执行源码。比较官方与玩家流程时必须核对真实可用项。
</code_context>

<specifics>
## Specific Ideas

用户原话核心：直接用厂家现成的界面和 Skill，把生成接口换成我们的 Flow，素材自动回填，后面再考虑统一工作台。

阶段长期背景：横屏、文戏、每集 3–5 分钟、固定角色音色、精确台词、正面说话镜头对口型。后四项不代表 Phase 1 当场完成，也不要求首版把厂家配音/口型服务替换掉。
</specifics>

<deferred>
## Deferred Ideas

- 统一工作台：当前首版不做。
- 剧本输入格式/生产画风：尚未限定，后续结合实际工作流再细化。
- 同模型质量重做：进入 Phase 2 图片/视频处理。
- 局部暂停、依赖阻断、独立任务继续及最终成片合格门槛：进入 Phase 3/4，并由 Phase 6 整体验收。
- 固定音色、对白和口型：Phase 5 验收，首版保留厂家能力。
</deferred>

---
*Phase: 01-workflow-boundaries*
*Context gathered: 2026-10-14*


## 2026-10-15 本地编排范围修订

D-15：用户确认 A，本地编排与执行，复用可取得的 Seko 界面和 Skill，以同一本地任务继续为第一卡验收。这替代 D-01 的云端编排限制；D-03 的厂家非图视频服务暂保留为待核实依赖。用户选择先检查现有文字模型接口再给可点击选项。

修订依据：[01-LOCAL-REVISION.md](01-LOCAL-REVISION.md)。


### D-16 文字路由已选

用户明确选择 GPT-6.1-Sol；本地文字编排固定 Codex CLI / gpt-6.1-sol，失败暂停。计划路由见 01-LOCAL-ROUTES.json；执行器尚未接通。Skill 新核实边界见 01-LOCAL-REVISION.md。第一卡未验收，0/7，无提交。
