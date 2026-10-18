# Requirements: 成熟漫剧工具接入自有 Flow

**Defined:** 2026-10-14
**Core Value:** 成熟工作流真实调用自有 Flow、回填素材并自动出片。

## v1 Requirements

### 成熟工作流与接管边界

- [ ] **BASE-01**: 用户能查看三家已验证能力与未完成项，并区分按钮、编辑器、Agent/Skill 的接管范围。
- [ ] **BASE-02**: 用户能针对选中的 Seko 成熟工作流，查看每一步输入输出、实际执行方及生成前可控边界的证据。
- [ ] **BASE-03**: 用户能知道当前网站版本和接入是否匹配；过期模块或无法接管的路径必须明确标记。
- [ ] **BASE-04**: 用户能得到目标工作流的接入清单和真实可行性结论；不能完成的步骤有具体阻断证据。

### Flow 图视频与模型适配

- [ ] **FLOW-01**: 用户能将目标工作流的图片生成任务交由自有 Flow，并得到可核验的新图片。
- [ ] **FLOW-02**: 用户能将目标工作流的视频生成任务交由自有 Flow，并得到可核验的新视频。
- [ ] **ADAPT-01**: 用户能追踪源提示词、参考图、转换后的参数和实际使用的模型；不支持的意图明确停止。
- [ ] **ADAPT-02**: 用户能查看同镜头同参考的原提示词与转换版实物对比及局限，优化结论有证据。

### Skill 串联与原站自动出片

- [ ] **SKILL-01**: 用户从选定成熟 Skill/工具发起创作时，目标图片与视频生成步骤实际走自有 Flow，且不重复触发厂家对应生成。
- [ ] **RETURN-01**: 用户的 Flow 结果与任务状态能回填到正确的素材、镜头及引用，原工作流可以继续执行。
- [ ] **RETURN-02**: 用户能从已回填的多个不同镜头自动导出原平台短片，成片确实使用新素材。

### 常驻运行与中断恢复

- [ ] **OPS-01**: 用户刷新页面或重启本机服务后能继续已知任务，不重复提交已存在的付费生成。
- [ ] **OPS-02**: 用户能看到提交、生成、回填、合成阶段及失败原因；写入结果未知时先核对再继续。
- [ ] **OPS-03**: 网站更新或能力失配时接入明确停止并定位受影响入口，不静默调用厂家生成或替代模型。

### 对白、固定音色与口型

- [ ] **VOICE-01**: 用户为角色指定的音色在短剧不同镜头中保持一致，有可回放的验收依据。
- [ ] **VOICE-02**: 用户剧本中的对白逐句准确，无漏句、错句或额外台词，并与字幕对应。
- [ ] **VOICE-03**: 正面说话镜头的口型与实际对白同步，通过独立检查；不以生成成功代替验收。

### 整集自动化与整体验收

- [ ] **FILM-01**: 用户提交一个完整剧本后，系统自动完成拆镜、素材生成、回填与合成，产出横屏 3–5 分钟剧情短片。
- [ ] **FILM-02**: 用户能从成片追溯每镜源剧本、模型任务及素材，角色、场景、声音连续性经过整体验收。
- [ ] **FILM-03**: 用户能查看每张任务卡、里程碑和整体的测试、验收与提交记录，明确完成与未完成部分。

## 已确认的跨阶段约束（2026-10-14）

以 `.planning/phases/01-workflow-boundaries/01-CONTEXT.md` 的 D-01～D-14 为准：

- BASE-02/BASE-04：在原站比较官方和玩家成熟 Skill，优先完整流程和少人工；不预先限定画风或假设用户已有剧本。
- FLOW-01/FLOW-02/SKILL-01：首版只替换图/视频生成；编剧、拆镜、配音、口型、剪辑继续使用厂家能力。
- FLOW-01/FLOW-02/OPS-02：对技术成功但质量不合格的画面自动检查，同模型最多重做 2 次；仍失败明确暂停并说明原因。
- OPS-01/OPS-02/RETURN-02/FILM-01：暂停失败镜头及依赖，其他独立镜头继续；全部合格才能输出最终成片，不跳过失败镜头。
- VOICE-01～VOICE-03：验收目标保留，但不要求将厂家声音/口型服务改成自有后端。
- 不允许失败后改回厂家图/视频、改模型或伪造完成。未知提交结果不属于可直接重发的质量重做。

## v2 Requirements

- **MULTI-01**: 在 Seko 主线闭环后，按已记录的能力矩阵扩展 LibTV/OiiOii 原生工具与 Skill 接管；不丢弃既有集成成果。
- **EXTEND-01**: 用户所说的“其他能力”待具体讨论后进入范围，不预先猜测功能。

## Out of Scope

| Feature | Reason |
| --- | --- |
| 新装 ComfyUI/其他软件 | 用户明确禁止 |
| 激烈打斗优先 | 用户选择文戏 |
| 静默换厂家接口、替代模型、伪造完成 | 禁止兜底 |
| 独立重造整套创作平台 | 当前方向为复用成熟工具 |

## Traceability

| Requirement | Phase | Status |
| --- | --- | --- |
| BASE-01 | Phase 1 | Gaps Found |
| BASE-02 | Phase 1 | Pending |
| BASE-03 | Phase 1 | Gaps Found |
| BASE-04 | Phase 1 | Pending |
| FLOW-01 | Phase 2 | Pending |
| FLOW-02 | Phase 2 | Pending |
| ADAPT-01 | Phase 2 | Pending |
| ADAPT-02 | Phase 2 | Pending |
| SKILL-01 | Phase 3 | Pending |
| RETURN-01 | Phase 3 | Pending |
| RETURN-02 | Phase 3 | Pending |
| OPS-01 | Phase 4 | Pending |
| OPS-02 | Phase 4 | Pending |
| OPS-03 | Phase 4 | Pending |
| VOICE-01 | Phase 5 | Pending |
| VOICE-02 | Phase 5 | Pending |
| VOICE-03 | Phase 5 | Pending |
| FILM-01 | Phase 6 | Pending |
| FILM-02 | Phase 6 | Pending |
| FILM-03 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0

*Last updated: 2026-10-14 after initialization from confirmed conversation requirements*

## Phase 1 独立验收记录（2026-10-15）

阶段结论gaps_found，按GSD规则撤回本阶段全部Complete发布状态；这不否定BASE-01/03已有证据核验通过。01-VERIFICATION.md保留逐项判断：BASE-01/03已证，BASE-02/04缺真实同稿比较、选定流程与前置控制/完整可行性证据。补齐并重验前不宣布阶段完成。


## 2026-10-15 本地编排范围修订

D-15 生效：BASE-02/04、SKILL-01、RETURN-01 的执行权威改为本地 run/step；Seko 可取得的界面／Skill 及素材工具仍复用。旧云端 run 恢复未完成。仅本地部署页面不满足要求；缺 Skill 正文不能据元数据替写冒充。其他模型、质量、对白及零安装约束不变。

修订依据：[01-LOCAL-REVISION.md](phases/01-workflow-boundaries/01-LOCAL-REVISION.md)。
