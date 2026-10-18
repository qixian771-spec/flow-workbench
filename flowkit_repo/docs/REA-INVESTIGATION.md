# REA 接入与首轮调查

后续已完成 Seko 两次原生生成接管、Flow 新视频生成、自动上传回填与原站出片，见 [接管实测与验收](SEKO-NATIVE-FLOW-TASKS.md)。本文保留首轮静态调查时的结论与限制。

## 方案与范围

使用官方 [morluto/rea](https://github.com/morluto/rea) 的 `rea-agents@6.4.0`，临时 CLI 分析本机已保存的 OiiOii 客户端与 Seko 前端代码。用户本轮建议使用 REA；此次仅增加 REA 的 npm 缓存，不进行全局安装，不运行 setup，不更改 Codex MCP 配置，不安装原生反编译引擎。

目标是发现后续生成接管、素材回填和时间线更新的可验证调用关系。静态发现不等于平台已接入 Flow，也不改变此前三家实测验收结论。

## 任务卡

| 卡片 | 执行与验收标准 | 状态 |
|---|---|---|
| REA-01 | 核对官方包、版本与本机 Node；运行 CLI 帮助 | 通过 |
| REA-02 | 分析已有 OiiOii 文件，记录模块/IPC 证据及限制 | 完成；图覆盖部分 |
| REA-03 | 分析已有 Seko JS，核对实际生成、上传、回填入口 | 完成；核心两文件图通过 |
| REA-04 | 复核原文件，保存可重现证据与结论，验收并提交 | 证据校验通过 |

## 环境核对

- npm 注册表：版本 6.4.0，仓库 `git+https://github.com/morluto/rea.git`。
- npm integrity：`sha512-Vj1zWfSlna5bphGoaoI/TcVBuYvze9u+OyPC3Shz8YkBqaCTqB4COnnRoX7XDwMpwI24ZlFEel2yEj0k8LTWEQ==`。
- 现有 Node 24.15.0 满足包要求；Flow 服务检查通过，扩展已连接。
- 原始输出保留在被 Git 忽略的 output 下；不会提交第三方完整代码、登录配置或带签名的素材链接。

## 首轮真实结果

| 分析范围 | 结果 | 限制 |
|---|---|---|
| Seko 已保存的 10 个 JS 文件 | 全部解析；3,005 条 findings | 大文件触发 worker 内存及父结果预算限制，整体图 partial |
| Seko canvas.js、shot.js 两文件 | 177 条 findings，图 complete；上传导出追踪命中 1 个种子、157 节点、181 边 | complete 仅限输入文件；导入的其他文件、运行时分支未覆盖 |
| OiiOii 已提取应用 987 个文件 | 983 个 JS 解析，166 个模块；17 个桥接 API、109 个暴露成员 | 全量图 partial；动态通道及资源限制影响关系图 |
| OiiOii 4 个核心文件 | 无资源限制；目标通道追踪命中，260 节点、310 边 | 动态 IPC 注册仍未自动配对；图 partial |

四次分析的 parse_failures 均为 0。解析成功不表示语义关系完整。保存的完整证据与追踪文件均在 `output/rea-test-20261013/`；提交的 [摘要](benchmarks/rea-20261013/summary.json) 包含证据 ID、输出 SHA-256、统计、覆盖限制。

### Seko 可继续验证的入口

REA 对 `shot.js:r` 的导出关系追踪成功；人工对照原文件，`r` 对应 `V`，调用 POST `guodong-studio/v1/shots/{id}/video/upload`。同一文件还包含：

- `h → D`：POST `.../{id}/gen-video`。
- `z → G`：PUT `.../{id}/lip-sync`。
- `b → v`：POST `.../{id}/lip-sync-multi`。

这些是客户端已有函数及路由的静态证据。本轮没有调用生成或口型接口，未证明它们允许外部音频、具备所需模型、或能直接替换为 Flow。接下来的可执行任务是捕获原生生成按钮的真实参数和状态更新契约，再实现显式的 Flow 接管；不得把接口名称当作完成证明。

### OiiOii 的重要反例

全量图追踪 `desktop:agent-mcp-call` 得到 no-match；只分析核心文件后同一追踪种子命中。原文件复核：

- `src/content-preload.cjs:73`：`oiioiiDesktopMcp.callTool` 调用该通道。
- `src/main.mjs:784`：动作表含 connect/call/read-resource/write-resource/disconnect，790 行用模板字符串注册通道。
- `src/local-tools/host.mjs:29`：连接配置取 `oiioii-local-files`。

因此“自定义 MCP 配置可保存/测试”不等于 Agent 已能任意调用自定义 Flow MCP；动态注册使 REA 无法完整自动配对。此发现加强了原有边界结论，没有解决时间线旧 sourceReferences，也没有完成原生生成接管。

## 复用方法与测试验收

固定版本，首次临时运行（仅 npm 缓存及依赖，不全局安装）：

```sh
npm exec --yes --ignore-scripts --package=rea-agents@6.4.0 -- rea --help
```

后续使用同一已缓存版本：

```sh
npm exec --offline --yes --ignore-scripts --package=rea-agents@6.4.0 -- rea analyze-javascript-application '<绝对路径>' --format json
npm exec --offline --yes --ignore-scripts --package=rea-agents@6.4.0 -- rea trace-application-feature '<追踪输入 JSON 路径>' --format json
```

追踪输入结构为 `{ "application": <完整 Evidence 对象>, "seed": { "kind": "channel", "value": "desktop:agent-mcp-call" } }`；Seko 使用 `kind=module,value=shot.js:r`。

优化：先做有限范围目录扫描，识别入口后单独分析相关文件；资源受限时明确标记未覆盖范围。证据图的“未命中”必须与原文件核对。Seko 保存文件曾重命名，且未下载所有依赖，不能用此目录宣称已还原完整站点导入图。后续采样保留原始资源文件名与相对路径。

验收完成：CLI 能运行；4 份分析、3 份追踪均生成可解析 JSON；核心 Seko 种子命中；OiiOii 小范围复查纠正全量图未命中；证据摘要校验通过。此次未修改平台页面、客户端代码、生成模型或已有桥接逻辑，三家实测结论维持 [原报告](THREE-PLATFORM-LIVE-RESULTS.md)。LibTV 尚未经过 REA 分析。
