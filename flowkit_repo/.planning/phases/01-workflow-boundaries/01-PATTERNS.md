# Phase 1: 成熟工作流与接管边界 - Pattern Map

**Mapped:** 2026-10-15 · **Files analyzed:** 8 · **Analogs found:** 6 / 8

仅覆盖报告、证据契约、离线验收器与回归 fixture，不修改生产桥。NEW 是建议路径，尚未创建；CONTEXT/RESEARCH 未锁定新文件名，规划器可合并报告。

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `docs/THREE-PLATFORM-LIVE-RESULTS.md`（MODIFY） | model（报告） | transform | 同文件 | exact |
| `docs/SEKO-WORKFLOW-BOUNDARIES.md`（NEW） | model（候选/步骤/接入报告） | transform | 三家报告 | role-match |
| `docs/SEKO-BUILD-COMPATIBILITY.md`（NEW） | model（版本报告） | transform | 三家报告 | role-match |
| `docs/benchmarks/workflow-boundaries/evidence.json`（NEW） | model | file-I/O | 无 | none |
| `docs/benchmarks/workflow-boundaries/current-build.json`（NEW） | model | file-I/O | 无 | none |
| `scripts/workflow_evidence_probe.py`（NEW） | utility | file-I/O、transform | `scripts/platform_probe.py`、`scripts/seko_probe.py` | exact |
| `tests/test_workflow_evidence_probe.py`（NEW） | test | transform | `tests/test_platform_probe.py`、`tests/test_seko_probe.py` | role-match |
| `tests/fixtures/workflow-evidence/valid.json`（NEW） | model（fixture） | file-I/O | `tests/test_platform_probe.py` 内联 fixture | partial |

## Pattern Assignments

### 三份报告

**Analog:** `docs/THREE-PLATFORM-LIVE-RESULTS.md`。第 3 行原文：`日期：2026-10-13（本机）。以下只比较已完成的接入实测，不把官网介绍计入通过。` 第 13 行明确“失败，既有分镜仍可引用旧视频”；24–28 行采用“平台 | 本机成片 | 审计记录”。
- 三家报告沿用 9–20 行能力矩阵，增加历史/当前与证据 ID，保留旧引用反例。
- 工作流报告沿用 24–28 行来源关联；新增官方/玩家候选、实际人工步骤、选择依据、逐步输入输出/执行方/请求发起方/前置控制证据和接入项 ID。缺玩家来源明确阻断。
- 版本报告沿用日期/范围先行；分别列旧标签、归档、执行当次资源，关联状态码、内容类型、哈希、实际/所需导出。历史 404 不冒充当前事实。

### 离线验收器

**Analog:** `scripts/platform_probe.py`。3–7 行使用 argparse、hashlib、json、Path 标准库。95–105 行摘录：
```python
def index_unique(items):
    result = {}
    for item in items:
        if not item["id"] or item["id"] in result:
            raise ValueError("missing or duplicate ID")
        result[item["id"]] = item
    return result

def check(report, name, passed, **details):
    report.append({"check": name, "passed": bool(passed), **details})
```
复用于证据/候选/步骤/接入项唯一 ID 和闭合引用；空证据集合显式失败，不让 all([]) 通过。140–145 行 hashlib.sha256() 分块读取可复用。222–226 行错误模式为 `report = {"passed": False, "error": str(exc)}`，随后 JSON 写入并 `return 0 if report["passed"] else 1`；新脚本不用 subprocess，移除相应异常类型。

**范围限制 analog:** `scripts/seko_probe.py:65–67` 使用 limits，原文包括 `'Audio flags are not a volume, voice or lip-sync verification'`。新报告明确离线契约通过不证明当前站点或生成前控制；“证据有效”与“可接入/阻断”分开输出，充分取证的阻断不能误计可接入。

### 回归测试与 fixture

**Analog:** `tests/test_platform_probe.py:1–8` 使用 unittest、importlib.util 加载脚本；13–23 行合法基线加 deepcopy。32–35 行原文：
```python
    def test_canvas_only_change_fails(self):
        self.after = copy.deepcopy(self.before)
        self.assertFalse(self.checks()["affected_clips_updated"])
        self.assertFalse(self.checks()["no_stale_source_reference"])
```
新测试逐一破坏证据链接、文件字节、采样时效、前/后置控制类型、玩家来源、步骤关联、唯一 ID、非空集合，另测充分证据阻断。按 `tests/test_seko_probe.py:23–26` 断言具体命名失败项。

fixture 复用 `tests/test_seko_probe.py:13–18` 的 `json.loads((path / filename).read_text())` 本地加载方式。新 fixture 显式标记合成数据，不充当真实在线证据；哈希测试用临时目录已知字节。无需新增依赖。

## Shared Patterns

- 唯一 ID、命名检查、结构化错误及非零退出码复用上述 analog；未知/缺字段不能默认成功或补造证据。
- `scripts/seko_probe.py:32–48` 分开检查节点、镜头引用、时序和完成状态；新检查同样区分发现、静态、运行、当前构建与前置控制。
- 离线工具无鉴权入口，不复制生产 auth；在线取证保持现有登录和只读边界，不生成/上传/写时间线，报告脱敏。
- 单测证明契约行为；人工核验证明来源/控制点。当前构建需执行当次观察，模拟测试不能替代。

## No Analog Found

| File | Role / Data Flow | Reason |
|---|---|---|
| `docs/benchmarks/workflow-boundaries/evidence.json`（NEW） | model / file-I/O | 没有候选来源、证据层级、逐步控制与接入项完整关联契约；按 RESEARCH 定义字段/枚举/引用 |
| `docs/benchmarks/workflow-boundaries/current-build.json`（NEW） | model / file-I/O | 没有旧缓存/归档/当前采样及导出比较的完整契约；明确时间基准，私有归档缺失显式报告 |

## Metadata

**搜索范围：** scripts、tests、docs 的 5 个指定 analog，均完整读取并用 git ls-files 确认跟踪，无运行镜像。已读根 AGENTS 与阶段 CONTEXT/RESEARCH；项目 .codex/skills/、.agents/skills/ 未发现技能文件。仅写本文件，无安装、在线请求、测试或提交。覆盖：exact 2、role-match 3、partial 1、none 2。
