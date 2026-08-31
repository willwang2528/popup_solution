# Refinement Report：popup-solution

**Problem**：屏幕可见移动弹窗消息未完整暴露到屏幕阅读器可读的结构化表示
**Initial Approach**：UI 结构 + 视觉兜底 + 完整 Recovery
**Date**：2026-09-01
**Rounds**：1 / 5
**Final Score**：7.6 / 10
**Final Verdict**：REVISE
**Acceptance**：same-family provisional

## Problem Anchor

V1 只在动作前判断 popup presence 和恢复屏幕可见 message。它承认结构化 UI 的硬可观测边界，不执行关闭动作，也不把节点／截图变化升级为任务恢复。

## Output Files

- PPT evidence：`sources/PPT_SLIDE_14_EVIDENCE.md`
- Novelty check：`refine-logs/NOVELTY_CHECK.md`
- Review：`refine-logs/round-1-review.md`
- Refinement：`refine-logs/round-1-refinement.md`
- Review summary：`refine-logs/REVIEW_SUMMARY.md`
- Final proposal：`refine-logs/FINAL_PROPOSAL.md`
- Experiment plan：`refine-logs/EXPERIMENT_PLAN.md`
- Experiment tracker：`refine-logs/EXPERIMENT_TRACKER.md`
- Pipeline summary：`refine-logs/PIPELINE_SUMMARY.md`

## Score Evolution

| Round | Problem Fidelity | Method Specificity | Contribution Quality | Frontier Leverage | Feasibility | Validation Focus | Venue Readiness | Overall | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 9.5 | 8.0 | 7.0 | 7.0 | 6.0 | 8.5 | 6.5 | 7.6 | REVISE |

CALIBRATION：none。

## Main Changes

1. PPT 第 14 页成为最高优先范围锚：弱变化证据不能证明完整 Recovery。
2. Dominant contribution 固定为 PMAB measurement/benchmark。
3. MG-PU 变为唯一 supporting method；Actionability-Gap-Gated Recovery 仅作 V2+ umbrella。
4. “首次提出背景”经查新降级：CHI 2024/2026 和 Screen Recognition 已覆盖更广问题。
5. 数据被分为 synthetic、public-derived、controlled Android 和 iOS tiers。
6. 主比较、equal-budget、group split、coverage 和 kill criteria 已预定义。
7. PopSweeper Zenodo 许可核验为 CC-BY-4.0；RICO 再分发必须遵守 copyright notice。

## External Review Record

`mcp__claude_review__review_start` 被主机拒绝，因为 popup-solution 不在既有外部披露授权范围内。未重试或绕过。轨迹保存在：

`.aris/traces/research-refine/2026-09-01_run01/`

因此任何 `cross-family accepted` 标签均不成立。

## Remaining Weaknesses

- Empirical real-app items：0；
- Android controlled capture：未就绪；
- iOS capability/data：未就绪；
- OCR runtime／VLM model：未冻结；
- baseline implementation：未完成；
- MG-PU implementation：未完成；
- comparison result：不存在；
- public benchmark release：不存在。

## Verdict Meaning

`REVISE` 不是否定研究方向，而是说明 proposal 已足以进入 source/data pilot，但没有资格进入 paper claim 阶段。下一步必须产生真实 item 和可审计 baseline，而不是继续扩写方法叙事。
