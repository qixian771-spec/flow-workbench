# 本机 Flow 生图

LW-02 复用原生图片节点、媒体生成接口和工作区素材写入。供应商为 `flowKit`，唯一生图模型为 Nano Banana 2.1（BELUGA）。当前仅支持横屏原生尺寸文生图；参考图、蒙版与其他尺寸明确报错。

工作区真实路径和规范化媒体输入形成稳定任务ID；同输入重复提交只读取原任务，不再次扣费生成。若确需另一次生成，应显式修改提示词。FlowKit 日志保存任务、输入hash、工程、视频、场景、生成请求和最终素材ID；未知提交停在 needs-inspection，不能自动重发。任务状态保存在现有 FlowKit 的 output/toonflow-jobs，画布与媒体在本仓库 data/workspaces。

默认安装的媒体供应商仅为 flowKit。本机启动时 LW-01 自动复制的其他供应商已移到 data/providerBackups/lw01；未删除源码或其他用户配置。文字设置保持 customProviders=[]，没有接入或调用 GPT-6.1-Sol，未完成剧本自动拆镜。

真实验收见 flowImageAcceptance.json：原生节点生成并回填一张新图，刷新与重复提交后同一Flow请求、同一SHA256。Seko标签0。截图位于相邻 FlowKit 仓库 output/toonflow-local-20261015/flow-image-backfilled.png。
