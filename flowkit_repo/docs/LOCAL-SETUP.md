# 本机 Flow Kit

源码目录为 `~/Desktop/flow cli/flowkit_repo`。Chrome 已加载该目录的 `extension/`，版本 0.5.2。请保留登录的 Google Flow 标签页。

## 后台运行

macOS 用户服务：`com.niuniu.flowkit`。登录后自动启动，退出后自动重新启动。

桌面目录受 macOS 隐私权限保护，后台服务运行在 `~/Library/Application Support/FlowKit`。该目录拥有独立虚拟环境、`.env`、数据库及 `output/`；原数据库已通过 SQLite backup 复制，原文件保留。

| 项目 | 位置 |
| --- | --- |
| 生效配置 | `~/Library/Application Support/FlowKit/.env` |
| 服务配置 | `~/Library/LaunchAgents/com.niuniu.flowkit.plist` |
| 日志 | `~/Library/Logs/FlowKit/` |
| 接口 | `http://127.0.0.1:8100/docs` |
| 浏览器桥接 | `ws://127.0.0.1:9222` |

已固定当前浏览器项目「9月 12 - 13:05」，UUID 为 `a5ff6d71-9e97-4d95-bc2e-5f88702da727`。需要切换时编辑生效配置，并在无生成任务时重启服务。直接生成接口仍应明确传入 `project_id`；上游原有的空值逻辑可能新建会话项目。

查看服务：

```bash
launchctl print "gui/$(id -u)/com.niuniu.flowkit"
```

在没有运行中任务时重启（SIGINT 触发正常退出，由服务管理器重新启动）：

```bash
launchctl kill SIGINT "gui/$(id -u)/com.niuniu.flowkit"
```

停止自动运行：

```bash
launchctl bootout "gui/$(id -u)/com.niuniu.flowkit"
```

重新启用：

```bash
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.niuniu.flowkit.plist"
```

## 源码与部署

运行目录是明确部署的副本，源码修改不会自动生效。更新时先停止服务，再复制变更后的 `agent/` 或 `scripts/` 文件至运行目录，按需更新该虚拟环境依赖，保留运行目录的 `.env`、数据库和输出，再启用服务并验收。

如在终端直接运行源码，先停止后台服务以释放端口，再使用 `scripts/start-local.sh`。它要求明确配置 Python 路径和项目 UUID；配置不合法即退出。源码目录 `.env` 与后台服务配置彼此独立。

启动器强制监听本机、使用 Flow 提供方，并关闭 Flow/Muse 的媒体降级选项。

## 验收

```bash
curl --fail http://127.0.0.1:8100/health
curl --fail http://127.0.0.1:8100/api/flow/status
curl --fail http://127.0.0.1:8100/api/providers/status
```

应显示扩展已连接、版本 0.5.2、项目 UUID 已配置、`allow_degraded=false`、Flow 提供方可用。

`flow_key_present=false` 是当前网页传输方式的正常结果。`/api/flow/credits` 只返回配置的档位，不代表真实余额；不能用它验收 Google 登录或余额。
