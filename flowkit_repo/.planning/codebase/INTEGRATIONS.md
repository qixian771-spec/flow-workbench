# 外部集成与边界

| 集成 | 入口/证据 | 当前边界 |
| --- | --- | --- |
| Flow | `agent/sdk/services/flow_provider.py`、`agent/services/omni_flash.py` | 实际模型与能力需按项目核对 |
| Seko | `agent/api/seko.py`、`extension/seko_page.js` | 限定首帧视频；编辑器和 Skill 未全面接管 |
| LibTV | `scripts/libtv_flow_bridge.py`、`docs/LIBTV-FLOW-LIVE-RESULT.md` | CLI 调度/回填/合成；原生 Agent 未替换 |
| OiiOii | `docs/OIIOII-FLOW-LIVE-RESULT.md` | 上传/合成已有实物；旧来源元数据问题仍在 |
| REA | `docs/REA-INVESTIGATION.md` | 静态发现用于定位；不能代替运行验证 |

Seko 登录保留在浏览器；本机桥认证与第三方登录不同。规划与审计不得包含密钥、会话数据、签名素材 URL 或第三方完整源码。
