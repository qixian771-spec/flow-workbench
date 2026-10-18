# 本地网页启动与验收 LW-01

源码基线 d2e94aca7b59659ff6b4ca15f03cf134ec7f0e1d；用户授权仅安装项目锁定依赖。已有 Bun 1.3.13、Node 24.15.0、FFmpeg 8.1.1；没有安装或升级全局运行环境。

## 启动

在本仓库运行 `NODE_ENV=production bun --no-install apps/server/src/index.ts`。浏览器打开 http://127.0.0.1:3000 。服务只监听127.0.0.1。`data/settings.json` 保存配置（权限0600）；`data/workspaces/` 保存工程、画布、后续素材与产物；这些运行数据不入Git。

已按bun.lock执行frozen-lockfile、ignore-scripts，安装范围为根构建依赖、web、server及所需packages，排除桌面应用。没有运行依赖生命周期脚本。工具、节点和扩展来自本仓库源码构建。

网页与服务入口原先传递引用桌面.hutch类型，独立类型检查失败；应用元数据提取到appConfig.ts，桌面配置继续使用原类型约束，网页和服务不再引用桌面套件。独立服务和开发网页均绑定回环地址。

## 实际验收

- 前后端类型检查、前后端构建、tools/nodes/ext构建通过。
- Chrome关闭全部11个Seko标签后，在本地原生界面创建flowAcceptance工程与图片节点，填写提示词。
- 内容落盘到data/workspaces/flowAcceptance/画布1.json；刷新并选中节点后，原提示词仍显示；证据摘要见localStartupAcceptance.json。
- 本卡0次模型调用。文字接口按用户D-18要求保持空，后续可配置供应商/协议/API地址/模型。画布上游默认媒体列表尚未接Flow；不能把打开界面记为生成或自动出片通过。
- 原始截图在相邻flowkit_repo/output/toonflow-local-20261015/local-startup.png。

## 后续卡

LW-02接Flow媒体适配器与任务绑定；LW-03双镜新视频；LW-04本地合成；LW-05恢复。每卡独立测试、真实验收后提交。文字接口未配置时，自动拆镜保持暂停；人工结构化镜头只能证明媒体链路。
