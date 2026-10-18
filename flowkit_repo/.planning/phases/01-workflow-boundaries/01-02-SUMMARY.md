---
phase: 01-workflow-boundaries
plan: "02"
subsystem: testing
tags: [seko, evidence, build-compatibility, skills, provenance]
requires:
  - phase: 01-01
    provides: 证据索引与范围校验
provides:
  - 当前三个旧构建依赖404与新标签桥启动失败的真实证据
  - 官方14及创作者合作29的同稿元数据对比和明确选择阻断
  - 本机图片及Omni模型配置事实，非实际请求证明
affects: [01-03, BASE-02, BASE-03]
tech-stack:
  added: []
  patterns: [read-only-browser-audit, unknown-manual-counts, source-bound-candidates]
key-files:
  created:
    - docs/benchmarks/workflow-boundaries/current-build.json
    - docs/SEKO-BUILD-COMPATIBILITY.md
    - docs/SEKO-WORKFLOW-BOUNDARIES.md
  modified:
    - scripts/workflow_evidence_probe.py
    - tests/test_workflow_evidence_probe.py
    - docs/benchmarks/workflow-boundaries/evidence.json
key-decisions:
  - "创作者合作Skill按明确署名纳入community，发布者官方与实际创作者分开；不额外要求独立于厂家。"
  - "双方仅元数据与来源对照，selection=blocked，实际人工次数null，comparison_complete=false。"
requirements-completed: [BASE-03]
requirements-pending: [BASE-02]
actuals:
  tokens: 17028
  tasks: 2
  commits: 2
plan_head_before: c8daf83d7c07f84df2c2a8d5451c0e0113787a37
plan_head_after: 7872e80eb8dfbd0a5bcf61c3401d046b84ecea35
duration: 15min
started: 2026-10-15T11:06:00Z
completed: 2026-10-15
status: complete
---

# Phase 01 Plan 02: 当前构建失配与同稿候选比较 Summary

**新标签真实桥启动失败、三个旧依赖当次404；官方14与创作者合作29同稿资料对比完成，但实际流程/人工成本缺证据，保留选择阻断。**

status: complete 仅表示本计划两张调查任务卡依照各自允许的“明确匹配/失配/未知”和“有据选择或明确选择阻断”交付。没有完成候选选择、完整工作流接管或Phase 1验收；BASE-02仍pending，feasibility=unassessed。

## Task Commits

| 卡片 | 测试 → 执行器来源验收 → 提交 | SHA |
| --- | --- | --- |
| 01-02-01 构建核对 | 34 tests；真实build合同27 evidence/15 claims/10 modules通过；新旧页面与响应逐项核对 | `dbe5b93` |
| 01-02-02 同稿候选 | 42 tests；真实candidates合同33 evidence/15 claims/10 modules/2 candidates通过，comparison_complete=false；双方详情及来源复核 | `7872e80` |

两次均在测试与证据验收后正常git commit，未跳hook；没有提交RED状态。6个交付文件，无生产桥修改。最终元数据另行提交，不纳入上面实测2个任务commit区间。

## 01-02-01 测试与验收

- RED：新增 `test_build_valid_matched_modules_blocked_bridge` 后运行，1 test/1 FAIL，stage_supported=false，因为build尚未实现。未提交失败版本。
- GREEN：实现build/--build后34 tests通过。反例包括错误audit、陈旧/未来/历史冒充current、200 HTML、缺导出、哈希脱链、无模块和无实际启动证据的ready。
- 实际CLI：build返回contract_valid=true、10模块观察。离线合同不会把真实404或unknown改写为兼容成功。
- 浏览器验收：旧标签显示新版本提示、5完成/1待检查，保留未刷新；独立新标签登录问候与原工程可见，实际桥报canvas动态import失败。没有重发未知任务。
- 当前同源GET采样：2026-10-15T11:10:59Z，LoginContext-CFHyujin、canvas-BZat8bJg、useOSSUploader-BaPQIV7u均404。三个当前页面新模块200 JavaScript并含所需符号，但语义等价未证实，保持unknown。
- 旧标签只读Debugger源/导出；历史sources.json/rea-analysis.json只读。canvas归档字节哈希与旧标签同为95e89d95…；另外两个旧依赖不在该sources清单。没有把缓存当服务器响应。
- /health extension_connected=true，但authenticated_connections=0；与Seko登录/项目和桥启动状态分别列出。没有导出或使用凭据。

## 01-02-02 测试与验收

- RED：新增 `test_candidates_metadata_only_blocked_is_valid`，1 test/1 FAIL，candidates stage尚不支持。未提交RED。
- GREEN：42 tests通过。反例覆盖缺官方/社区真实来源、混用输入、原稿哈希错误、未知人工次数写0、广告输出冒充已运行、作者与来源不符、缺少阻断原因。
- 实际CLI：candidates返回contract_valid=true，33证据/15声明/10模块/2候选，comparison_complete=false、feasibility=unassessed。
- 真实来源：原站/skill-community，官方14「BJD古偶甜宠剧」与合作创作者29「复古梦核情绪短片【你翔哥哥】」。后者明确署名与签约创作者介绍，官方发布与创作者分列，不增加“必须独立玩家”的要求。
- 同稿：原创《最后一班车》，SHA-256 e12ba3f6…；全文和purpose落盘，双方都使用original-dialogue-station-v1。未为其中一方额外补设定，也未提交网站。
- 实际流程与确认/编辑/搬运次数没有执行观察；全部count=null，outputs=advertised。选择保持blocked，不把宣传180秒闭环当实际成片通过。
- 当前客户端只读源码确认GET详情、PUT use和Agent handoff字段；尚未证明服务器生成前可暂停/替换。未点击use/生成。网络事件窗口存在truncated，仅使用具体详情请求状态，不宣称全量零请求审计。
- 本机GET /api/models于11:19:11Z保存脱敏实证 `ev-model-flow-catalog`：默认NANO_BANANA_2_1→BELUGA，Omni frame_to_video 8→abra_i2v_8s；明确configuration_only/actual_request=false。官方14的gmlm-3-flash仅历史metadata，不升级为当前实际请求。

## Overall Verification

- `python3 -m unittest tests.test_seko_probe tests.test_seko_flow_job tests.test_platform_probe -q`：33 tests通过。
- `node --test tests/test_seko_generation_hook.cjs tests/test_seko_resident_page.cjs tests/test_seko_native_backfill.cjs`：16 pass，0 fail/skip/todo。
- git diff --check通过；提交文档和采样无Cookie、Bearer、签名参数或完整第三方源码。无安装，无生成，无上传，无生产配置变更。extension.crx/pem与父代理config/执行说明未纳入任务提交。
- 来源语义验收由执行器阅读真实UI/响应/源码完成，不冒充用户本人验收；整体阶段检查由父流程继续。

## Deviations from Plan

- 按用户顺序，RED只记录不提交，GREEN与证据验收后提交；全局TDD mode=false，任务tdd=true仍执行RED→GREEN。
- 配置允许在既有main提交由父流程按用户授权设置；每次提交前root pin与protected检查均通过，未改分支或推送。
- 标准库HTTP证书链读取失败，未关闭校验；已有浏览器同源只读采样完成。没有新增工具或改变验证结果。
- 无生产功能偏离。调查结果包含计划允许的选择阻断，不作为可行/不可行结论。

## Deferred Issues / Next Plan

1. BASE-02：双方实际输出与人工成本未观察；需先建立图视频生成前控制，再安全同稿验证。selection仍blocked。
2. 当前桥三个硬编码资源404；新模块运行语义对应关系待后续适配核验，Phase 1不修生产桥。
3. 01-03可引用模型事实、候选来源与使用契约继续边界整理；不得伪造已选中/已接管/已完成阶段。

没有代码stub或跳过的自动测试。上述未知为真实证据缺口，非伪造空数据；按计划必须保留。

## Auth Gates

Seko既有登录正常，无认证阻断。作者外部社媒去参数访问跳到小红书登录；未登录，原站署名已有证据，因此不新增用户操作门槛。

## Self-Check: PASSED

6个交付文件及本SUMMARY实际存在；dbe5b93与7872e80均为HEAD祖先，无意外删除。提交计数从磁盘ledger测得2，diff字符/4实际17028；统计区间截至最后任务commit。
