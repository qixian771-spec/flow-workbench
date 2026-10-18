---
phase: 01-workflow-boundaries
plan: "01"
subsystem: testing
tags: [evidence, provenance, workflow-boundaries, unittest]
requires: []
provides:
  - 真实归档到矩阵声明的离线 tracer
  - 三家九入口范围的历史与当前证据矩阵
  - 哈希、声明范围、证据等级与矩阵引用检查
affects: [01-02, 01-03, BASE-01]
tech-stack:
  added: []
  patterns: [standard-library-only, named-checks, bounded-evidence-claims]
key-files:
  created:
    - scripts/workflow_evidence_probe.py
    - tests/test_workflow_evidence_probe.py
    - docs/benchmarks/workflow-boundaries/evidence.json
  modified:
    - docs/THREE-PLATFORM-LIVE-RESULTS.md
key-decisions:
  - "supported_capabilities 固定人工已复核范围，拒绝把节点成功扩大成完整流程成功。"
  - "历史日期保留本机日精度；本次读取源码不升级为当前运行证据。"
requirements-completed: [BASE-01]
coverage:
  - id: BASELINE-CLI
    description: 证据合同和三家矩阵闭合检查
    requirement: BASE-01
    verification:
      - kind: unit
        ref: tests/test_workflow_evidence_probe.py
        status: pass
      - kind: integration
        ref: python3 scripts/workflow_evidence_probe.py --evidence docs/benchmarks/workflow-boundaries/evidence.json --stage matrix
        status: pass
    human_judgment: false
  - id: BASELINE-SOURCES
    description: 历史观察、声明范围与当前未知的来源语义验收
    requirement: BASE-01
    verification:
      - kind: manual_procedural
        ref: 本文件两卡来源验收记录（执行器阅读）
        status: pass
    human_judgment: true
    rationale: 哈希不能证明语义或当前运行，阶段独立验收仍需判断范围。
actuals:
  tokens: 13671
  tasks: 2
  commits: 2
commits: 2
plan_head_before: b006a3d83d0ffae0ea11c34bde28ef396c16e577
plan_head_after: 13ca81931ce738d1c1deb21901d2a89169d293b9
duration: 10min
completed: 2026-10-15
status: complete
---

# Phase 1 Plan 01: 三家能力证据基线 Summary

**15 条真实来源关联 15 条有界声明，覆盖三家九入口，并拒绝静态冒充运行、历史冒充当前和旧引用反例消失。**

## Performance

- Started: 2026-10-15T10:54:05Z
- Completed: 2026-10-15T11:03:51Z（任务实现完成；随后 metadata 更新）
- Tasks: 2/2；四个计划交付文件及本 SUMMARY。
- tokens 为两个任务提交实现 diff 的 54,684 字符 /4 向上取整；不是模型消耗数。提交计数为上述 before..after 实测 2，不包含后续 metadata 提交。

## Task Commits

1. `574f589` — feat(01-01): trace archived workflow evidence to bounded claims
2. `13ca819` — feat(01-01): audit three-platform capability matrix and counterexamples

两卡均先完成测试与执行器来源验收再提交。元数据通过单独 docs 提交保存，最终 SHA 由执行返回记录。

## 01-01-01 测试与验收

- RED：`python3 -m unittest tests.test_workflow_evidence_probe -v`，退出 1，17 tests / 17 assertion failures；目标 `test_real_file_and_matching_claim_pass` 对未实现 scaffold 的 contract_valid=False 断言失败，不是加载或环境错误。原始输出在本机 `output/workflow-boundaries-01-01/task1-red.json`；`gsd-tools check tdd-red-evidence` 返回 `RED_EVIDENCE_OK`。用户要求测试、验收后才提交，未提交 RED。
- GREEN：同命令，新增 CLI 退出码/只读检查后共 18 tests，退出 0。验证 0/1/2 退出码、缺档、哈希、唯一 ID、范围、历史/当前、静态冒充运行、文件/采样二选一。
- 实际 CLI：`python3 scripts/workflow_evidence_probe.py --evidence docs/benchmarks/workflow-boundaries/evidence.json --stage tracer`，退出 0，contract_valid=true，20 named checks，1 evidence / 1 claim，feasibility=unassessed。
- 来源验收：执行器逐字段打开 `node-update-probe.json`，node.genFileUrl 为 B（5c3835…），shots[1].shotVideoUrl 为 A（252fcf…）；与 `SEKO-FLOW-LIVE-RESULT.md` 的 2026-10-13 过程对应。SHA-256 `e12038d2b90b68d66f3c012328b201776204bfaea8a9ab120785c782566d59e2`。矩阵 `seko-canvas-stale-shot` → `ev-seko-stale-shot` → 真实脱敏归档闭合。未放入合成 fixture，未复制签名查询串或凭据。
- 证据边界：仅证明历史自动传播反例；不证明当前线上、生成前控制、整条工作流或可行性。
- 提交：`574f589`。tracer feedback gate 在扩展前重跑 18 tests 和真实 tracer，均退出 0，随后进入 01-01-02。

## 01-01-02 测试与验收

- RED：`python3 -m unittest tests.test_workflow_evidence_probe.WorkflowEvidenceProbeTests.test_matrix_all_nine_scopes_pass -v`，退出 1，1 个目标断言失败（matrix stage 尚不支持）；`gsd-tools check tdd-red-evidence` 返回 `RED_EVIDENCE_OK`。原始记录 `output/workflow-boundaries-01-01/task2-red.json`。没有提交 RED。
- GREEN：`python3 -m unittest tests.test_workflow_evidence_probe tests.test_platform_probe tests.test_seko_probe -v`，退出 0，52 tests；其中新增检查器 25 tests。原始记录 `output/workflow-boundaries-01-01/task2-green.json`。
- 实际 CLI：`python3 scripts/workflow_evidence_probe.py --evidence docs/benchmarks/workflow-boundaries/evidence.json --stage matrix`，退出 0；194 个命名检查，15 evidence /15 claims，9/9 平台入口覆盖，feasibility=unassessed。
- 来源验收：逐项打开 15 条引用的文件；核对 LibTV acceptance、replacement/stale audit，OiiOii render-audit（15/16、旧 sourceReferences），Seko 旧镜头快照、14 项 REPLACE、24 项原生按钮审计及页面桥定向转交代码。每行的时间、平台、入口、状态、限制与来源对应；所有原文件 SHA-256 复算一致。
- 静态验收：真实归档读到 7 文件/7 解析/0 失败、672 findings、443 节点/687 边及 chat 超预算限制；编辑器 gen-video/gen-image 与 Agent plan/next-ep 字符串存在；JSON 与旧 TOON 已分开。只读本机归档没有作为运行成功证据。私有归档不随 Git 分发，缺失明确失败。
- 威胁检查：提交内容无 Cookie、Bearer 凭据、签名查询串或完整第三方源码；新增工具仅本地读取，路径不能逃逸根目录。未安装，未生成，未改提供方或生产桥，未宣称新剧本/整集完成。
- 计划总回归：`python3 -m unittest tests.test_seko_probe tests.test_seko_flow_job tests.test_platform_probe -v` 退出 0，33 tests；`node --test tests/test_seko_generation_hook.cjs tests/test_seko_resident_page.cjs tests/test_seko_native_backfill.cjs` 退出 0，16 pass/0 fail/0 skip。原始记录 `output/workflow-boundaries-01-01/regression.json`。
- 来源语义验收由执行器人工阅读完成，不冒充用户本人验收。Phase 1 独立验收仍由后续阶段验证执行；BASE-02/03/04 未完成。

## Decisions Made

- 只实现固定 tracer/matrix stage，后续 candidates/selection/steps/integration_items/handoff 按计划留空，由 01-02/03 填写；未知 stage 不允许通过，没有 final 认证。
- 实际路由模型不在本卡推测或改动；开发代理继承当前会话，resolver 未返回具体模型 ID。

## Deviations from Plan

**[Rule 2 - Missing critical validation] 为声明范围增加 supported_capabilities。** 自由文字 capability 无法机器判断是否扩大；该小字段记录来源已人工核对的范围，检查器逐项匹配平台/入口/能力。测试 test_broader_capability_rejected 验证，包含于 `574f589`。它不声称能自动判定来源语义。

用户覆盖通用 TDD 提交顺序：RED 实际运行和分类器证据保留于本机 output，仅 GREEN+来源验收后原子提交。按执行补充保留用户授权的 main 分支，无 worktree、不推送；每次提交检查根目录和分支。

状态处理器已推进计数，但遗留了 READY TO EXECUTE/零已完成计划的旧正文；同步修正状态文本为 01-01 完成、后两计划和阶段验收待完成。全里程碑 0 个完成阶段的进度保持不变。SDK 生成的 state.json 与偏差 WINDOWS 记录一并保存；该已解决校验偏差标为 fixed。

## Issues Encountered / Evidence Limits

- 历史快照未保存精确 UTC 采样时刻时只使用有据的本机日期；不修改 audit.started_at 使旧证据变新。
- 私有 REA 归档真实可读，但不随 Git 分发；别的机器缺档将明确失败。
- source-only 的当前本地桥范围无法证明线上兼容或服务端生成前控制。blocked=contract_unproven，不等于技术不可能。
- 仅创建标准库离线检查器，没有新增网络、鉴权或生产 schema 面；无新凭据，未运行第三方归档代码。
- 未新增 TODO、跳过测试、未跑的计划 verify 或阻碍本计划的 stub。后续 stage 空集合是计划明确分工，不通过本次检查冒充 final。

## Next Phase Readiness

01-02 可扩展当前构建与官方/玩家候选证据，并核查用户要求的真实模型路由。01-03 才建立逐步契约、生成前控制与真实接入清单。当前仅 BASE-01 完成，不能标 Phase 1 或整部漫剧完成。

## Self-Check: PASSED

5 个交付/记录文件存在；两条任务提交均为 HEAD 祖先；未发现新增占位实现。真实 CLI、源码/报告哈希和所有指定测试已记录通过。工作区无本计划遗留生成文件；output 日志按现有规则忽略，其他人的 config、执行补充及 extension.crx/extension.pem 保留。
