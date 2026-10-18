---
phase: 01-workflow-boundaries
plan: "04"
card: "01"
status: accepted_local_image_tracer
completed: 2026-10-15
requirements_completed: []
---

# 第一卡：公开 Seko 工作流的本地适配

已完成方案、A～E 内部任务、自动测试和真实验收。缺口卡进度 1/7；01-04 整份计划、Phase 1、里程碑和整体均未验收。旧 Seko 云端恢复仍未成功，不修改旧证据结论。

## 交付

- 固定公开来源 `sekoplatform/seko-video-creation@f20eeb886c10cdd04e6f3bfef40a563bc9bd8628`，保留原文、MIT 许可、哈希；仅复用其公开规划／任务队列结构作为本地单镜适配，不声称取得站内 Skill 14/29。
- 既有 FlowKit 服务增加持久化本地执行器，复用已安装扩展的认证通道。每个外部写入前落盘，身份错配和未知结果停止，重复输入返回原任务。
- 文字明确使用现有 Codex CLI `gpt-6.1-sol`，low；图片明确使用 Flow `BELUGA`（原站显示 Nano Banana 2.1）。该路径关闭生成重试和扩展账号切换，无替代模型或替代素材。
- 页面适配自动下载 Flow 原始图片，上传、审核、建立 Seko 节点并读取验证 SHA256，然后回传同一 run/step；执行器自动再次调用 Sol，读取真实媒体和节点身份进入 `video_ready_gate`。
- 后续视频路由已写明 `flow / abra_i2v_8s / frame_to_video / 8s / 720p / HORIZONTAL`，本卡未派发视频。

## 真实结果

| 证据 | 实际值 |
|---|---|
| local run | eedacf2c-49c2-4b6f-9f02-652d60834930 |
| image step | generate_image:1 |
| Flow request | 315a918c-3051-4da0-b814-5a2179a1d817 |
| Flow media | b587a425-a9dc-4759-921b-6c3eadba7e55 |
| Seko node / gen | 2110766758585061377 / 2110766758589255682 |
| 原图与回读 SHA256 | 3cc1893ebeb640f98e09ce665a44371d17ff09254d4b5c388a9a310d3d085fc0 |
| 格式 | JPEG，1376×768，保留原始字节 |
| 下游 | 同 run 的 Sol 输出准确引用上述 node/media，进入 video_ready_gate |
| 重开恢复 | 新页面再次提交相同输入返回同 run；同 scene 仍只有 1 个 Flow 请求 |
| 原厂生成请求 | 本地任务观察窗口为 0；只有素材上传、审核和建节点 |

## 失败与修复，没有抹去中途人工介入

1. 第一尝试 `15358154-6063-437a-8a8b-edc0843ced91` 在调用 Flow 前被校验挡住：场景 API 自动添加画风前缀。通过显式 `image_prompt` 保留模型实际提示词，补反例测试；该失败尝试仍为 needs-inspection，没有生成媒体。
2. 上表任务真实生成后返回 JPEG，而初版只接受 PNG。它停止在收集环节；补齐 JPEG 头部／尺寸校验和浏览器 MIME 类型，不转码。修复部署后明确执行一次“只读重检已完成媒体”，恢复原 run、原 request、原产物，未重发生成。
3. 恢复后的下载、上传、审核、建节点、字节回读和 Sol 续行均由适配器自动完成。不能把本次描述为从第一次启动就零人工干预；一次格式修复恢复可在 inspections 中核对。

## 测试与验收

- Python：109 项通过，覆盖固定文字配置、生成前路由、同输入去重、未知写入停止、错误回执、原厂／跨账号切换禁止、JPEG/PNG、只读恢复、同 run 续行及旧作业回归。
- Node：14 项通过，覆盖节点／genId／文件路径／状态／字节身份反例及既有回填逻辑。
- `scripts/verify_seko_local_run.py` 从真实状态、两次 CLI 输出、页面窗口、重开状态、Flow 原站模型标识、实际 Flow 请求与场景记录核对，输出 `pass_local_image_tracer`。
- 目视新图：空茶馆、雨窗、蓝伞、右侧白茶杯、灰色石板路均可见；没有人物或文字。原站画布可见同一图。
- 真实证据反例：把完成状态改成仅回填、篡改媒体 hash、替换文字模型，验收器均拒绝。第一方文件 diff 检查通过；公开 Skill 原文的 7 处空白格式按来源原样保留，以保持来源哈希。
- 既有云端 gate 检查器及反例测试一并保留，仍要求真实服务器恢复，不能用本地通过标志冒充云端通过。
- pytest 不在已有运行环境中；未安装，未声称跑过完整 pytest 套件。上述相关标准库测试、Node 测试和真实链已完成。

脱敏验收：`docs/benchmarks/workflow-boundaries/local-tracer-acceptance-20261015.json`。原始运行记录位于现有 FlowKit 的 `output/seko-local-workflow/jobs/<run>/`；页面／图片／截图／网络证据位于工程 `output/seko-local-plan-20261015/`。

## 实际边界

页面适配器通过现有浏览器开发通道载入，刷新后需要重新载入适配器；本地任务身份和结果可恢复，未完成扩展自动常驻部署。原常驻桥仍存在旧模块失配，截图中的旧桥报错不代表这条独立本地路径失败。后端已更新到现有本机服务并保存更新前备份，未安装软件。

依赖 Seko 登录、上传存储、审核和画布；没有把整站变为离线软件。私有 Skill 比较、整条视频流程、自动成片、固定声音与口型均尚未验收。后六卡未启动；下一步先按本地执行归属修订 01-04-02。
