# LW-02：Toonflow 原生生图接入现有 Flow

前置：LW-01 在 Toonflow 仓库 de90ac6 通过。D-18 取消Sol接入；文字配置暂空。D-19 仅允许项目锁定依赖安装。

1. FlowKit 增加独立 Toonflow 本地任务与场景绑定：任务UUID、输入hash、Flow工程/视频/场景/request ID持久化。生成只通过现有batch队列。固定BELUGA、横屏；不支持参考图的初版入口明确拒绝，不能静默忽略。
2. 绑定场景派发前校验输入和模型；走strict_route，禁止Flow内部切换及worker自动重试。未知外部写入进入needs-inspection，重复调用不得生成第二次。
3. Toonflow增加flowKit供应商，复用原生画布与generateMedia落盘流程。工作区+输入内容形成稳定任务ID；原生素材库仍接收本地文件。模型标注Nano Banana 2.1，文字配置不调用Sol。
4. 测试：输入身份冲突、模型错误、横竖屏错配、未知回执不重发、重复请求、失败不兜底；前后端类型与构建。
5. 实测：关闭所有Seko标签，Toonflow原生节点发起一张全新Flow图片，Flow请求完成，图片显示并保存同一画布、素材hash一致，刷新不重复生成。仅文字未配置的媒体路径验收；不得标记剧本全自动通过。
6. 真实验收后提交该卡相关源码；随后才实现Omni视频卡。

## 实测验收通过（2026-10-15）
- 原生节点发起真实BELUGA；1376×768 JPEG，866954字节。Flow、工作区文件SHA256完全一致。
- 关闭Seko（0标签），刷新仍保留同节点；同任务重复POST及刷新后仅1次生成、retry_count=0。
- 28项unittest通过；前后端类型检查和构建通过。额外pytest回归套件因现有环境缺依赖未运行，未越权安装。
- 证据：docs/benchmarks/workflow-boundaries/toonflow-image-acceptance-20261015.json。
