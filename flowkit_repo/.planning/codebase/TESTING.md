# 测试地图

- `tests/test_seko_resident.py`：持久作业与状态。
- `tests/test_seko_resident_page.cjs`：自动启动、刷新读取、原生视频拦截。
- `tests/test_seko_flow_job.py`、`tests/test_prompt_adaptation.py`：提交/收集与转换。
- `tests/test_seko_native_backfill.cjs`、`tests/test_seko_dialogue_pipeline.cjs`：回填和对白编排。
- 页面测试使用替代模块，不证明线上哈希地址仍可用；网站升级必须实时验收。
- 静态解析、模拟测试、真实调用、完整成片分别记录，不能互相替代。
- 本次只校验规划结构、路径、需求映射、GSD 可读性；未重跑生成或业务测试。
