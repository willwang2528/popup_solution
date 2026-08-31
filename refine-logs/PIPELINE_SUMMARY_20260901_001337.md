# Pipeline Summary：移动弹窗消息可访问性

**Problem**：屏幕可见 popup message 与平台暴露给屏幕阅读器的结构化表示之间存在不可观测缺口
**Final Method Thesis**：MG-PU 只在可审计的结构消息 sufficiency contract 失败时调用视觉 ROI，并以 VPMA–coverage–cost 检验选择性融合
**Final Verdict**：REVISE
**Date**：2026-09-01
**Review**：same-family provisional；external Claude disclosure rejected

## Final Deliverables

- Evidence anchor：`sources/PPT_SLIDE_14_EVIDENCE.md`
- Novelty：`refine-logs/NOVELTY_CHECK.md`
- Proposal：`refine-logs/FINAL_PROPOSAL.md`
- Review summary：`refine-logs/REVIEW_SUMMARY.md`
- Experiment plan：`refine-logs/EXPERIMENT_PLAN.md`
- Experiment tracker：`refine-logs/EXPERIMENT_TRACKER.md`

## Contribution Snapshot

- Dominant：Popup Message Accessibility Benchmark（PMAB）measurement/benchmark。
- Supporting：Message-Gap-Gated Popup Understanding（MG-PU）。
- Explicitly rejected：统一弹窗解决器、自动授权／关闭、用弱画面变化证明任务恢复、新 backbone 堆叠。

## Must-Prove Claims

1. 真实移动 popup 中存在可复现、可标注且非单一 App 驱动的 message observability gap。
2. 在同 frozen observation 和同预算下，MG-PU 相对 strongest deployable baseline 提升 VPMA，并且不靠 hallucination 或 abstention。

## First Runs to Launch

1. `SRC-002`：完成 PopSweeper archive 下载。
2. `SRC-003`：核验 byte size 与 MD5。
3. `SRC-004`：archive path-traversal／bomb scan 与 inventory。
4. `SRC-005`：解析 label schema，抽查 image-label alignment。
5. `SRC-006`：测量 PopSweeper ↔ RICO ID/hierarchy join rate。

## Main Risks

- **Prior art**：Screen Recognition 已覆盖 pixel→accessibility metadata；只保留 popup-message-specific delta。
- **Circular dataset**：sampling/split 在 method prediction 前冻结。
- **No device**：P1 public-derived pilot 不能替代 P2 controlled 和 P3 iOS。
- **License**：CC-BY source 与 RICO restricted redistribution 分开。
- **External review**：无授权前保持 provisional。

## Next Action

等待当前 source download 进入 terminal state；随后立即执行 checksum、safe inventory 和 join audit。只有 M0 通过，才解锁 30-item annotation pilot。
