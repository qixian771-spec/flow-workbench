# Roadmap: 成熟漫剧工具接入自有 Flow

## Overview

基于现有工程和实测逐步完成 Seko 主线，复用成熟创作工作流。先明确接管可行性，再交付真实生成、工作流串联、持久运行、对白和整集。旧实验不计入新阶段完成。阶段讨论后再生成方案与任务卡，不在初始化期间执行产品改动。

## Phases

- [ ] **Phase 1: 成熟工作流与接管边界** - 确定选中成熟工作流的真实调用链、接管边界、版本状态和可执行接入清单。
- [ ] **Phase 2: Flow 图视频与模型适配** - 目标图/视频任务经模型适配后由自有 Flow 真实生成，保留完整对照证据。
- [ ] **Phase 3: Skill 串联与原站自动出片** - 从选定成熟 Skill/工具触发目标生成，经 Flow 回填，继续原站工作流并导出多镜短片。
- [ ] **Phase 4: 常驻运行与中断恢复** - 上述闭环刷新与服务重启后仍可接续，未知写入和版本失配显式处理。
- [ ] **Phase 5: 对白、固定音色与口型** - 对白短片同时满足固定角色音色、精确台词与正面镜头对口型。
- [ ] **Phase 6: 整集自动化与整体验收** - 从完整剧本自动完成一集横屏 3–5 分钟文戏，并完成任务、里程碑、整体三级验收。

## Phase Details

### Phase 1: 成熟工作流与接管边界

**Goal**: 确定选中成熟工作流的真实调用链、接管边界、版本状态和可执行接入清单。
**Depends on**: Nothing (first phase)
**Requirements**: BASE-01, BASE-02, BASE-03, BASE-04
**Success Criteria**:
1. 三家矩阵每项标明实测/仅发现/未实现/受阻，并链接证据。
2. 选定工作流逐步骤记录实际执行方、请求与状态契约；Agent/Skill 服务端生成是否可控必须有证据。
3. 当前版本与旧常驻方案差异可复现；明确过期模块的影响。
4. 形成后续接入清单；若关键步骤无法接管，记录阻断原因并进入明确的范围决策，不伪装可行。

**Canonical refs**: `docs/REA-INVESTIGATION.md`, `docs/THREE-PLATFORM-LIVE-RESULTS.md`, `.planning/codebase/INTEGRATIONS.md`, `.planning/codebase/CONCERNS.md`
**Plans**: 共6份计划。01-01～03的7张调查卡已交付；独立阶段验收gaps_found。新增01-04～06共7张缺口卡已通过计划检查、待执行；Phase2禁止自动推进。
**Wave 1**
- [x] 01-01-PLAN.md — 真实证据 tracer、证据检查与三家能力矩阵（2 卡）

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 01-02-PLAN.md — 当前构建核查、同输入官方/玩家 Skill 比较（2 卡）

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 01-03-PLAN.md — 逐步骤调查、控制门槛、接入清单（3卡调查交付；阶段验收pending）

**Wave 4** *(blocked on Wave 3 completion)*
- [ ] 01-04-PLAN.md — 当前执行层生成前控制、外部结果恢复与双候选共同输入（2卡）

**Wave 5** *(blocked on Wave 4 real evidence acceptance)*
- [ ] 01-05-PLAN.md — 官方/署名创作者同稿同参考真实运行、比较和选择（3卡）

**Wave 6** *(blocked on Wave 5 real run acceptance)*
- [ ] 01-06-PLAN.md — 选定调用链、九类模型路由、接入清单与四指标验收（2卡）

**Cross-cutting constraints:** 顺序执行；零安装；不兜底、不自动切换模型/提供方；真实运行不得被静态资料、模拟、旧素材替代；未知仍为缺口。每卡测试及真实验收后提交，Phase1另行独立验收。新增计划不代表缺口关闭。

**Gap plan index:** `.planning/phases/01-workflow-boundaries/01-GAP-PLAN-INDEX.md`；**validation:** `01-GAP-VALIDATION.md`；**plan check:** `01-GAP-PLAN-CHECK.md`。

### Phase 2: Flow 图视频与模型适配

**Goal**: 目标图/视频任务经模型适配后由自有 Flow 真实生成，保留完整对照证据。
**Depends on**: Phase 1
**Requirements**: FLOW-01, FLOW-02, ADAPT-01, ADAPT-02
**Success Criteria**:
1. 图片和视频各有真实 Flow 新生成结果与提供方任务记录。
2. 源意图、参考图、实际模型与转换版本对应可查，不支持项停止。
3. 同镜头同参考完成原/转换提示词实物对照，不预设转换必然更优。

**Canonical refs**: `docs/MODEL-PROMPT-ADAPTATION.md`, `docs/SEKO-PROMPT-AB-TASKS.md`
**Plans**: TBD — discuss-phase 后由 plan-phase 拆解任务卡。

### Phase 3: Skill 串联与原站自动出片

**Goal**: 从选定成熟 Skill/工具触发目标生成，经 Flow 回填，继续原站工作流并导出多镜短片。
**Depends on**: Phase 2
**Requirements**: SKILL-01, RETURN-01, RETURN-02
**Success Criteria**:
1. 从选定成熟入口发起，目标图视频任务在厂家执行前被正确接管。
2. 真实素材和状态回填后镜头/时间线引用正确，原工作流继续。
3. 导出含多个不同新镜头的短片，通过媒体来源和完整解码检查。

**Canonical refs**: `docs/SEKO-NATIVE-FLOW-TASKS.md`
**Plans**: TBD — discuss-phase 后由 plan-phase 拆解任务卡。

### Phase 4: 常驻运行与中断恢复

**Goal**: 上述闭环刷新与服务重启后仍可接续，未知写入和版本失配显式处理。
**Depends on**: Phase 3
**Requirements**: OPS-01, OPS-02, OPS-03
**Success Criteria**:
1. 刷新与服务重启后任务可接续，已知任务不重复付费生成。
2. 提交、上传、回填等中断点能区分已完成、失败、结果未知。
3. 网站模块变化可检测并明确停止，不自动换接口或模型。

**Canonical refs**: `docs/SEKO-PERSISTENT-DIALOGUE-TASKS.md`
**Plans**: TBD — discuss-phase 后由 plan-phase 拆解任务卡。

### Phase 5: 对白、固定音色与口型

**Goal**: 对白短片同时满足固定角色音色、精确台词与正面镜头对口型。
**Depends on**: Phase 4
**Requirements**: VOICE-01, VOICE-02, VOICE-03
**Success Criteria**:
1. 同一角色跨镜头使用固定音色，并有听审记录。
2. 逐句对白与剧本、字幕相符，无漏说或擅自增补。
3. 正面说话镜头有独立口型检查，失败镜头不能混入已通过集合。

**Canonical refs**: `docs/SEKO-PERSISTENT-DIALOGUE-TASKS.md`
**Plans**: TBD — discuss-phase 后由 plan-phase 拆解任务卡。

### Phase 6: 整集自动化与整体验收

**Goal**: 从完整剧本自动完成一集横屏 3–5 分钟文戏，并完成任务、里程碑、整体三级验收。
**Depends on**: Phase 5
**Requirements**: FILM-01, FILM-02, FILM-03
**Success Criteria**:
1. 完整剧本自动产出横屏 3–5 分钟成片，非重复片段或仅拼接演示。
2. 镜头来源、人物场景和声音连续性有可核查记录。
3. 任务、阶段里程碑和整体均完成测试、验收及提交；剩余问题明确列出。

**Canonical refs**: `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`
**Plans**: TBD — discuss-phase 后由 plan-phase 拆解任务卡。

## Milestone Acceptance

- M1（Phase 1–3）：选定成熟工作流经 Flow 完成图视频、回填与多镜短片导出。
- M2（Phase 4–5）：常驻可恢复并完成对白质量验收。
- v1（Phase 6）：整集自动化；重新执行整体测试、验收、提交。
- 每张任务卡须有输入、依赖、改动范围、验证步骤、验收标准、证据和提交。
- 第一阶段若关键接管不可行，停止进入依赖它的阶段，带证据讨论范围调整；禁止自动替代。

## Progress

| Phase | Plans Complete | Status | Completed |
| --- | --- | --- | --- |
| 1. 成熟工作流与接管边界 | 3/3 | In Progress | - |
| 2. Flow 图视频与模型适配 | 0/TBD | Not started | - |
| 3. Skill 串联与原站自动出片 | 0/TBD | Not started | - |
| 4. 常驻运行与中断恢复 | 0/TBD | Not started | - |
| 5. 对白、固定音色与口型 | 0/TBD | Not started | - |
| 6. 整集自动化与整体验收 | 0/TBD | Not started | - |


## 2026-10-15 本地编排范围修订

D-15 生效：第一张缺口卡改为本地执行 tracer。旧服务器恢复证据保留未通过；现为范围修订／前置核实，0/7。后六卡在依赖通过并按本地归属修订前不执行。

修订依据：[01-LOCAL-REVISION.md](phases/01-workflow-boundaries/01-LOCAL-REVISION.md)。


### 2026-10-15 本地执行更新

01-04-01 本地单镜闭环已真实验收，缺口卡 1/7。01-04 整份计划仍未完成；后六卡先按 D-15/D-16 修订。旧云端恢复未验收，Phase 2 不自动推进。

### 2026-10-15 本地视频更新

修订后的 01-04-02 已完成 Omni 新视频、Seko 回填及同一本地任务续行，缺口卡 2/7。其余五卡和官方／玩家实测比较仍待修订执行。静音、常驻注入、整片导出未通过；Phase 1 与里程碑保持进行中。

### 2026-10-15 本地原生剪辑导出更新

01-05-01 修订后真实完成单镜裁剪和 Seko 原生自动导出，缺口卡 3/7。四张剩余卡、成熟 Skill 比较、多镜整集、对白音色与口型、常驻注入继续未完成。阶段和里程碑不自动关闭。

### 2026-10-15 本地双镜更新

01-05-02 按本地方案完成两个不同 Omni 视频的自动回填、顺序裁剪、硬切衔接和 Seko 原生导出。缺口卡 4/7，剩余三卡待修订执行。已验证8秒双镜接口链路，未验证整集、固定音色、口型或页面常驻。成熟 Skill 同稿比较继续未完成，Phase 1 与里程碑不关闭。
