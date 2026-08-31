# 面向视障人士的移动端弹窗消息研究

本目录是后续研究主入口。当前 v1 已收拢为：面向使用 TalkBack、VoiceOver 等屏幕阅读器的视障人士，判断移动端当前是否出现普通弹窗，并从“结构化 UI／可访问性表示＋必要时视觉兜底”中生成可读、无关键编造的弹窗消息。

v1 不自动点击或关闭弹窗。弹窗消失、屏幕阅读器焦点恢复、原页面恢复和被阻断任务恢复均为进阶目标。

## 当前入口

1. [`RESEARCH_RULES.md`](./RESEARCH_RULES.md)：从飞书 revision 46 原样同步的研究章程，保持原文不变。
2. [`RESEARCH_RULES_AMENDMENT_V1.md`](./RESEARCH_RULES_AMENDMENT_V1.md)：用户最新 v1 范围修订；与旧口径冲突时，以此为准。
3. [`AGENTS.md`](./AGENTS.md)：仓库级执行约束。
4. [`RESEARCH_BRIEF.md`](./RESEARCH_BRIEF.md)：v1 问题锚点、方法、实验与贡献口径。
5. [`method/METHOD_SPEC.md`](./method/METHOD_SPEC.md)：Message-Gap-Gated Popup Understanding 方法规格。
6. [`dataset-v1/README.md`](./dataset-v1/README.md)：论文字段与我方字段并集，以及 v1 message profile。
7. [`data-collection/papers.jsonl`](./data-collection/papers.jsonl)：PPT 14 篇论文的逐篇机器可读证据记录。
8. [`data-collection/FIELD_UNION.md`](./data-collection/FIELD_UNION.md)：跨 Android、iOS、移动 Web 的字段并集与证据边界。
9. [`refine-logs/FINAL_PROPOSAL.md`](./refine-logs/FINAL_PROPOSAL.md)：当前 proposal，状态为 `provisional`。
10. [`dataset-v1/VALIDATION_REPORT_V1_MESSAGE.md`](./dataset-v1/VALIDATION_REPORT_V1_MESSAGE.md)：schema、fixture、QA 与负向变异验证。
11. [`refine-logs/V1_SCOPE_LOCAL_REVIEW.md`](./refine-logs/V1_SCOPE_LOCAL_REVIEW.md)：同模型家族独立复核；状态 PASS/provisional，不是 cross-family acceptance。
12. [`sources/PPT_SLIDE_14_EVIDENCE.md`](./sources/PPT_SLIDE_14_EVIDENCE.md)：PPT 第 14 页“五级回证表”的可审计转录与 v1 分层解释。
13. [`sources/SOURCE_LEDGER.md`](./sources/SOURCE_LEDGER.md)：PopSweeper/RICO 许可、校验、实际清点、数量差异与 adapter-only 发布策略。
14. [`refine-logs/NOVELTY_CHECK.md`](./refine-logs/NOVELTY_CHECK.md)：当前查新结论与不可宣称的 broad-first 边界。
15. [`refine-logs/EXPERIMENT_PLAN.md`](./refine-logs/EXPERIMENT_PLAN.md)：claim-driven v1 实验计划、强基线、指标和停止条件。
16. [`refine-logs/EXPERIMENT_TRACKER.md`](./refine-logs/EXPERIMENT_TRACKER.md)：真实数据摄取、标注、实验与发布的当前状态。
17. [`MANIFEST.md`](./MANIFEST.md)：本轮耐久研究产物及其状态清单。

## v1 闭环

```text
移动端观察
→ 判断是否存在目标弹窗
→ 从结构化表示提取消息
→ 判断消息是否完整、无矛盾
→ 必要时只对弹窗区域做 OCR／视觉补全
→ 输出弹窗消息或安全弃答
→ 对照人工真值回证
```

v1 输出至少包含：

- 弹窗存在性；
- 弹窗可读消息；
- 标题、正文、关键金额／时间／对象／后果等关键信息；
- 使用了哪些结构化／视觉证据；
- 置信度与是否弃答。

v1 主成功值为 `VPMA`：存在性正确，且正样本消息语义正确、没有关键编造。配套报告 detection F1、critical-information recall、critical-hallucination rate、coverage／abstention、视觉调用率与延迟。

## 研究边界

- 包含：Android、iOS，以及扩展分析中的移动 Web／WebView 普通弹窗。
- 排除：CAPTCHA、风控、身份认证、PIN／生物识别、支付确认、安装／删除、权限安全控制、人工审核及其他高风险流程。
- v1 只读观察并生成消息，不执行弹窗动作。
- Appium、XCUI、UIAutomator 能读到元素，不等于 TalkBack／VoiceOver 用户一定可聚焦、可理解。
- 没有真实目标用户研究时，只报告技术消息判断性能，不宣称已改善真实用户体验。

## 进阶层

数据 schema 继续保留动作、Dismissal、`C_tech`、`C_a11y`、`T`、`VTR-tech` 与 `A-VTR`，用于后续可选研究和兼容既有论文方法。它们在 v1 中应为空、`null` 或明确标为 `advanced`，不得成为 v1 纳入条件或主指标。

原始论文 PDF、PPT 和上游 ARIS 工作区未复制进本仓库；机器可读记录保留来源定位与证据等级。后续提交以 Git 历史追踪版本。

## 当前完成度

字段并集、v1 schema、非经验 fixture、验证器、方法与实验协议已经形成；PopSweeper 归档已完成本地完整性/安全审计，并冻结 120 条 adapter-only 来源候选。90 条 numeric 候选已逐一连接到 RICO semantic JSON/PNG，但该语义层级不含 message text/content-desc；全部候选仍只有 popup presence 标签。人工消息标注、可进入指标的 pilot item、基线结果和 iOS 数据尚未形成。仓库中的 3 条 fixture 只验证数据契约，不构成论文实验数据或方法效果证据。
