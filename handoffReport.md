# Toonflow / FlowKit 本地漫剧工作台交接报告

更新时间：2026-10-15。用途：供后续 AI 接手；本轮仅交接，不启动下一张开发卡。

## 1. 先读结论

已经真实打通：本机 Toonflow 输入一个新剧本 → 本地中转站 Gemini 拆镜并生成两类提示词 → Flow 新生成两张图片 → Omni 新生成两个不同视频 → Gemini 图片/抽帧审核 → 回填原生画布 → 本机 FFmpeg 自动导出 16 秒影片。全过程归属一个持久化总任务，无 Seko 运行依赖。

这只是**静音双镜头自动链路验收通过**，不是整个漫剧产品完成。跨镜头道具细节仍不一致；固定角色音色、精确台词、对口型、人物一致性和每集 3–5 分钟尚未验收。不要将“自动审核给了通过”描述成内容质量全面通过。

代码已提交：Toonflow `3b7ae8a`；任务卡与验收证据 FlowKit `feb80dc`。交接时 Toonflow 工作树干净；FlowKit 有大量早期 Seko 未提交工作，必须保留。

## 2. 用户目标与约束（优先级高于旧方案）

- 最终目标：拿到剧本后自动制作横屏剧情漫剧，偏文戏，单集 3–5 分钟；固定角色音色、精确台词、正面说话对口型。
- 最新架构：基于成熟开源 Toonflow 的**本地网页工作台**。网页访问本机地址，源码、任务、素材、成片存本机；不要求模型离线。不能退回 Seko 网页代操作作为主线。
- 文字模型必须灵活配置。用户已取消 GPT-6.1-Sol 绑定，最新指定使用**本地中转站 Gemini**。
- 生图固定 Nano Banana 2.1，视频固定 Omni。失败不能自动切换模型、供应商、协议或用旧素材/占位数据冒充真实生成。
- 不安装新东西。历史仅授权过 Toonflow 项目锁定依赖，已安装完成；不能将该例外扩展为新增软件、全局包、模型、ComfyUI 等。
- 已授权真实生成消耗。仍按任务卡顺序推进：方案 → 拆任务 → 任务卡 → 执行 → 测试 → 真实验收 → 提交。没有通过不能报完成。
- 不合格媒体可同模型最多重做 2 次；局部暂停，其他独立镜头继续；提交结果未知不能当质量失败而重发付费请求。
- 用户偏好中文、内联可视化；需要询问时用一道可点击选择题逐个问，不反复要求其重载 Chrome 或手工操作。

## 3. 本地位置、提交与服务

|用途|位置/状态|
|---|---|
|工作根目录|`/Users/niuniu/Desktop/flow cli`|
|Toonflow 源码|`/Users/niuniu/Desktop/flow cli/toonflow`|
|Toonflow 分支/提交|`local/flow-workbench` / `3b7ae8a`|
|FlowKit 源码及规划|`/Users/niuniu/Desktop/flow cli/flowkit_repo`|
|FlowKit 分支/提交|`main` / `feb80dc`|
|本地工作台|`http://127.0.0.1:3000/#/workspace`|
|FlowKit HTTP / 扩展 WS|`127.0.0.1:8100` / `127.0.0.1:9222`|
|本地文字中转|`http://127.0.0.1:18080/v1`|
|FlowKit 实际运行副本|`/Users/niuniu/Library/Application Support/FlowKit`|
|FlowKit LaunchAgent|`com.niuniu.flowkit`|
|FlowKit 日志|`/Users/niuniu/Library/Logs/FlowKit/agent.log`、`agent.error.log`|
|FlowKit plist|`/Users/niuniu/Library/LaunchAgents/com.niuniu.flowkit.plist`|
|Toonflow 配置|`toonflow/data/settings.json`，权限0600，Git忽略，含凭据|
|验收工作区|`toonflow/data/workspaces/flowAcceptance`|

交接时 3000 正在监听（PID 32961，仅作当时记录，接手需重新核对）。Toonflow 当前通过源码服务启动，不是已安装的常驻桌面应用：

```sh
cd '/Users/niuniu/Desktop/flow cli/toonflow'
NODE_ENV=production bun --no-install apps/server/src/index.ts
```

不要重复启动同端口服务。FlowKit 是既有 LaunchAgent，交接核查健康、扩展0.5.2已连接。Chrome 使用用户“用”配置，最近有效浏览器实例ID为5；实例/标签ID不是永恒值，不能沿用早期失效3/4实例结论。

已有 Bun、Node、FFmpeg 和项目依赖够本卡使用。不要执行安装命令。运行时文件不一定随源码改动自动更新；FlowKit 如需改动，须单独部署已测试的对应文件到运行副本，不能仅修改仓库后宣称运行版本已变。

## 4. 明确模型路由

|任务|路由|约束|
|---|---|---|
|读剧本、拆镜、静帧/视频提示词|Toonflow 原生自定义供应商 `localGemini`，OpenAI-compatible|接口/模型可更换；每任务固定配置快照|
|本次文字请求模型|`gemini-3.8-flash-high`|这是中转站暴露的 ID，不根据名称猜测上游版本|
|本次预期文字回执模型|`gemini-3.8-flash-n`|真实观察所得，显式配置 `responseModel`；不符就暂停|
|图片|Flow `BELUGA` / Nano Banana 2.1|16:9原生尺寸，当前适配器仅文生图，不支持图像参考输入|
|视频|Flow `abra_i2v_8s` / Omni|单图、8秒、720p、横屏、静音，首帧必须是已登记Flow图片|
|图片/视频质量审核|与总任务相同 Gemini|图片原图；视频首帧 + 1/4/7秒帧，非全帧审查|
|剪辑/导出|现有系统FFmpeg|无文字模型调用，H264，30fps，静音|

凭据不要输出、提交或写入报告。任务只记凭据指纹。原生设置中展开模型高级设置可以填写预期回执ID；为空则严格要求请求和回执ID相同。自动成片入口目前支持 OpenAI-compatible 文字协议，其他协议明确拒绝，不能宣称已经通用适配所有协议。

应用层没有自动换模型或文字重发；**既有中转站账号池的传输重试配置没有修改**。此前观察到中转配置存在重试和配额切换开关，不能声称整个上游链路绝无重试。回执模型匹配也不等于证明中转内部每次只调用一次。

## 5. 本轮核心实现位置

均在 `toonflow/`：

- `apps/server/src/utils/flow/textModel.ts`：复用原生模型配置，快照/凭据指纹、一次文字请求、精确回执、严格JSON结构。没有解析修补或默认剧本。
- `apps/server/src/utils/flow/autoTask.ts`：持久化总任务、拆镜、逐镜图片/视频/审核、最多2次质量重做、局部失败、原生画布回填、导出与恢复。
- `apps/server/src/routes/workflows/flowStart.ts`、`flowStatus.ts`、`flowResume.ts`：同源工作台与工作区路径保护。
- `apps/server/src/utils/media/generation.ts`：复用原生媒体生成和存储，加入总任务/步骤身份以及生成前持久化回调；向上返回 Flow job ID。
- `apps/server/src/utils/flow/exportFilm.ts`：扩展为总任务下不同图片根任务的多个视频；核对审核清单顺序、Flow回执、素材hash；沿用本机FFmpeg及幂等导出。
- `apps/server/src/routes/workflows/flowExport.ts`：导出接口。
- `apps/web/src/pages/workspace/components/autoFilm.vue`：原生工作台“自动成片”入口，选模型/输入剧本/进度/恢复/播放器。
- `apps/web/src/pages/workspace/components/workspaceMenu.vue`：入口挂载。
- `apps/web/src/components/settings/panels/languageModel/addCustomProviderDialog.vue`、`apps/web/src/stores/settings.ts`、`apps/server/src/utils/ai/index.ts`：预期回执模型配置。
- `packages/providers/src/media/flowKit.ts`：此前已完成的Flow图片/Omni适配器，本卡复用。Omni单图契约用 `images[0]`，不是 `firstFrame`。

FlowKit仓库已有实现：

- `agent/services/toonflow_jobs.py`：图片任务日记、稳定ID、生成前约束、下载hash验证。
- `agent/services/toonflow_video.py`：视频任务、源图字节hash、真实Omni提交回执、父任务推进。
- `agent/api/toonflow.py`：本机持久任务API。
- `agent/sdk/services/operations.py`、`flow_provider.py`：固定模型路由。
- `agent/worker/processor.py`：绑定任务失败不进入旧重试；启动时未知PROCESSING暂停核查，不重置排队。

## 6. API与恢复合同

Toonflow接口均为POST，前缀 `http://127.0.0.1:3000/api/workflows/`；本机调用需 `Origin: http://127.0.0.1:3000`、`x-toonflow-workspace: 1`、JSON Content-Type。

- `flowStart`：`directory`、`taskId`(UUID)、`script`、`providerId`、`modelId`、`shotCount`(2..8)。同ID同输入只返回已有任务；同ID不同输入409。
- `flowStatus`：`directory`、可选`taskId`。纯读取；active是当前服务进程内状态。
- `flowResume`：`directory`、`taskId`。完成任务验证本地文件后返回；恢复步骤核对配置。未决文字请求不重发。未决媒体先读取原Flow回执，只有submitted/complete可复用原幂等ID；不存在/失败/未知均停止。
- `flowExport`：`directory`、`taskId`、`workflow:true`、`canvas`、有序`shots`。核对总任务审核清单，不接收缺镜、外来回执、错hash或重复素材。完成导出复用相同文件，不再编码。

任务文件 `tasks/<taskId>/state.json`。素材 `assets/<nodeId>/`。自动画布 `autoFilm<taskId>.json`。导出 `exports/flow<digest>/film.mp4`。

任务执行依赖正在运行的单进程服务；刷新页面不影响执行，但服务重启不会盲目自动重放，需“核查原回执并继续”。没有宣称已做多进程调度、进程级常驻、自启动或任意故障自动恢复。

本卡加入自动画布指纹保护。旧验收任务是在保护代码加入前启动，原始任务状态可能没有 `canvasHash`；重启后“完成任务回读”已测通过。不要手工把它改为未完成并声称真实中断恢复。旧状态迁移以及原生画布被正常浏览/布局操作重写时的恢复策略，后续仍应专门评估。

## 7. 真正生成的验收样片

总任务：`30c84f8e-4b6a-4bdd-bcf1-5e4699da241c`。

剧本《等候》：雨后旧火车站空候车室，长椅上红书与黄铜怀表；第一镜推进，第二镜近景横移。没有人物或对白。

真实成片：
`/Users/niuniu/Desktop/flow cli/toonflow/data/workspaces/flowAcceptance/exports/flowe344ddcf55d9fdfb4db4/film.mp4`

16秒、1280×720、30fps、H264、无音轨、6,315,770字节。
SHA256：`f6d96d01643850d3dc61f6ad193ece1c425ee94196f8e25fcd730a4dfa7a6121`。

|步骤|Flow job ID|request ID|
|---|---|---|
|镜头1图片|e0f5c7e1-8366-6250-b9e2-05854b3ccfd7|e551ae23-7e49-4720-91ab-a9a6982d135b|
|镜头1视频|47ec90ad-fccd-d35a-1cc5-474dcd68ce4b|e956a939-e897-4775-8672-c26ac29b518a|
|镜头2图片|a12b27ee-9a92-f160-6119-ddda45f2322a|ffbe80b2-16b4-405a-8232-4433a0ab7044|
|镜头2视频|a1baa9fe-4356-9cf1-6ecc-5b570d4e3c3a|59449f37-68f1-4477-ad69-1b79d5cd2309|

两组Flow项目各2条请求，状态COMPLETED，retry_count均0。不是同一视频拼两遍，也不是复用上一张卡素材。

证据：
- `toonflow/docs/autoFilmAcceptance.json`：完整回执、hash、模型、19项检查、限制。
- `toonflow/docs/autoFilmWorkflow.md`：配置/接口/恢复说明。
- `flowkit_repo/docs/benchmarks/workflow-boundaries/toonflow-autofilm-acceptance-20261015.json`：规划仓库留档。
- `flowkit_repo/output/toonflow-local-20261015/geminiAutoFilm.png`：工作台实际播放到6/16秒。
- 同目录 `geminiAutoCanvas.png`：原生4节点真实回填。
- 任务目录中的 `filmFrame1.jpg`、`filmFrame7.jpg`、`filmFrame9.jpg`、`filmFrame15.jpg`：独立抽帧审查。

## 8. 已做测试与不可夸大的边界

已通过：前后端typecheck/build；19项HTTP/运行时检查；原生界面单次启动；实际视频播放；刷新、新标签、Toonflow服务重启；同任务/同成片hash及mtime不变；恢复检查后仍只有4条Flow请求。

19项包括非法镜头数/字段/ID/供应商/模型/路径，幂等启动与输入冲突，重复导出/错误顺序/hash/根任务，配置变动、未决文字/媒体回执、画布冲突、已知检查点恢复、完成任务恢复，以及真实Gemini输出被不匹配的严格结构拒绝。

其中5项是**手动修改本次任务的持久状态进行故障注入**，检查后恢复原字节；不是实际付费瞬间断电。不得改写为实机断电、上游超时或账号切换测试。

本次4次审核均首次接受，因此“同模型最多重做2次”的实现尚未在这次真实流程触发；不可声称该分支已真实验收。Gemini审核仅逐镜头，未做跨镜联合一致性检验；独立审查已发现怀表细节变化。

首次UI刷新播放器有blob地址提前释放的问题，已修复并复验，最终readyState=4、duration=16、播放非暂停。

此前FlowKit的29项相关Python单测是上一卡结果；本卡没有重新运行它们，也没改FlowKit生产Python代码。不要把历史测试列成本轮新跑的测试。

## 9. 规划与下一步建议（尚未执行）

优先阅读：
1. `flowkit_repo/.planning/phases/01-workflow-boundaries/01-LOCAL-WORKBENCH-REVISION.md`，D-17到D-20为最新方向。
2. 同目录 `01-LW-06-TASKS.md`。
3. `toonflow/docs/autoFilmWorkflow.md` 与验收JSON。

`.planning/state.json`下一步指向 LW-07，但宏观阶段标题仍含早期原站工作流描述，不能据此恢复旧架构。整个Phase1/里程碑/项目没有整体完成。

建议先修订下一张任务卡再实现，重点：
- **跨镜一致性与审核缺口**：当前图片适配器只支持文生图，两个镜头独立生成，不能保证同角色/道具；需明确角色/道具参考图接入及跨镜审核合同，不要只调提示词就承诺一致性。
- **对白**：用户长期要求固定音色、精确台词、正面口型。当前静音流程会暂停有对白的剧本；需要明确实际可用的配音/口型接口、模型路由与真实验收。不能自动装工具，也不能猜测Omni具备所需控制能力。
- **恢复与常驻**：目前手动核查恢复、单进程执行；补真实中断场景、任务版本/画布保护迁移、服务常驻方案前须写清边界。
- **质量重做**：用真实不合格结果验收最多2次、独立镜头继续、失败阻断最终导出；区分质量失败与未知付费提交。
- 最后才扩到3–5分钟和整体验收；不要一次扩成另一个大工作台或安装新生态。

本轮只写交接报告，不启动下一张卡。后续接手应保留用户已经授权的真实生成消耗范围与配置选择；按用户下一条指令继续，先核对现场与任务卡，不重复询问已经确认的事项。

## 10. 接手操作清单

1. 阅读本报告、两个仓库AGENTS.md、上述最新任务卡和证据。
2. 只读核对git状态、3000/8100健康、原任务state.json和成片hash；不要先重载扩展或重启浏览器。
3. 在现有工作台“自动成片”里查看原任务并播放；必要时打开自动画布。
4. 修订下一张卡的范围、模型路由、验证标准，再按用户指令实施。
5. 只提交自己改动且已通过验收的文件。不要 `git add .`、`reset --hard`、`clean` 或处理历史未提交文件。

Toonflow校验命令（使用现有依赖）：
```sh
bun run --cwd apps/server typecheck
bun run --cwd apps/server build
bun run --cwd apps/web typecheck
bun run --cwd apps/web build
```
新增/改名路由时先 `bun run --cwd apps/server routes`，不要手改自动生成router.ts。服务端源码运行需在适当时机重启才加载新代码；Web构建完成后再刷新页面。

## 11. 仓库与操作注意事项

- Toonflow要求新增源文件小驼峰；磁盘操作用 `@toonflow/file`，完整快照用 `writeAtomic`。
- Toonflow AGENTS禁止新增测试模块/框架/脚本；本轮采用既有typecheck/build和必要HTTP/运行时手动验证，没有新增测试文件或依赖。
- FlowKit AGENTS要求生成使用现有batch/服务调度，不能写临时脚本循环代替工作流。本卡编排是Toonflow正式服务代码，底层复用现有FlowKit批量接口。
- FlowKit未提交变更主要在 `agent/services/seko_local_workflow.py`、`extension/manifest.json`、`extension/seko_page.js`、Seko脚本/测试及旧gap证据。都是历史工作，别覆盖、还原或一并提交。
- `flowkit_repo/extension.pem` 是敏感文件，绝不读取展示或提交。其他API Key、settings.json、运行环境文件同样不入Git。
- 不要将 Seko 上传成功、素材复用、参考图上传或局部UI跳转当作服务器生成接管。历史Seko 4/7与当前Toonflow LW-01..06是两条验收记录。
- 本轮没有重新实测LibTV/OiiOii，不根据聊天记忆编造其能力排名。
- 浏览器自动化用既有CUA；实际“用”配置实例已核对，不再反复要求用户退出/重载Chrome。

## 12. 可直接交给下一位AI的起始指令

> 请先读取 `/Users/niuniu/Desktop/flow cli/handoffReport.md`，并核对其中最新任务卡、提交、真实回执和当前运行状态。保留所有未提交历史工作，不安装任何新东西，不做模型或素材兜底，不重新绑定GPT-6.1-Sol。当前本地Toonflow + 本地中转Gemini + Flow双镜头静音自动出片已跑通；跨镜一致性、固定音色、精确对白和口型仍未验收。先按用户下一条指令修订任务卡，再执行、测试、真实验收、提交。用中文和内联可视化汇报，不把旧样片或状态注入当作新真实生成。
