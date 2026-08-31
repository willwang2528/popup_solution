# Research Proposal：面向视障人士的移动弹窗消息判断

> 当前版本：v1 message-only scope，2026-08-31
> 状态：`provisional`
> 审阅：same-family local validation；未获得本课题外部 Claude 披露授权，不能标为 cross-family accepted
> 历史：[`round-0-initial-proposal.md`](./round-0-initial-proposal.md) 的 Recovery 主线已被用户最新范围修订取代

## 1. Problem

依赖 TalkBack、VoiceOver 等屏幕阅读器的视障人士可能遇到结构化可访问性表示不能完整呈现的移动弹窗。问题不只是“树为空”，还包括消息节点被合并、标题／正文／关键事实缺失、平台字段异构、宿主文本混入、树—图不同步和跨通道矛盾。

v1 的可证伪问题是：

> 在普通移动弹窗的动作前观察中，结构优先、message-gap-gated 的视觉补全，能否比 structure-only、vision-only 和 always-on fusion 更准确地判断弹窗存在性并生成语义正确、无关键编造的可读消息？

本阶段不自动关闭弹窗。Dismissal、屏幕阅读器焦点、原页面和原任务恢复属于进阶研究。

## 2. Scope

- 人群：使用屏幕阅读器的盲人和低视力移动用户；
- 平台：Android、iOS；移动 Web／WebView 分组扩展；
- 对象：普通、获授权观察的弹窗；
- 排除：CAPTCHA、风控、认证、支付、权限安全控制、人工审核等；
- 产出：popup/no-popup/abstain、消息、关键事实、置信度与证据；
- 动作策略：`no_action`。

真实用户体验是动机，不是 v1 技术实验可直接证明的结果。

## 3. Method

方法名：**Message-Gap-Gated Popup Understanding（MG-PU）**。

```text
frozen screenshot + platform structured representation
→ popup scope detection
→ structured message reconstruction
→ message sufficiency gate
   ├─ sufficient: compose message
   ├─ missing/merged/contradictory: popup-ROI visual completion
   └─ unresolved: abstain
→ evidence alignment + critical-fact guard
→ popup presence + message + confidence
```

门控检查 popup scope、标题／正文覆盖、关键事实、阅读顺序、owner/context、树—图同步和通道矛盾；不能只判断空树。视觉只补消息，不定位或执行动作。

关键机制详见 [`../method/METHOD_SPEC.md`](../method/METHOD_SPEC.md)。

## 4. Dataset

一个 item 是一个动作前、只读的 popup-message observation。来源字段并集保持：14 篇论文 90 个字段＋我方既有方法 165 个字段＝255 条 crosswalk；v1 `message_judgment` 是单独计数的协议扩展。

最小 gold：

- `popup_present_gt`；
- `blocking_gt`；
- `message_text_gt`；
- `critical_facts_gt`；
- message observability 与 evidence。

最小 prediction：presence、message、critical facts、confidence、abstain、source observation、model version、latency 与 evidence。

v1 `action_attempts=[]`，D/C/T/VTR 均为 `null/not_applicable`。数据 schema 详见 [`../DATASET_SCHEMA.md`](../DATASET_SCHEMA.md)。

## 5. Metric

对弹窗正样本：

```text
VPMA = presence_correct
       AND message_semantically_correct
       AND NOT critical_hallucination
```

对无弹窗负样本，`VPMA=presence_correct`；abstain 的 VPMA 为 null。主报告 VPMA 与 coverage，同时报告 Presence Macro-F1、正类 recall、false-notification rate、message semantics、Exact Match、Character F1、critical-information recall、critical-hallucination rate、视觉调用率和延迟。

## 6. Experiments

### E1 Message-gap census

在 Android/iOS action-free pilot 中比较 screenshot 可见消息与结构化暴露，按 missing、merged、ambiguous、contradictory、stale、owner mismatch、visual-only 分组报告覆盖。

### E2 Paired main experiment

每个 frozen observation 配对运行 structure-only、OCR-only／vision-only、always-on fusion、MG-PU 和 human-readable-message oracle。方法不得看到 gold，也不得执行点击。比较 VPMA、coverage、hallucination 与成本。

### E3 Ablations

去视觉、始终视觉、空树 gate、去 owner/context、去同步检查、去矛盾检查、去关键事实约束。

### E4 Generalization

按 App、template、SDK/CMP、UI framework、OS family 与 near duplicate 分组切分；报告 Android/iOS、语言、owner、popup kind、exposure tier 和 message complexity。

`N` 在 pilot 后依据配对效应、cluster size、目标置信区间和功效分析冻结。

## 7. Claims and kill criteria

待验证贡献：

1. accessibility message gap 的问题形式化；
2. 带原始平台字段、结构／视觉证据和消息标注的跨平台数据 contract；
3. message-gap gating 在等预算下的性能／成本权衡。

不能预先宣称：第一个提出、第一个公开数据集、指标已经更好、真实体验已经改善。

Kill criteria：

- structure-only 与 MG-PU 的 VPMA 无实质差异且成本更低；
- always-on 在等预算下稳定优于 gate；
- 分组隔离后增益消失；
- 增益依赖更高 hallucination 或过度 abstain；
- 真实 message gap 过少，结果只存在于人工腐蚀；
- iOS 无目标设备数据却试图声称跨平台；
- 无目标用户研究却试图声称体验改善。

## 8. Current evidence status

- 文献采集：14/14 篇记录完成，来源证据等级保留；
- Schema：`1.1.0-provisional`；
- Source-field union：90＋165＝255；
- v1 fixture：positive/no-popup/abstain 三条 synthetic，均不可训练／不可进入经验指标；
- Empirical Android/iOS data：0；
- Cross-family review：未执行，当前仅 provisional。

## 9. Next gate

先运行小规模 Android/iOS 只读 capability pilot，验证截图／结构化表示同步、message gold 可标注性、真实 gap 比例和 baseline 方差。该 gate 通过后再冻结正式 N、split、模型／prompt、门控阈值、标注预算与公开发布方案。
