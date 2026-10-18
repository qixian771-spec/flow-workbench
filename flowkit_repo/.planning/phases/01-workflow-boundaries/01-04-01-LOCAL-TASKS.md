# 01-04-01 本地适配执行卡

用户已明确要求完成方案后直接执行；D-15 本地编排、D-16 GPT-6.1-Sol 生效。仅本卡；后六卡不启动。

## 实现方案

复用 sekoplatform/seko-video-creation @ f20eeb886c10cdd04e6f3bfef40a563bc9bd8628 的完整公开工作流、PLAN/TASK_QUEUE 状态结构与策划输出字段。保存原文、MIT 许可及哈希。适配层明确替换原先不透明的 plan-tasks/story-tasks 调用，不能称为站内 Skill 14/29 的复刻，也不调用原厂生成。

在既有 Flow Kit 服务中增加本地作业执行器。沿用现有扩展的认证消息通道和 /api/seko/jobs 路径，不安装、不增加浏览器权限。新作业使用独立命名空间和 workflow 标记，与历史视频作业区分。临时页面适配器只进行明确构建的原站上传、审核、建节点和读回；原云端等待任务保持不动。

执行序列：创建 local run → GPT-6.1-Sol 输出单镜结构化策划 → 创建新 Flow video/scene → batch 提交新图 → collect 校验完成及媒体 → 浏览器自动上传/审核/建节点/读回同字节 → 本地接受同 run/step 回执 → GPT-6.1-Sol 读取真实素材身份生成下一镜头动作计划 → 同 run 到达 video_ready_gate。最后一步仅计划，视频派发留给后续路径验证，不能把本卡说成视频或成片验收。

文字模型固定 codex-cli/gpt-6.1-sol，low；图片固定 Flow NANO_BANANA_2_1→BELUGA；后续视频固定 Omni abra_i2v_8s/8s/720p/横屏。所有返回先由确定性代码校验，模型无权调用厂家 API 或自行确认回填成功。没有替代模型、替代素材或失败后继续逻辑。

## 顺序内部任务

| 顺序 | 产物／主要文件 | 测试与停止条件 |
|---|---|---|
| A 来源与合同 | assets/seko-public-workflow 原文/许可/来源；本卡 | 哈希对应固定提交，明确原文和适配差异 |
| B 本地执行器 | agent/services/seko_local_workflow.py；tests/test_seko_local_workflow.py | RED→GREEN：身份、固定路由、去重、未知结果停止、上传不等于完成、同 run 续行 |
| C 现有 API 与页面回填 | agent/api/seko.py；scripts/seko_local_workflow_page.js；对应测试 | 原认证仍有效，旧作业兼容，浏览器仅非生成写入；完整媒体 hash 回读 |
| D 真实单次运行 | output/seko-local-live-*、脱敏验收 JSON | 一次页面启动后链路自动推进；不由助手逐步提交；新 Flow request/media；Seko node/gen；下一步引用一致 |
| E 回归、验收和提交 | 本卡 SUMMARY、STATE、审计报告 | 自动测试全部通过；真实证据核对、UI/产物可见、去重再次检查；精确文件提交 |

## 验收

1. 输入、来源 Skill hash、本地 run/step、文字调用、新 Flow request/media、回填节点和下游引用有完整有序记录。
2. Flow 新图可打开，回填前后字节 SHA256 相同，原站节点实际完成；本地接收后自动继续到不同步骤 video_ready_gate。
3. 所有生成来自 Flow；生成前就由本地执行器掌握派发权，页面禁止原厂生成写入且保存请求观察窗口。不得伪造 Seko 云端 ToolCallCompleted。
4. 重复 create/collect/checkpoint 不重复生成；错误 run/step/model/hash/节点、缺回执、提交结果未知均停止。页面重新读取同 job 返回相同状态；完整常驻跨重启调度留给 Phase 4。
5. 测试命令：`python3 -m unittest tests.test_seko_local_workflow tests.test_seko_resident tests.test_seko_flow_job tests.test_workflow_evidence_probe -v`；`node --test tests/test_seko_local_workflow_page.cjs tests/test_seko_generation_hook.cjs tests/test_seko_native_backfill.cjs`。
6. 新测试将由 B/C 创建，未运行前不得记录通过。若真实链未通过，只保存错误和进度，不提交或推进后卡。

## 实施风险控制

新路径对每次外部写入先落盘。发生不明结果时不重发；已知 Flow request 可只读查询。后端每作业进程文件锁加现有 API 锁；页面用 Web Locks 防双标签重复上传。模块构建失配立即报错。CLI 不载入用户配置、不启用 shell 工具，只允许结构化文字返回；stdout 中工具执行事件视为失败。原始 URL 和模型诊断只在忽略的 output 内，Git 只提交身份/hash/摘要。

计划自检：目标、固定路由、来源、真实续行、身份反例、提交门均已覆盖。未派发子代理；本轮按用户顺序执行要求内联完成，独立阶段验收留到阶段结束。本卡通过不自动关闭 BASE-02/04 或 Phase 1。


## 执行结果

A～E 完成，见 `01-04-01-SUMMARY.md`。实际 Flow 返回 JPEG，修订媒体合同为已验证 PNG/JPEG 原始字节；仅显式重检已完成请求可恢复收集，不重发生成。一次提交前提示词修复、一次同任务格式修复恢复均保留。真实验收通过；完整常驻和视频派发未包含。
