# Flow Workbench (本地 AI 漫剧全自动生成工作台)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Runtime](https://img.shields.io/badge/Runtime-Bun%20%7C%20Python%203.11%2B-green.svg)]()
[![Model](https://img.shields.io/badge/Models-Nano%20Banana%202.1%20%7C%20Omni%20Flash%20%7C%20Gemini-orange.svg)]()

基于 **Toonflow** 可视化漫剧工作台与 **FlowKit** 协议层桥接引擎打造的本地 AI 漫剧自动化制作平台。

本项目已真实跑通端到端生产闭环：  
**输入剧本 → 本地中转 Gemini 拆镜与生词 → Google Flow (Nano Banana 2.1) 生图 → Flow (Omni 8s 720p) 视频生成 → Gemini 首帧/抽帧质量审查 → 回填 Toonflow 节点画布 → 本机 FFmpeg 幂等合成导出成片**。

---

## 📌 架构全景

```text
               ┌────────────────────────────────────────────────────────┐
               │         Toonflow 本地漫剧工作台 (端口 3000)              │
               │   • Vue 3 + Fastify + Bun 运行环境                      │
               │   • 剧本拆镜编排 / 原生画布节点回填 / 自动成片入口        │
               └──────────────┬──────────────────────────┬──────────────┘
                              │                          │
        1. 拆镜与提示词生成    │                          │ 3. 逐镜审查与质量重做
                              ▼                          ▼
               ┌────────────────────────┐      ┌────────────────────────┐
               │ 本地文字中转站 (Gemini) │      │  本机 FFmpeg 剪辑流水线 │
               │  (OpenAI 兼容 REST)     │      │   无损拼接 / 幂等导出成片 │
               └────────────────────────┘      └────────────────────────┘
                              ▲
                              │ 2. 生图与生视频任务提交
                              ▼
               ┌────────────────────────────────────────────────────────┐
               │          FlowKit 协议层代理服务 (端口 8100 / WS 9222)   │
               │   • FastAPI 调度与状态持久化                             │
               │   • 真实消耗 Google AI 订阅每月 1,000 Flow 积分          │
               └──────────────────────────────┬─────────────────────────┘
                                              │ WebSocket RPC
                                              ▼
               ┌────────────────────────────────────────────────────────┐
               │           Google Chrome + FlowKit 扩展 (MV3)            │
               │   • 静默驻留 flow.google.com 页面底层                    │
               │   • 计算 reCAPTCHA Enterprise + CSRF 凭据               │
               │   • 规避 DOM 点击脆弱性，直接发送底层 batchexecute RPC   │
               └────────────────────────────────────────────────────────┘
```

---

## 目录结构

```text
flow-workbench/
├── toonflow/               # 漫剧工作台主系统（Vue3 前端 + Fastify 服务端）
│   ├── apps/web/           # Web 端界面（包含 /#/workspace 漫剧画布与自动成片面板）
│   ├── apps/server/        # 后端路由与流式任务编排
│   └── packages/providers/ # 多模态生成适配器（FlowKit、Gemini 等）
├── flowkit_repo/           # Google Flow 逆向与协议代理服务
│   ├── agent/              # FastAPI 后端服务 (REST 8100 + WS 9222)
│   ├── extension/          # Chrome 扩展（Manifest V3 桥接器）
│   └── scripts/            # 自动化脚本与测试用例
├── handoffReport.md        # ⭐️ 团队交接与开发设计报告（后续接手开发必读）
├── launch_bridge.py        # 浏览器桥接启动脚本
└── README.md               # 本项目说明文档
```

---

## ⚙️ 环境依赖

* **系统**：macOS (推荐 Apple Silicon M 系列)
* **运行环境**：
  * [Bun](https://bun.sh/) (用于 Toonflow 快速开发与编译)
  * Node.js 20+
  * Python 3.11+
  * [FFmpeg](https://ffmpeg.org/) (确保在系统 PATH 中，用于视频抽帧与合成)
* **浏览器与账号**：
  * Google Chrome
  * 已订阅并登录拥有月度积分的 **Google Flow** 账号 (`flow.google.com`)

---

## 🚀 快速启动指南

### 1. 配置并启动 FlowKit 后端
```bash
# 1.1 进入目录并创建 Python 虚拟环境
cd flowkit_repo
python3 -m venv .venv
source .venv/bin/activate

# 1.2 安装依赖
pip install -r requirements.txt

# 1.3 启动本地 FlowKit 服务
python -m agent.main
# 服务启动后将监听：API http://127.0.0.1:8100，WS ws://127.0.0.1:9222
```

### 2. 在 Chrome 中加载 FlowKit 扩展
1. 打开 Chrome，访问 `chrome://extensions/`。
2. 开启右上角 **“开发者模式” (Developer mode)**。
3. 点击 **“加载已解压的扩展程序” (Load unpacked)**，选择目录：
   `flow-workbench/flowkit_repo/extension`。
4. 打开 [flow.google.com](https://flow.google.com) 并登录账号，标签页保持在后台即可。
5. 访问 `http://127.0.0.1:8100/health`，若 `extension_connected: true` 说明桥接成功。

### 3. 启动 Toonflow 漫剧工作台
```bash
cd ../toonflow

# 3.1 安装项目依赖（使用 Bun）
bun install

# 3.2 启动本地开发服务
NODE_ENV=production bun --no-install apps/server/src/index.ts
```

### 4. 访问与使用
打开浏览器访问：  
👉 **`http://127.0.0.1:3000/#/workspace`**

1. 在左侧菜单点击 **“自动成片”** 入口。
2. 配置你的本地文字模型路由（默认支持本地 OpenAI-compatible 协议，推荐 Gemini-3.8-Flash）。
3. 粘贴剧本内容，设定镜头数（2~8 镜）。
4. 点击执行，系统将自动拆镜、依次向 FlowKit 请求生图与生视频、调用 Gemini 进行抽帧合规审核，并最终合并导出为标准 16:9 720p 视频成片。

---

## 📖 后续开发与交接说明 (For Developers)

在继续下一阶段特性开发前，**务必详细阅读 [handoffReport.md](./handoffReport.md)**。

当前已完成与验收边界：
- [x] 静音双镜头全自动拆镜、生图、生视频、抽帧审核、导出全链路（已跑通）。
- [x] 任务幂等恢复与持久化快照。
- [x] Flow 原生 Nano Banana 2.1 与 Omni Flash (8s) 路由绑定。

后续待推进里程碑（开发卡）：
1. **角色/道具跨镜一致性**：接入 Flow 参考图（Reference Images）实体机制，解决多镜头下主体外观漂移。
2. **对白、固定音色与正面说话口型对齐**：规划 TTS 接口与对口型模型管线。
3. **异常中断原子化恢复**：完善多进程与长周期任务异常熔断保护。
4. **单集 3~5 分钟文戏漫剧整体验收**。

---

## 🔒 安全与隐私

* 仓库不包含任何私有 API Key、Cookie 或 Token。
* 敏感文件（包括 `data/settings.json`、`extension.pem`、本地 SQLite 数据库与测试素材）已在 `.gitignore` 中彻底排除。
* 本地凭据通过本地加密快照存储，请勿将含真实密钥的配置文件推送到公共分支。

---

## 📄 开源许可

本项目代码遵循 [MIT License](./LICENSE)。所集成的子模块版权分别归其原作者所有。
