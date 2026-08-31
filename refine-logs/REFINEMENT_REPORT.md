# Refinement Report：v1 弹窗消息判断

**Problem**：无障碍场景下，移动弹窗消息在结构化可访问性表示中缺失、合并、异构或矛盾
**Current approach**：Message-Gap-Gated Popup Understanding（MG-PU）
**Date**：2026-08-31
**External review rounds**：0
**Verdict**：REVISE / PROVISIONAL

> 用户已将 v1 从完整 Recovery 明确降级为“判断并告知弹窗消息”。旧 `D ∧ C ∧ T` 主线只保留在 Git 历史、`round-0-initial-proposal.md` 和 advanced compatibility 字段中；不再是当前 v1 success。

## Problem Anchor

对依赖 TalkBack、VoiceOver 等屏幕阅读器的视障人士，当结构化 UI／可访问性树无法完整表达弹窗标题、正文或关键事实时，结构优先、视觉兜底的方法能否可靠判断弹窗存在性，生成语义正确且无关键编造的可读消息？

v1 只读观察，不执行点击。Dismissal、焦点、页面和原任务恢复是进阶层。

## 本轮收紧结果

1. 把任务从 Recovery 改为 `popup_message_judgment_v1`。
2. 把方法从 Actionability Gate 改为 Message Sufficiency Gate；视觉只补消息。
3. 一个 v1 item 止于 prediction／notification，强制 `action_attempts=[]`。
4. 主指标改为 `VPMA`，配套 presence F1、critical-information recall、critical-hallucination rate 和 coverage。
5. D、C_tech、C_a11y、T、VTR-tech、A-VTR 保留为 nullable advanced 字段，但不得进入 v1 success 或 eligibility。
6. 来源并集保持 90 个论文字段＋165 个我方字段＝255 条 crosswalk；`message_judgment` 作为单独计数的 profile extension。
7. synthetic fixture 扩展为 positive、no-popup、abstain 三条，并与经验数据隔离。
8. “第一个”“公开数据集”“指标更好”“体验改善”继续作为待验证主张，不写成事实。

## Current outputs

- 权威范围修订：[`../RESEARCH_RULES_AMENDMENT_V1.md`](../RESEARCH_RULES_AMENDMENT_V1.md)
- 当前 Brief：[`../RESEARCH_BRIEF.md`](../RESEARCH_BRIEF.md)
- 当前方法：[`../method/METHOD_SPEC.md`](../method/METHOD_SPEC.md)
- 当前 Proposal：[`FINAL_PROPOSAL.md`](./FINAL_PROPOSAL.md)
- 当前 schema：[`../dataset-v1/schema/item.schema.json`](../dataset-v1/schema/item.schema.json)
- 当前验证：[`../dataset-v1/VALIDATION_REPORT_V1_MESSAGE.md`](../dataset-v1/VALIDATION_REPORT_V1_MESSAGE.md)
- 历史 Recovery 初稿：[`round-0-initial-proposal.md`](./round-0-initial-proposal.md)

## Validation status

```yaml
schema_version: 1.1.0-provisional
profile: popup_message_judgment_v1
source_field_union: 90 + 165 = 255
synthetic_fixtures: 3
canonical_validation: pass
negative_mutations_rejected: 7
review_independence: same-family
acceptance_status: provisional
external_disclosure: not_sent
```

`research-refine` 的正式 cross-family acceptance 需要真实 Claude MCP 调用和完整 trace。项目现有自动外部披露授权不覆盖本弹窗课题，因此没有外发材料，也没有把 Codex agent 审计包装成跨模型验收。

## Remaining weaknesses

- real-app Android/iOS item 均为 0；
- iOS 结构化表示与 VoiceOver 相关能力尚未在目标设备实测；
- message semantics 与 critical hallucination 的双标／裁决协议尚未 pilot；
- 还未证明真实 message gap 足够普遍，也未证明 MG-PU 优于 baselines；
- screenshot/UI tree 的版权、隐私、脱敏和公开许可仍待审核；
- 新颖性与“首次”主张尚未通过系统查新；
- 无目标用户研究，不能声称真实体验改善。

## Next steps

1. 运行小规模 Android/TalkBack 与 iOS/VoiceOver 只读 capability pilot；
2. 冻结 screenshot/tree 同步窗口、message gold 规范、模型／prompt 与 gate threshold；
3. 配对比较 structure-only、vision-only、always-on 与 MG-PU；
4. 从 pilot 估计 paired effect、coverage、cluster size，再做功效分析并冻结 N；
5. 通过权限、隐私、标注和 split gate 后才进入公开发布。
