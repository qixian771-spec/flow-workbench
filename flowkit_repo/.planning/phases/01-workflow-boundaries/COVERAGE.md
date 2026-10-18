# Phase 1 — 范围与来源覆盖

No external API integration: Phase 1 调查既有原站/桥入口、采集只读运行证据并验证本地报告合同，不实现外部服务适配或新的 API/SDK 接入；D-02 的 Flow 图视频和回填属于 Phase 2/3，D-03 的编剧、拆镜、配音、口型、剪辑继续保留厂家服务。

此声明分类的是交付责任。调查可读取现有接口，不能因此把所有厂家能力扩为本阶段实现。实际生产桥、调度恢复、质量重做、声音验收分别属于 Phase 2～6；统一工作台已延期。本阶段没有 ORM schema 修改或包安装，schema-push/包安装 checkpoint 条件不成立。assumption-delta 扫描实际返回 detected=false。AI/UI 实现均不在范围，无 AI-SPEC/UI-SPEC 交付要求。

## 四源覆盖审计

| SOURCE | ID | 内容 | Plan / Task | 状态 |
|---|---|---|---|---|
| GOAL | Phase 1 | 调用链、接管边界、版本、接入清单 | 01-01～03 | COVERED |
| REQ | BASE-01 | 三家能力与入口范围 | 01-01-01/02 | COVERED |
| REQ | BASE-02 | 选中流程与生成前控制 | 01-02-02、01-03-01/02 | COVERED |
| REQ | BASE-03 | 当前版本与依赖匹配 | 01-02-01 | COVERED |
| REQ | BASE-04 | 接入项与真实可行性/阻断 | 01-03-02/03 | COVERED |
| RESEARCH | Evidence | 分层声明、真实哈希、部分 REA、TOON/JSON 区分、旧引用反例 | 01-01 | COVERED |
| RESEARCH | Build | archived/cached/current、HTTP/类型/导出、桥状态 | 01-02-01 | COVERED |
| RESEARCH | Candidates | 官方/玩家、同输入、人工成本、摘要不等于执行源码 | 01-02-02 | COVERED |
| RESEARCH | Boundary | 浏览器/服务端、派发时序、输入输出恢复、全局保护误伤 | 01-03-01/02 | COVERED |
| RESEARCH | Native services | 口型重生成与最终媒体来源，责任层级 | 01-03-01/03 | COVERED |
| RESEARCH | Validation | 标准库验收器、命名负例、契约有效与可行分离、scope suite | 三份计划及 VALIDATION | COVERED |
| RESEARCH | Security | 脱敏、第三方资料不可信、零安装、L1/high | 三份 threat_model | COVERED |
| CONTEXT | D-01 | Seko 原站入口 | 01-02 truths/02-02 | COVERED |
| CONTEXT | D-02 | Flow 图视频+真实回填的接入边界 | 01-03 truths/03-01/03-03 | COVERED；生产实现后续 |
| CONTEXT | D-03 | 保留厂家服务 | 01-03 truths/03-01/03-02 | COVERED |
| CONTEXT | D-04 | 禁止兜底/假完成 | 01-01 truths、所有禁止项及控制验收 | COVERED |
| CONTEXT | D-05 | 官方/玩家都比较 | 01-02 truths/02-02 | COVERED |
| CONTEXT | D-06 | 完整流程和少人工优先 | 01-02 truths/02-02 | COVERED |
| CONTEXT | D-07 | 画风开放 | 01-02 truths/02-02 | COVERED |
| CONTEXT | D-08 | 无现成剧本/输入格式开放 | 01-02 truths/02-02 | COVERED |
| CONTEXT | D-09 | 同模型最多两次质量重做 | 01-03 truths/03-03 | COVERED；后续约束交接 |
| CONTEXT | D-10 | 局部暂停/独立继续/全部合格 | 01-03 truths/03-03 | COVERED；后续约束交接 |
| CONTEXT | D-11 | 不提前实现质量调度 | 01-03 truths/03-03 | COVERED |
| CONTEXT | D-12 | 一次一题可点击/接受自由说明 | 01-03 truths/03-03 | COVERED |
| CONTEXT | D-13 | 需求已收口 | 01-01 truths/01-01 | COVERED；历史决定 |
| CONTEXT | D-14 | 方案到提交、无安装、讨论状态真实 | 01-01/03 truths、所有卡与 VALIDATION | COVERED |

## 规划依据与依赖

已有研究和 PATTERNS 足以作本地标准库方案，Level 0 无新增依赖；当前网站事实仍需执行期新取证。history-digest 无已完成阶段；graphify disabled，不修改设置。estimate-calibration 实际 factor=1、sample_count=0、confidence=low；三计划 raw/tokens 为 28000/30000/34000。

Wave 1 → Wave 2 → Wave 3；三计划共享证据/验收器/测试文件，显式顺序执行。现存生产路径经 git ls-files 确认；新阶段 RESEARCH/PATTERNS/VALIDATION 是本轮待提交源文件，不是安装镜像。output 下归档仅作为只读输入，缺失明确报告。本次仅写计划和验证映射，无生产实现、运行采样、安装或业务测试。

四条 spec-less 未分类边缘记录完整保留在 PLAN 与 VALIDATION；7 条召回的产品禁止项均 descriptor-less、status=unresolved、verification=null，保持 flagged-unverified，没有自动解除或虚构 wired checks。证据源完整性/类型等一般正确性由单测承担；凭据/注入等通用安全归 threat_model。
