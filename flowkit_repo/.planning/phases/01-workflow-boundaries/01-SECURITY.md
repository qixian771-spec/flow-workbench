---
phase: "01"
slug: workflow-boundaries
status: verified
threats_open: 0
asvs_level: 1
register_authored_at_plan_time: true
created: "2026-10-15"
---

# Phase 1 安全约束核验

范围仅限本轮离线证据工具、脱敏资料与只读调查；不代表生产接管成功，也不是全仓安全认证。按secure-phase的L1规则，预先编写的12条威胁均找到缓解，不额外派发深审计。4条代码审查问题经修复和反例测试复核，修复过程见REVIEW-FIX。

## Trust Boundaries

| 边界 | 穿越的数据 | 控制 |
|---|---|---|
| 第三方页面/归档到本机审计 | 不可信文案、运行摘要 | 按来源类型/时间/范围记录，不执行文案 |
| 本机到Git报告 | 脱敏字段、哈希、结论 | 无凭据、完整第三方源码或签名链接 |
| 调查到后续执行决定 | 候选、控制点、路由、完整度 | 缺证据不放行，不自动换提供方/型号 |

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|---|---|---|---|---|---|---|
| T-01-01 | Tampering | workflow_evidence_probe 与 evidence.json | high | mitigate | validate_evidence哈希/ID/根目录/引用/声明范围检查；缺失、哈希错、空集合测试 | closed |
| T-01-02 | Information Disclosure | evidence.json/报告 | high | mitigate | 5份实际报告/证据字段复核与凭据/签名URL扫描0可疑项；仅摘要，扩展pem/crx未读取未纳入 | closed |
| T-01-03 | Repudiation | 三家矩阵 | medium | mitigate | 三家九入口保留时间、来源和限制；各SUMMARY保存命令和提交 | closed |
| T-01-SC | Tampering | 包安装面 | high | mitigate | 只用Python/Node标准库；提交范围无依赖包变更，无新增安装命令或REA下载 | closed |
| T-01-04 | Tampering | current-build.json | high | mitigate | validate_build响应字段绑定；CR-02修复及真实404伪造200反例；旧缓存unknown | closed |
| T-01-05 | Elevation of Privilege | Skill 详情与 use 入口 | high | mitigate | 01-02-SUMMARY记录只读详情；未调用Skill.use；候选文案为advertised不视为观察 | closed |
| T-01-06 | Information Disclosure | 运行采样 | high | mitigate | current-build/evidence只留脱敏摘要；凭据/签名URL扫描0可疑项 | closed |
| T-01-07 | Denial of Service | 旧标签与未知任务 | medium | mitigate | 01-02-SUMMARY记录保留旧页、独立新标签采样；没有刷新未知写入现场 | closed |
| T-01-08 | Tampering | control 证据与 feasibility | high | mitigate | validate_controls拒绝后置/浏览器沉默；CR-01/04绑定真实运行/触发；未知保持未完成 | closed |
| T-01-09 | Elevation of Privilege | Agent 自动派发入口 | high | mitigate | 本轮无生产派发修改、无Skill.use/生成；未移除保护，保留服务影响仍unknown | closed |
| T-01-10 | Repudiation | integration_items/handoff | high | mitigate | validate_final接入闭合/非空必需步骤/真实阻断与缺证据分离；当前ready=false | closed |
| T-01-11 | Information Disclosure | 步骤合同与来源 | high | mitigate | 步骤/路由报告仅脱敏摘要；5份文档扫描与源字段复核；没有登录或签名素材链接 | closed |

## Accepted Risks Log

无风险接受或豁免。控制点尚未证实属于待执行取证缺口，未执行不受控生成，不能宣称该产品路径安全或可用。

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|---|---|---|---|---|
| 2026-10-15 | 12 | 12 | 0 | 父执行器，L1代码/资料复核，含CR修复测试 |

## Sign-Off

- [x] 每项有预设disposition及对应缓解证据
- [x] 无接受风险或未缓解high/critical项
- [x] threats_open=0；仅限本轮调查范围

**Approval:** verified 2026-10-15，阶段目标由独立VERIFICATION另行判断。
