# LibTV / OiiOii / Seko：三家真实结果

整理日期：2026-10-15。历史观察分别标日期；本次仅打开本地来源、建立索引和运行离线审计，没有重新生成或修改生产桥。当前主线按用户决定为 **Seko**。

## 证据口径

[证据索引](benchmarks/workflow-boundaries/evidence.json)将证据合同有效、真实观察和可行性分开。离线通过只表示来源字节、引用和已复核范围相符，`feasibility=unassessed`；不证明当前线上接入或整条工作流。每行有独立 claim_id，tested 包括实际观察到的失败反例。discovered 为仅发现，unimplemented 限于已检查实现，blocked 为证据合同尚未建立，unknown 为当前未核验。

`supported_capabilities` 是执行器打开来源后逐项登记的能力范围；检查器能拒绝扩大字段范围，不能替代来源语义复核。历史日期只有本机日精度时不编造 UTC 时刻。code_rev 标记被审阅归档/源码的 Git 版本；私有归档没有 Git 版本时引用本次审计基线并明确说明，不声称是历史线上部署版本。

## 平台与入口矩阵

| claim_id | 平台 / 入口 | 历史实测或发现 | 当前状态待核验 | evidence_ids / 来源 | 局限 |
| --- | --- | --- | --- | --- | --- |
| `claim_id:seko-canvas-stale-shot` | Seko / canvas | tested；2026-10-13 | unknown：当前线上未重测 | `ev-seko-stale-shot`：[来源](benchmarks/seko-20261013/node-update-probe.json) | tested 表示反例被实际观察到：节点替换没有自动传播到所有既有镜头；不是完整替换通过。 |
| `claim_id:libtv-canvas` | LibTV / canvas | tested；2026-10-13 | unknown：当前线上未重测 | `ev-libtv-canvas`：[来源](benchmarks/libtv-20261013/acceptance.json) | 外部调度 Flow 真生成并同节点回填；原站生成按钮未拦截。 |
| `claim_id:libtv-editor` | LibTV / editor | tested；2026-10-13 | unknown：当前线上未重测 | `ev-libtv-editor`：[来源](benchmarks/libtv-20261013/replacement-audit.json) | 显式刷新连线后 15 项通过；16 秒成片、两段蓝条、解码和音轨通过。 |
| `claim_id:libtv-editor-cache` | LibTV / editor | tested；2026-10-13 | unknown：当前线上未重测 | `ev-libtv-editor-cache`：[来源](benchmarks/libtv-20261013/stale-audit.json) | 渲染读取新节点，但 no_stale_source_reference=false；成片正确不证明全部引用一致。 |
| `claim_id:libtv-agent-skill` | LibTV / agent_skill | unimplemented；2026-10-13 | unknown：当前线上未重测 | `ev-libtv-agent-skill`：[来源](LIBTV-FLOW-LIVE-RESULT.md) | 历史报告明确 TV Director 自动任务接管未验证、网页按钮未改写；不能推导平台永远不支持。 |
| `claim_id:oiioii-canvas` | OiiOii / canvas | tested；2026-10-13 | unknown：当前线上未重测 | `ev-oiioii-canvas`：[来源](benchmarks/oiioii-replacement-20261013/render-audit.json) | asset ID 保留、URI 更新、回下载哈希匹配；不证明自动传播或本轮 Flow 新生成调度。 |
| `claim_id:oiioii-editor` | OiiOii / editor | tested；2026-10-13 | unknown：当前线上未重测 | `ev-oiioii-editor`：[来源](benchmarks/oiioii-replacement-20261013/render-audit.json) | 显式更新片段后 ID/时序/音量保留；sourceReferences 仍旧，严格 16 项仅 15 通过，整体失败。 |
| `claim_id:oiioii-agent-skill` | OiiOii / agent_skill | discovered；2026-10-13 | unknown：当前线上未重测 | `ev-oiioii-agent-skill`：[来源](REA-INVESTIGATION.md) | 仅记录静态 IPC/MCP 通道；核心范围命中纠正全量 no-match，未证明 Agent 能调用自有 Flow、没有原生生成接管。 |
| `claim_id:seko-canvas-native` | Seko / canvas | tested；2026-10-13 | unknown：当前线上未重测 | `ev-seko-canvas-native`：[来源](benchmarks/seko-native-flow-20261013/audit.json) | 两次指定工程原生按钮触发、两份不同新 Flow 视频及回填；观察窗原站生成请求 0。只限当时首帧 8 秒横屏测试，非整个 Agent。 |
| `claim_id:seko-editor` | Seko / editor | tested；2026-10-13 | unknown：当前线上未重测 | `ev-seko-editor`：[来源](benchmarks/seko-20261013/replacement-audit.json) | 指定原 shotId 的 REPLACE 后 14 项通过；16.041667 秒多一帧，无独立同构来源缓存字段，不能虚构缓存/精确口型通过。 |
| `claim_id:seko-editor-discovery` | Seko / editor | discovered；2026-10-14 | unknown：当前线上未重测 | `ev-seko-editor-discovery`：[来源](../output/seko-interface-audit-20261014/rea-input/shot-BflClSjB.js) | 只读归档确认独立 guodong-studio/v1/shots/{id}/gen-video 与 gen-image；仅发现接口，不证明已接管。 |
| `claim_id:seko-agent-skill` | Seko / agent_skill | discovered；2026-10-14 | unknown：当前线上未重测 | `ev-seko-agent-skill`：[来源](../output/seko-interface-audit-20261014/rea-analysis.json) | 7 模块/7 解析/0 失败、672 findings、443 节点/687 边；chat 语义图超预算，整体不完整。事件流和 Skill 元数据不能证明生成前控制。 |
| `claim_id:seko-canvas-current` | Seko / canvas | 历史实测不替代本行源码结论 | unknown；2026-10-15 本地源码核对 | `ev-seko-canvas-current`：[来源](../extension/seko_page.js) | 本地源码仅定向转交 canvas-node/gen-video，硬编码模块尚待 01-02 当次线上验证；旧刷新成功不能证明当前兼容。 |
| `claim_id:seko-editor-current` | Seko / editor | 历史实测不替代本行源码结论 | unimplemented；2026-10-15 本地源码核对 | `ev-seko-editor-current`：[来源](../extension/seko_page.js) | 在已检查页面桥范围内没有编辑器转交分支；宽泛视频 fetch 阻止不能算 Flow 接管，不能推断所有站点路径。 |
| `claim_id:seko-agent-current` | Seko / agent_skill | 历史实测不替代本行源码结论 | blocked；2026-10-15 本地源码核对 | `ev-seko-agent-current`：[来源](../extension/seko_page.js) | 本地转交仅画布首帧路径；Agent 服务端生成前控制未建立。属于 contract_unproven，不是技术不可行，也不是登录失败。 |

## 保留的历史媒体、引用和质量边界

三家最初沿用同一 Flow A 风景视频与 B 识别素材（左右翻转、顶部蓝条），各编排两个 8 秒片段。统一文戏《雨停之前》当时只准备/保存，未制作该剧本的对话成片。三家原素材/节点 ID 均保留；Seko nodeId 不变而 genId 新增。B 版两段蓝条、解码及音轨检查通过；这不代表整部剧情、精确台词、固定音色或口型已通过。

- **LibTV**：[实测过程](LIBTV-FLOW-LIVE-RESULT.md)。官方 CLI 1.1.3 已用于上传、节点回填、显式刷新入边及原站合成；源缓存刷新前仍旧。外部任务调度 Flow 真生成、回填、成片曾通过；原生按钮和 TV Director 接管未实现。历史成片位于 `output/libtv-test-20261013/rendered-live/Flow回填-16秒合成验收 成片.mp4`，16 秒。
- **OiiOii**：[实测过程](OIIOII-FLOW-LIVE-RESULT.md)。已有 CLI + Agent UI 用于片段显式更新；自动传播失败，片段 resourceUri 原先仍旧。更新后 clipId、时长、裁剪与音量保留，重开持久化通过，但 sourceReferences 残留旧 URI，不能记为严格替换通过。本轮没有新 Flow 生成调度或原生生成接管。历史成片 `output/platform-test-20261013/oiioii-replacement-16s.mp4`，16 秒。
- **Seko**：[初次实测](SEKO-FLOW-LIVE-RESULT.md)区分画布节点、既有分镜、显式 REPLACE；无独立同构来源缓存字段，不虚构其通过。历史成片 `output/seko-test-20261013/seko-live-16s.mp4`，B 对照 `seko-b-16s.mp4`。初次 LibTV/Seko 新生成各将同一新 8 秒片段重复两遍，只证明技术链路，不构成两镜新剧情或同剧本质量竞赛。
- **Seko 后续按钮实验**：[接管实测](SEKO-NATIVE-FLOW-TASKS.md)使用两段不同的新视频（纸船、白鹭），24 项实物审计通过，原站生成 HTTP 请求在记录窗口中为 0；第一段未保存 hasMore 字段，不能宣称无限范围全量网络审计。实际自动上传/原站内容检查/原镜头回填/原站出片及重开持久通过，临时会话接管随后解除。成片 `output/seko-native-flow-20261013/seko-native-flow-16s.mp4`。该结果只更新指定画布首帧视频按钮范围，不覆盖 Agent/Skill。
- Seko 两类 16 秒成片均为 16.041667 秒，比源片段多一帧；对齐后初次 SSIM >0.986，后续两镜为 0.987288/0.990907。未据此验收精准对白同步。
- [常驻/对白实验](SEKO-PERSISTENT-DIALOGUE-TASKS.md)曾验证旧构建的刷新/重开接续；4 镜约 20 秒是 Flow 画面加 Seko 配音/口型重生成，不能保留原 Flow 动作的限制仍在。输入音色/台词与成片音轨相关性不是逐字听辨或逐音素口型认证；这些质量项未完成独立验收。
- [提示词 A/B](SEKO-PROMPT-AB-TASKS.md)是有限静音首帧规则、每种一个样本的实验；没有证明稳定质量提升。三家无人值守整部剧本流水线均未交付。

## 静态归档与当前兼容性

2026-10-14 私有只读归档实际存在：[sources.json](../output/seko-interface-audit-20261014/sources.json)、[rea-analysis.json](../output/seko-interface-audit-20261014/rea-analysis.json)。后者是真正 JSON，7 文件/7 解析成功/0 失败、672 findings、443 图节点、687 条边；chat 语义图超过结果预算，整体图不完整。旧 [rea-evidence.json](../output/seko-interface-audit-20261014/rea-evidence.json)实际上是 TOON 文本，未修改或当 JSON 解析。本机归档不随 Git 分发，缺失会明确审计失败。

编辑器有独立生成路由；Agent 有 plan/next-ep 事件入口，官方 Skill 详情只有元数据的既有观察不代表可移植执行正文。静态名称和后置事件均不能证明厂家生成前可暂停或注入外部结果。[REA 首轮调查](REA-INVESTIGATION.md)的 10 文件/两文件实验与上述 7 模块调查属于不同历史批次，不能混算。

2026-10-14 两个硬编码构建模块曾返回 404；这不是本日重新请求结果。01-02 负责当次网站、构建、官方/玩家候选与模型路由取证。当前矩阵不填写未经核验的实际模型 key，也不更改提供方。

## 当前决策与可重复验收

旧“LibTV 优先”建议属于最初 A/B 结果背景，当前以用户指定的 Seko 为主线。OiiOii 来源元数据反例保持开放。原先建议的 36 秒六镜短文戏、随后 3–5 分钟整集仍是后续验收目标，不表示已交付；用户剧本与生产输入格式尚未确定。

`python3 -m unittest tests.test_workflow_evidence_probe tests.test_platform_probe tests.test_seko_probe -v`

`python3 scripts/workflow_evidence_probe.py --evidence docs/benchmarks/workflow-boundaries/evidence.json --stage matrix`

tracer stage 仍可用于基础合同检查；matrix 额外检查三家×三入口、两个关键历史反例、报告与索引 ID/证据一致。单测合成资料仅存在临时目录；实际 RED/GREEN、来源验收及逐任务提交见 [01-01 执行记录](../.planning/phases/01-workflow-boundaries/01-01-SUMMARY.md)。研究阶段 33 项 Python/16 项 Node 是历史运行记录，本次结果以该执行记录为准。
