# Review Summary：popup-solution ARIS refinement

**Problem**：移动弹窗的屏幕可见消息没有完整暴露给屏幕阅读器可读的结构化表示
**Initial Approach**：结构化 UI + 视觉兜底，并进一步做 Actionability-Gap-Gated Recovery
**Date**：2026-09-01
**Rounds**：1 / 5
**Final Score**：7.6 / 10
**Final Verdict**：REVISE
**Review independence**：same-family provisional；external Claude disclosure rejected

## Problem Anchor

- Bottom-line：让屏幕阅读器用户能知道普通移动弹窗是否存在、表达了什么和有哪些关键事实。
- Must-solve bottleneck：结构树缺失、合并、过滤、异构、宿主文本污染和树—图矛盾。
- Non-goals：统一解决、自动点击、CAPTCHA/风控绕过、从弱变化推断完整 Recovery。
- Success：真实公开 benchmark + group-disjoint、等预算实验；MG-PU 主比较通过预注册门。

## Round-by-Round Resolution Log

| Round | Main concerns | Simplified / corrected | Solved? | Remaining risk |
|---|---|---|---|---|
| 0（历史） | 把 dismissal、Context、focus 和 task Recovery 混入 V1；只有 schema fixtures | 用户将 V1 降为 message judgment | yes for scope | empirical data 仍为 0 |
| 1 | PPT 第 14 页未成为硬边界；“first”过宽；benchmark 与方法贡献不聚焦 | 固化五级回证表；dominant=PMAB，supporting=MG-PU；加入 source/license/data tiers 和 kill criteria | partial | no real item/baseline/result；cross-family unavailable |

## Overall Evolution

- 从“统一消除弹窗”纠正为“承认不可观测性并测量 popup message gap”。
- 从完整 Recovery 缩到 V1 action-free popup-message judgment，不再把消息判断命名为恢复成功。
- 从 255 字段 contract 明确过渡到必须产生 empirical item 的 benchmark。
- 从泛化的结构＋视觉融合缩到一个 message sufficiency gate。
- 把 PPT 第 14 页的弱／强回证分层写成不可违反的 claim boundary。
- 查新后取消宽泛的“第一个提出移动无障碍问题”。

## Score

| Axis | Score |
|---|---:|
| Problem Fidelity | 9.5 |
| Method Specificity | 8.0 |
| Contribution Quality | 7.0 |
| Frontier Leverage | 7.0 |
| Feasibility | 6.0 |
| Validation Focus | 8.5 |
| Venue Readiness | 6.5 |
| Weighted Overall | 7.6 |

CALIBRATION：none。

## Final Status

- Anchor：preserved and corrected。
- Focus：tight enough for execution。
- Modernity：appropriately uses frozen VLM/OCR; no forced new backbone。
- Strongest part：hard observability boundary + popup-specific evidence contract + equal-budget selective fusion test。
- Weakest part：当前没有 empirical dataset item 和 comparison result。
- Cross-family：not accepted；failed external disclosure attempt is locally traced。

## Next Gate

完成 PopSweeper source integrity/join audit，随后解锁 30-item annotation pilot。该 gate 之前不冻结正式 N、不声称公开 benchmark 已完成，也不运行会被误读为论文主结果的 synthetic-only leaderboard。
