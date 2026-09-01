# Refinement Report：PMAB-Android V1

**Date**：2026-09-01
**Rounds**：3
**Verdict**：`PROCEED_WITH_CAUTION / pre-empirical`
**Cross-family review**：completed, accepted as review trace
**Fatal design flaws remaining**：0
**Execution readiness**：3.5/5

## Problem anchor

面向使用 TalkBack 等屏幕阅读器的视障人士，V1 测量动作前 Android 状态中目标 popup 是否存在，以及截图可见消息能否从 accessibility representation 正确重建。V1 不点击、不关闭、不恢复焦点／页面／任务，也不声称真实体验改善。

## Main refinement

1. Dominant contribution 固定为 PMAB-Android factual measurement benchmark；MG-PU 只作 allocation policy。
2. 正式输入改为真实同步 Android screenshot + accessibility representation；PopSweeper/RICO 只验证来源适配、标注与工程契约。
3. Popup scope 使用截图可观察定义，不推断持续性或 dismissibility。
4. CAPTCHA、风控、认证、支付、OS/App 权限与安全控制、人工审核显式 `out_of_scope`，不得混入 `uncertain`。
5. G1 截图事实 gold 与 G2 structure sufficiency audit 分离；G2 发现 G1 错误只能触发 versioned correction/restart。
6. 三族比较、K25/K50/K100、K50 主确认比较、cluster bootstrap、Holm/BH 控制和负／零结果出口已冻结。
7. iOS、UX、Recovery 和 broad-first claim 全部移出 V1。

## Output files

- Final proposal：`FINAL_PROPOSAL.md`
- Experiment plan：`EXPERIMENT_PLAN.md`
- Review summary：`REVIEW_SUMMARY.md`
- Independent review：`../reviews/RESEARCH_REVIEW.md`
- Experiment tracker：`EXPERIMENT_TRACKER.md`
- Pipeline state：`REFINE_STATE.json`

## Current evidence

- 255-field union contract：已生成并验证；
- PopSweeper/RICO pilot：30 items，技术媒体 QA 已通过；
- 真人 G1/G2 gold：0；
- 正式同步 Android item：0；
- 正式 empirical score：0；
- public empirical dataset：blocked；
- research docs/code：完成 clean-clone audit 后可公开。

## Verdict meaning

`PROCEED_WITH_CAUTION` 表示研究设计可以进入 feasibility/G1/G2 pilot，不表示 benchmark 或方法贡献已经成立。任何 empirical claim 必须等待真实 capture、人工 gold、gap census、matched-budget comparison 与 release gate。
