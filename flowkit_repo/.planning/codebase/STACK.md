# 技术栈（定向代码地图）

日期：2026-10-14。范围为当前接入工作相关源码，不宣称全仓审计。

- Python / FastAPI / Pydantic / aiosqlite：`requirements.txt`、`agent/main.py`、`agent/db/`。
- HTTP API 与 WebSocket 扩展桥：`agent/api/`、`agent/services/flow_client.py`；本机服务 8100，扩展连接 9222。
- Chrome MV3 JavaScript：`extension/manifest.json`、`extension/seko_page.js`、`extension/seko_content.js`、`extension/seko_background.js`。
- 已有 Node 测试、Python unittest/pytest 风格测试；依赖缺失时不能把未运行说成通过，也不新增安装。
- 已缓存 REA 6.4.0 用于离线静态分析；已有媒体处理工具用于实物验证。
- 本轮未修改业务代码、依赖或运行时部署。
