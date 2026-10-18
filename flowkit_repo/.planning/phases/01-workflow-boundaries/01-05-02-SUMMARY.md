---
phase: 01-workflow-boundaries
plan: "05"
card: "02"
status: complete
scope: local-two-distinct-shot-native-export
requirements-completed: []
coverage:
  - deliverable: Two distinct Flow videos edited and exported in one local run
    human_judgment: false
    verification:
      - kind: real-audit
        ref: docs/benchmarks/workflow-boundaries/local-multishot-acceptance-20261015.json
        status: pass
      - kind: tests
        ref: tests/test_seko_local_multishot.py
        status: pass
  - deliverable: Native editor two-shot playback
    human_judgment: false
    verification:
      - kind: browser-evidence
        ref: output/seko-local-multishot-20261015/playback.json
        status: pass
---
# 第四卡：同一本地任务的双镜衔接与原生自动出片

用户明确要求先按本地方案修订下一卡，再执行多镜衔接与出片。01-05-02 已按 01-05-02-LOCAL-TASKS.md 完成 A–E；缺口卡 4/7。原官方／创作者同稿比较仍未完成，没有以本卡替代。其余三卡尚未开始，阶段和里程碑保持进行中。

## 真实执行与模型路由

同 run `eedacf2c-49c2-4b6f-9f02-652d60834930` 新增 multishot 子步骤。一次页面启动自动完成第二镜策划→新生成→回填→独立双镜工程→分别裁剪→一次原生导出→同任务继续。17:20:32Z 启动，17:22:23Z 完成媒体核验，约111秒；人工没有搬运素材、排序、裁剪或点击导出。

|任务|固定实际路由|本卡调用|
|---|---|---|
|第二镜分时动作提示|Codex CLI GPT-6.1-Sol / low；只返回结构化文本|1次|
|首帧|第一卡已验收 Flow BELUGA 图片 b587a425-a9dc-4759-921b-6c3eadba7e55|新增生图0次|
|第一镜 A|第二卡已验收 Omni 原始视频；缓慢推镜|新增生成0次|
|第二镜 B|Flow Omni abra_i2v_8s；首帧模式、8s、720p、横屏；向右横移|新生成1次，retry_count=0|
|剪辑和导出|Seko 原生服务，model=null|两镜、两次trim、一次render|
|身份、顺序、状态继续|本地确定性执行器|同一持久任务|
|成片检查|已有 ffprobe/ffmpeg，解码、SSIM、抽帧与黑帧检测|只分析，不合成|

两镜共用已验收首帧，但 B 是独立新生成视频，operation、media、文件 hash 均与 A 不同。A保留1–5秒，B保留2–6秒，按A→B硬切，输出8.041667秒；画面由推进切到横移，茶馆、伞、杯、窗外雨景继续。没有把同一段视频重复播放当成两镜。

## 实际身份与产物

|对象|值|
|---|---|
|第一镜 media|f74d2a35-cac2-42f7-b1fe-c7473a140f78|
|第二镜 scene|4e42bb08-aef7-46af-821f-4d960fb2665d|
|第二镜 request|0aaca3eb-7a0a-49e4-b30e-e367e3e76432|
|第二镜 operation|d3f1319c-ed91-4db3-9c67-a4096f067db1|
|第二镜 media|083509f3-7e75-4da0-bd14-8db969e10fe6|
|第二镜原站回填 node|2110783295183978497|
|独立双镜 canvas|2110783301014462465|
|独立双镜 story|2110783303661068290|
|按顺序的 shots|2110783303677845506 → 2110783303707205633|
|原生 render|2110783307835875329|
|第二镜原片 SHA256|cb7f641586e70f801688c06ee23c86f202d4fdaa71107fbcbc4aa12d80eeeeeb|
|成片 SHA256|189fa7e130e884ad9c21ec2be58dcf1ecfb91291e8531ac9110b145a2dd16fd1|
|成片规格|4,217,308 bytes；1280×720；8.041667秒|
|续行关口|multishot_export_complete；同run的multishot-export-manifest.json|

成片：`/Users/niuniu/Library/Application Support/FlowKit/output/seko-local-workflow/jobs/eedacf2c-49c2-4b6f-9f02-652d60834930/seko-multishot-export.mp4`。保留Seko原生水印。

## 测试、真实验收和记录

- 144项相关Python测试与24项Node测试全部通过。新增覆盖：错误输入／首帧／模型、第二操作重复、同输入重复启动、未知提交不重发、顺序反转、重复素材、错误节点／裁剪／故事、两次裁剪未齐不导出、非本任务render、不合格第二段不出片、同run清单绑定和完成后只读恢复。
- 真实验收器 `scripts/verify_seko_local_multishot.py` 返回 `pass_local_two_shot_native_export`；检查原生前后快照、网络窗口、模型回执、原始文件hash、逐段SSIM日志、同run清单、重开状态和原站播放证据。
- 第一段中心SSIM：offset0=0.944966、offset1=0.987746、offset2=0.945123。第二段：0.863662、0.986222、0.868326。两段均为一帧编码偏移，采用事先规定的0–2帧范围；未修改0.95通过门槛。
- 对实际成片使用错误来源进行反证：重复第一镜的匹配值0.490967；倒序来源0.491062，均低于门槛。验收器另拒绝未完成导出、错剪辑执行方、重复media、反转输出清单四例。
- 实际切点93–100帧抽帧可见A→B切换，没有黑帧；整片黑帧检测无区间。Seko原生编辑器完整播放至00:08 / 00:08。两镜各4秒，实际服务返回顺序、裁剪范围和文件路径都与计划相符。
- 网络业务写入：第二镜上传一次；视频内容检测一次；原画布回填node一次；创建独立canvas一次；独立canvas加第二node一次；两节点一次加入时间线；分别trim两次；render一次。没有厂家生图／生视频调用。已有站点统计请求单独排除，不算业务写入。
- 重开新页面载入适配器并启动同run，未触发上传、模型生成或原生写入；持久结果完全一致。原工程四条历史对白镜头与第三卡的单镜剪辑工程均保持不变。
- 旧扩展曾显示已失效构建模块错误；本卡明确使用已核对的当前模块与现有扩展通信通道，真实链路完成。没有安装、换提供方或切换生成模型；没有触发旧云端等待工具。

机器报告：`docs/benchmarks/workflow-boundaries/local-multishot-acceptance-20261015.json`。测试日志、原生快照、完整网络窗口、播放截图、切点抽帧及反例位于 `output/seko-local-multishot-20261015/`；服务更新前备份位于 `output/seko-local-multishot-deploy-20261015/`。当前修改和真实运行使用同一适配器版本。

## 边界与偏差

本卡验证两镜自动剪辑和导出，尚不是3–5分钟整集、完整剧情、固定音色／精确台词／口型验收；也未验证任意镜头数和溶解转场。原始音轨保留，不宣称完全静音。原视频A正常复用为剪辑输入，第二视频B是本卡真实新生成，不把复用A说成重新生成。

本地任务持久化；页面脚本仍通过已有开发通道载入，并显示状态面板及生成保护。重开需要载入适配器，常驻注入未完成。旧Seko云端任务未恢复。

没有执行中变更模型或替代成片路线。原七卡第四张的目标按用户请求事先从候选比较修订为双镜本地执行；未满足的比较需求保留。阶段总体验收未通过，本次只提交第四卡。
