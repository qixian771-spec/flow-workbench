# Phase 1 执行补充 — 2026-10-15

用户本轮要求：按任务卡一个接一个执行，边测边记录，测试和验收后提交；不安装新东西，不兜底；写清任务到模型的路由。

## 顺序与提交

3 组计划顺序执行，共享当前工作区；workflow.use_worktrees=false 与 parallelization=false。保留原有 main 分支，不推送。extension.crx/extension.pem 与任务无关，不读其内容、不提交。任务先写反例并观察 RED，再实现 GREEN 和证据验收，**不提交未通过的 RED 状态**；用户要求优先于通用 TDD 分步提交习惯。记录真实 RED/GREEN 输出即可。

## 模型路由补充验收

01-02 调查候选时记录可见模型；01-03 在 docs/SEKO-WORKFLOW-BOUNDARIES.md 增加路由表，并在 evidence.json 的逐步合同关联对应证据：任务类型、厂家原模型/服务、自有目标提供方、用户称呼、实际 model key、配置来源、当次观测/历史观测、可用状态、禁止自动替换。

- 用户目标：图片走自有 Flow（此前称 Nano Banana 2.1），视频走自有 Flow Omni。模型称呼不能代替实际 key；从现有运行配置、模型目录或真实请求核验，有差异明确展示，不擅自换模型。
- 厂家保留：编剧、拆镜、配音、口型、剪辑；模型不可见则标“厂家未暴露/待核验”，并写实际服务/调用点，不能猜型号。
- 区分当前生效路由与后续目标路由；Phase 1 不修改生产提供方配置，不伪称已完成全部替换。
- 未知提交结果不得重发；质量失败最多同模型重做两次是后续实现约束。

## 本轮开发代理路由

GSD model_profile=inherit，resolve_model_ids=omit；执行器 gsd-executor 的 resolver model 为空、effort=high，故继承当前会话模型，不指定其他型号。代码审查和阶段验收使用对应 GSD 角色，派发前记录 resolver 结果。继承模式未返回具体模型 ID 时，不把推测型号写成实际型号。未使用外部 cross-AI 运行器，不安装或更新 GSD。

## 完成口径

每卡测试与证据复核后提交；阶段独立检查另行判断。真实技术阻断和访问/证据不足区分；后者保持未完成，不伪装可行或不可行。模型路由表遗漏任务、无证据却填实际 key，均不通过补充验收。

## 执行后核验记录

- 执行器、审查器、修复器、阶段验收器resolver均model为空（继承当前会话）、effort=high；不宣称具体模型ID。
- 7张卡与4个审查修复顺序执行。最新107 Python、16 Node通过；完整真实生成链仍pending。
- REVIEW原始4项错误通过已修复并保留反例/处置。CR-03提交顺序瑕疵及amend修正见REVIEW-FIX，不隐藏过程。
- validate-phase完成覆盖审计，真实运行缺口保留manual-only/partial；secure-phase按已编写威胁表做L1核验。
- ui-review适用性：本轮无前端修改、无UI-SPEC；三次wave UI gate frontend=false。UI审查跳过，不生成虚构评分，不安装浏览器/测试工具。
- scope resolver因中文SUMMARY提交表出现no-task-commit-rows；审查明确限定7份源文件，修复仅3文件，不扩大范围。
- 配置中的use_worktrees=false和allow_default_branch_commits=true落实用户顺序执行/当前分支提交授权；无远程推送。
