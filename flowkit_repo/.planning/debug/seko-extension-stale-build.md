---
status: investigating
trigger: 用户要求查清旧文件加载原因，不再反复要求重载；修复后真实验收再提交
---

# Seko 扩展磁盘版本与运行版本不一致

## Current Focus

- hypothesis: Chrome 仍登记并执行上次提交的内容脚本；新版磁盘清单尚未进入运行注册。
- next_action: 解决 Chrome 扩展注册更新未生效的原因。当前不能自动操作扩展管理或以其他通道代重载，不能用临时注入替代常驻验收。
- unresolved: 用户报告已点击重载，但实际 manifest 不变；具体为何该动作没有替换运行注册尚未确定，不能推断用户没有操作。

## Evidence

- Chrome 主进程为 /Applications/Google Chrome.app/Contents/MacOS/Google Chrome --no-startup-window，没有自定义 user-data-dir。
- 当前连接浏览器配置名“用”，对应本机 Default 配置。
- 只读 Secure Preferences 中 ID hpnjecanenblgehkiiopnidgjjgakiop 的 path 为 /Users/niuniu/Desktop/flow cli/flowkit_repo/extension；真实路径相同，不是符号链接；各 profile 下无该 ID 的打包安装副本。
- 从 Seko 页已运行的 Flow Kit 隔离上下文只读调用 chrome.runtime.getManifest()，运行清单第一组 js 仅 seko_page.js；磁盘对应组为 seko_local_bundle.js、seko_page.js。
- 两份清单 version 都是 0.5.2。不能用该版本或服务 connected 字段判断部署成功。
- Debugger.getScriptSource 读取的 seko_page.js 与 git HEAD:extension/seko_page.js 字节完全相同（SHA256 e89676a5fa3b01827c2e4f5d660d17c4fd96de2c3556f677710bda5e9dae4f40）。磁盘更新文件 SHA256 9de6bfe13502470b42480ce95a01c0ac767a285747a7028efed498dac3c2357c。
- 差异精确为本地任务过滤与 __flowkitSekoLocal.ownsPage() 判断；新 bundle 完全未出现在脚本记录中。
- 当前 bundle 的构建一致性及 JS 语法检查通过，不能把尚未被加载的 bundle 解释为运行后异常。
- 真实刷新与新标签都复现旧入口，排除仅原标签残留。断线恢复还未验收。
- 原始证据：output/seko-local-resident-20261015/loaded-build.json、loaded-build-diff.json、actual-loaded-entry.js、reload-second-check.json。

## Eliminated

- 仅旧网页残留：全新标签亦复现。
- 修改到链接目标外或另一个安装包：当前配置路径与真实路径一致，未找到该 ID 打包副本。
- 新入口已运行但业务初始化失败：运行清单没有登记它，实际脚本记录也没有它。
- 新旧公开版本不同：二者都是0.5.2，需要文件指纹而非版本号区分。

## Changes and verification

新增只读构建核验器，对照运行 manifest、扩展 ID、脚本 URL 与三个运行脚本 SHA256。刷新／新标签／重连的正式验收必须逐次满足该检查；相同版本号、旧文件、缺 bundle、其他扩展、临时注入均不得通过。

7项新增测试与3项任务查找回归测试通过。实际旧构建输入被核验器明确拒绝，退出码1是本次负向验收的预期结果。

未安装，未切模型，未新增生成，未代重载、重注册或临时注入业务代码。只是修复了部署验收的漏检；运行注册未修好，仍4/7，不提交。

## 加载链及日志续查

- Chrome 版本155.0.8059.41；PID81057自本地2026-10-12 21:31:55运行，尚未完整退出。
- FlowKit日志11:22:29本机服务启动，11:22:33扩展连接；11:46:50断开，11:46:51重连，此后截至调查没有新的连接切换。WS握手仅发送版本和支持域名，既不报告manifest内容，也不记录重载原因，不能把该次重连当作新版部署证明。
- Chrome没有持久chrome_debug.log；最近一小时统一日志按扩展ID、manifest.json、Failed to load extension过滤无命中。没有历史按钮事件或完整扩展加载错误日志，不能确认“点击未触发”还是“未记录的重载失败”。
- 只读检查Extension Scripts的完整WAL记录（该目录没有SST表）没有Flow Kit项；源码也没有registerContentScripts/updateContentScripts调用。没有证据支持动态注册覆盖本卡静态脚本。Extension State中Flow Kit记录是alarms；未修改数据库或缓存。
- popup.js只有请求日志读取、日志详情展开、sidePanel.open。截图中的弹窗不提供reload操作；刷新此弹窗不等同于重载扩展。这是代码事实，不是对用户操作的推断。
- Chromium官方 installed_loader.cc 的 ShouldReloadExtensionManifest 对未打包扩展返回true，启动 LoadAllExtensions 链会重读清单再登记。源码依据：https://chromium.googlesource.com/chromium/src/+/refs/heads/main/chrome/browser/extensions/installed_loader.cc 。因此无需删除、安装、清缓存或改权限，完整退出Chrome再打开可以触发这条明确的加载路径；效果仍需实测确认，不能预先宣布修好。
- 原始记录：loading-chain-investigation.json、connection-lifecycle.json、chrome-load-errors.log（同证据目录）。

## 一次手动动作与后续验收

保存网页未提交内容后，用Chrome菜单“退出Google Chrome”（Cmd+Q；若提示则按住）完整退出，确认Dock运行圆点消失，再重新打开Chrome的“用”配置。无需重新安装或反复点重载。当前工具策略禁止代重载及替代通道完成同一操作，故不由代理重启Chrome。

用户完成后首先核对新主进程与runtime manifest、三份实际脚本指纹。构建身份一致后才按原卡执行刷新、新标签、服务断开再恢复；检查同任务状态、成片SHA与生成账本不变。三项及测试全部通过才提交。本次调查不构成运行态修复或验收。


## 用户报告完整退出重开后的自动复核 2026-10-15T19:08:05.603581+00:00

用户已明确授权电脑自动化，不缺授权。真实进程检查仍为PID81057、启动时间2026-10-12 21:31:55；运行连接计数仍2次、断开1次。对现有Seko页再次正常刷新后读取实际runtime manifest，仅seko_page.js；实际文件SHA仍e89676a5fa3b01827c2e4f5d660d17c4fd96de2c3556f677710bda5e9dae4f40，新bundle没有加载，无截断。构建校验器再次明确拒绝，退出码1。用电脑自动化只读检查Chrome当前窗口为Flow Kit请求记录弹窗，没有观察到退出确认提示。无法确认用户动作发生在何处，但已确认当前被测浏览器进程未更换。

未代退出、杀进程、重注册或发送reload命令，以遵守此前工具禁止替代通道完成重载的限制。未安装、未调用生成、未启动断线验收、未提交。后续必须先观察到实际的新注册/脚本指纹，再恢复真实验收。证据post-restart-report-build.json与post-restart-report-diff.json。


## 原生窗口与自动化实例交叉对应（最新）

通过原生Chrome关闭请求日志弹窗后看到窗口title含jack (用)；打开个人资料菜单确认jack • 用，与Default配置一致。原生窗口新建并打开已知Seko成片URL，随后在当前browser4的user.openTabs中出现新标签216965899，证明原生窗口与自动化连接是同一实例。该标签实际Flow Kit ID仍hpnjecanenblgehkiiopnidgjjgakiop，清单仍仅旧seko_page.js；配置中路径为当前仓库extension。已留存instance-profile.png、instance-correlation.json。

已展开这个准确窗口的Chrome菜单，退出项文本为“退出Google Chrome”、原生action为terminate:，未执行。让用户直接点击该菜单项并重新打开“用”，可避免快捷键/关闭弹窗混淆；无需再找其他窗口或配置。菜单截图接口不可用，保留已拍的个人资料截图及AX证据，没有采用替代截屏。用户动作后代理负责构建核对、刷新、新标签、断线恢复和通过后的提交。当前仍4/7，未验收未提交。
