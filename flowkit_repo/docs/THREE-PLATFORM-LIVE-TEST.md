# LibTV / OiiOii / Seko 本机实测记录

日期：2026-10-13。以下保留首轮认证阻塞记录。用户随后完成登录：LibTV CLI 已认证；OiiOii 已跑通真实 Flow 媒体上传、Agent 自动剪辑和原站 16 秒成片导出，详见 [OiiOii 实测结果](OIIOII-FLOW-LIVE-RESULT.md)。R02 状态更新为 IN_PROGRESS，三站同剧本比较尚未完成，不宣布平台胜出。

后续更新：LibTV 已跑通“读取节点提示词 → 自有 Flow 新视频生成 → 同节点回填 → 刷新剪辑引用 → CLI 原站合成 → 下载验证”，详见 [LibTV 实测结果](LIBTV-FLOW-LIVE-RESULT.md)。这属于外部调度，不是原站按钮拦截。生成样片仍为风景技术素材，完整统一剧本仅保存，未制作；Seko 的后续实测也已完成，见 [Seko 实测](SEKO-FLOW-LIVE-RESULT.md)。最新并列结论见 [三家真实结果](THREE-PLATFORM-LIVE-RESULTS.md)。

> 下方是首次登录前的历史记录，保留失败事实；不代表当前认证或接入状态。当前状态以上方最新结果链接为准。

## 首轮历史任务卡与验收

| 卡片 | 工作 | 实际结果 | 验收 |
| --- | --- | --- | --- |
| R02-A | 固定统一剧本、镜头与比较口径 | `benchmarks/three-platform-script.txt`，虚构文戏《雨停之前》，16:9、36 秒、双人六镜头 | 测试输入已准备；固定声音样本及该剧本 Flow 素材尚未生成 |
| R02-B | 查找官方工具并运行 | LibTV CLI 1.1.3、OiiOii CLI 0.1.8 已安装并运行；OiiOii Desktop 0.4.1 已安装启动 | 工具启动通过，不代表云端工程权限通过 |
| R02-C | 获得可操作的测试工程 | LibTV 账号检查返回 401；OiiOii 未认证；Seko 创作入口显示登录框 | 阻塞，三站均未创建测试工程 |
| R02-D | 接管生成并回填 Flow 媒体 | OiiOii CLI 的真实上传命令返回 AUTH_REQUIRED，未上传 | 接管未测、回填未通过认证前置条件 |
| R02-E | 持久保存、自动剪辑与导出 | 无可用测试工程 | 未测 |

## 真实操作证据

### LibTV

- 在官网新建画布触发登录框，可选微信、手机、团队邮箱等入口，未登录。
- 官方插件页提供 Codex marketplace、Remote MCP 和 CLI。下载其 CLI skill 包，执行官方安装脚本，二进制安装于 `~/.libtv/libtv`，版本 1.1.3；安装器向 `~/.zshrc` 添加 PATH。
- `libtv account list` 返回 `接口错误 [401]: 未登录`。
- `libtv project list` 返回空列表不能证明认证成功，未将它计为工程操作通过。
- 启动 `libtv login web` 后浏览器仍是未登录首页，没有获得账号会话。
- 随包文档明确：`upload` 可上传本地文件并创建媒体节点；节点支持连线；`video-clip` 支持时间线、裁剪、音量及合成任务。这是比只有官网介绍更具体的集成线索，**尚未执行到远端成功**。
- `node create` 与 `--run` 分离有利于探索只建工程再填 Flow 素材，但不证明已能接管原站 Agent 的生成任务。

### OiiOii

- 官网工作台未登录；官方 npm 包 `@oiioii/cli@0.1.8` 已安装，安装时禁用 npm lifecycle scripts。
- `oiioii auth status --json` 返回 `authenticated: false`、`credential_source: null`。
- `oiioii inspect capabilities --json` 能列出能力描述；它不代表账号已登录，也不代表生成执行成功。
- 使用此前真实 Flow 生成的 `output/live-20261013/omni-1-1-flash.mp4` 执行 `oiioii upload resource ... --name Flow-verified-import-probe.mp4 --json`，实际返回 `AUTH_REQUIRED`，没有发生上传。该视频是 8 秒风景素材，只用于验证传输入口，不能计为本次文戏样片。
- CLI 有工作区、画布节点和媒体上传命令；CLI 浏览器授权页说明会创建新的 API Key，当前停在“登录后继续”。未创建凭据。
- 官方 Desktop 0.4.1 下载至本任务 output，签名为 Developer ID Application: ho gi (59P47Y24YD)，系统检查结果 `accepted / Notarized Developer ID`。
- 已安装到 `~/Applications/OiiOii.app`，启动后真实界面只有“在浏览器中登录”，未看到可跳过登录的本地创作入口。官网更新记录中的本地素材、自定义 ComfyUI 能力尚未进入实测。

### Seko

- 实际打开官网创作画布 `/infinite-canvas`，显示手机号、验证码和企业登录入口。
- 聚焦检索未找到可核验的官方 CLI 或桌面下载入口；不能据此断言不存在。
- 没有登录会话，未创建工程，接管、回填、自动导出均未测。

## 接入判断

| 平台 | 已验证的入口 | 后续可验证路线 | 仍需实证 |
| --- | --- | --- | --- |
| LibTV | CLI 可启动，账号接口明确要求认证 | 建画布 → 上传真实 Flow 文件 → 媒体节点连线 → video-clip 合成 | 生成拦截、节点持久性、素材版本、真实渲染、自动继续 |
| OiiOii | CLI 可启动；桌面端可启动；上传命令明确要求认证 | 工作区与画布节点 → 媒体上传；桌面端另查自定义 ComfyUI | 音视频绑定、完整导出、是否能使用自定义生成后端 |
| Seko | 实际创作入口可打开 | 登录工程后检查素材/生成/导出链路 | 当前三个核心指标全部未知 |

没有把 CLI 存在记成“Flow 接管成功”，没有绕过账号、伪造成功响应或把本地拼片当成原站自动出片。此轮没有提交新的收费生成任务；无法据此估算整集成本。

## 本机证据位置

`output/platform-test-20261013/`（忽略于 Git，保留在本机）：

- `libtv-account-check.txt`：LibTV 401 结果。
- `oiioii-auth-status.json`：OiiOii 认证状态。
- `oiioii-upload-probe.json`：真实上传命令的 AUTH_REQUIRED 结果。
- `oiioii-desktop-login.png`：已安装桌面端的登录界面。
- `seko-login.jpg`：Seko 创作入口的登录界面。
- `tools/`：官方安装包与 LibTV 随包文档。安装包不提交仓库。

## 官方来源

- [LibTV 官方插件与 CLI](https://www.liblib.tv/plugin)
- [LibTV 官方 Codex 集成仓库](https://github.com/liblib-ai/marketplace)
- [OiiOii 官方 CLI 包](https://www.npmjs.com/package/@oiioii/cli)
- [OiiOii 官方桌面端](https://www.oiioii.ai/desktop)
- [Seko 创作入口](https://seko.sensetime.com/infinite-canvas)

安装与认证入口检查已记录；R02 成片比较、M0 接管闭环及整体用户验收均未通过。提交该记录仅保存本次检查点。
