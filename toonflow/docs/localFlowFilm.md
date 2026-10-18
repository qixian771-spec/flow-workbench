# 本地 Flow 双镜头出片

现有工作台：http://127.0.0.1:3000。源码、画布、素材、导出清单和成片均在本机；Flow生图与视频仍是远程生成。

固定路由：图片 Nano Banana 2.1/BELUGA；视频 Omni/abra_i2v_8s/8秒/720p/横屏；剪辑使用本机已有的 system FFmpeg。文字供应商保持未配置，可在原生设置中后续指定其他接口，不调用 GPT-6.1-Sol。

原生图片节点输出连到视频节点的输入，选择单图参考。宿主对参考列表中唯一图片计算SHA256，再匹配已完成Flow任务；这是真实参考绑定，不会把旧视频当生成回执。输入不匹配报错，未知提交不自动重发。

## 自动导出接口

POST `/api/workflows/flowExport`，使用现有应用请求头（Origin为本机工作台地址、x-toonflow-workspace为1）。请求体：

```json
{
  "directory": "工作区绝对路径",
  "taskId": "本次图片根任务ID",
  "canvas": "画布1.json",
  "shots": [
    {"nodeId":"第一视频节点ID","jobId":"对应Flow视频任务ID","sha256":"已审视频SHA256","qualityAccepted":true},
    {"nodeId":"第二视频节点ID","jobId":"对应Flow视频任务ID","sha256":"已审视频SHA256","qualityAccepted":true}
  ]
}
```

这是可重复调用的自动化接口，按清单顺序自动核对、拼接、探测和落盘；没有新增导出按钮。输出保存在当前工作区 `exports/flow<输入摘要>/film.mp4` 与 `manifest.json`，可直接用原生文档文件树打开播放。重复相同清单返回原成片，检查指纹且不再次编码；旧任务未完成或失败时暂停核查。首版只接已审8秒720p静音片段，最多40镜。

镜头质量确认字段是前置审查的回执，不是自动画面质量检测。本轮由执行者抽帧检查：第一版伞展开被淘汰，同Omni重做1次通过检查，导出仅使用修正版和左摇镜头。自动质量评分、剧本拆镜、配音、口型未验收。文字接口尚未选择，因此本次不是“给剧本全自动成片”。

真实结果见 flowImageAcceptance.json、flowVideoAcceptance.json、flowFilmAcceptance.json：1张新图、3条新视频（其中1条质量淘汰）、两个不同运镜合成16秒MP4。所有原始回执保留；测试未安装额外依赖。
