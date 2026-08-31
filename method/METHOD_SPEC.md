# Message-Gap-Gated Popup Understanding：方法规格 v1.0-provisional

> 任务 profile：`popup_message_judgment_v1`
> 方法简称：MG-PU
> 范围：只读判断和消息生成；不执行弹窗动作
> 进阶兼容：既有 Actionability-Gap-Gated Recovery 字段保留，但不参与 v1 成功判断

## 0. 范围锚与进阶路线

本规格受 [PPT 第 14 页五级回证边界](../sources/PPT_SLIDE_14_EVIDENCE.md) 约束。节点消失和截图／日志变化只能作为弱证据，不能证明原 Context、业务选择或原任务恢复。

MG-PU 是更广义 **Actionability-Gap-Gated Recovery** 路线的 V1 perception/message 子层：

```text
V1: observability gap → popup presence + accessible message
V2+: decision gap → user intent / safe candidate action
V3+: execution → authorized dismissal
V4+: recovery evidence → D + C_tech + C_a11y + B + T
```

只有 V1 在当前实验范围内。后续层级必须另建 profile、权限策略和动作后证据，不能用 V1 的 `VPMA` 替代。

## 1. 研究主张

当移动端结构化 UI／可访问性表示无法完整、无歧义地表达弹窗消息时，MG-PU 通过一个可审计的 message-sufficiency gate 按需调用弹窗区域视觉信息，并融合各通道证据，输出弹窗存在性、可读消息和关键事实；证据仍不足时安全弃答。

v1 不主张自动消除弹窗，也不主张恢复屏幕阅读器焦点、原页面或被阻断任务。

## 2. 输入与输出

### 2.1 输入

- 同一稳定 UI 状态下尽量同步的 screenshot；
- Android accessibility/UI hierarchy、iOS XCTest/XCUI snapshot、移动 Web DOM 等平台原始结构；
- 规范化的 owner/context、role/class、name/label/text/value/hint、层级、可见性与几何；
- 可获得时的 TalkBack／VoiceOver focus/utterance 观察；
- 每个字段的 presence status、provenance、时间戳和同步状态。

所有方法在同一个冻结 observation 上运行。不得使用点击后的截图、树或人工真值作为输入。

### 2.2 输出

```json
{
  "status": "judged",
  "popup_present_pred": true,
  "message_text_pred": "Special offer. Ends today.",
  "critical_facts_pred": ["offer", "ends today"],
  "confidence": 0.92,
  "structured_message_complete": false,
  "visual_fallback_used": true,
  "source_observation_id": "obs.popup",
  "evidence_uris": [],
  "model_or_rule_version": "mg-pu-v1",
  "latency_ms": 120
}
```

`status` 只能是 `judged` 或 `abstain`。弃答时不得输出臆测消息。

## 3. 安全与任务不变量

1. `action_attempts=[]`。
2. 决策必须是 `no_action` 或 `abstain`，不能是 `execute`。
3. 不输出或调用 tap coordinate、element action、protocol handler、Back、外部跳转或业务 API。
4. Dismissal、`C_tech`、`C_a11y`、`T`、`VTR-tech`、`A-VTR` 在 v1 中为 `null/not_applicable`。
5. CAPTCHA、风控、身份认证、支付、权限安全控制等样本不进入主数据；若被观察到，只允许 `abstain/out_of_scope`。

## 4. 方法模块

### M1 Observation Synchronizer

冻结一个动作前 UI 状态，记录树与截图时间戳、UI fingerprint、foreground owner、window/context 和采集错误。超过预设同步窗口或 fingerprint 不一致时标为 `stale`，不能静默融合。

### M2 Cross-platform Normalizer

保留原始平台字段，同时映射到公共层：

```text
owner/context
role_or_class
name_or_text
value_or_hint
visible/focusable/enabled
bounds + hierarchy + reading order
```

规范化不允许删除否定词、金额、日期、单位、对象、动作后果或按钮文案。

### M3 Popup Detector

基于 window/owner/layer、modal 属性、层级隔离、bounds/overlay、文本聚类和可选视觉检测给出 `popup_present_pred`。结构证据不足时可以请求视觉 detector；无弹窗负样本必须用完整、稳定上下文确认，不能把“树中没找到”直接当成 no-popup。

### M4 Structured Message Reconstructor

在候选 popup scope 内按可访问阅读顺序重建：

- title；
- body；
- list/option 文本；
- 关键金额、时间、对象、限制与后果；
- 有助于理解的按钮文案，但不据此执行动作。

记录每个片段的 source node、原始字段和 provenance。宿主页面候选必须被 owner/context、layer 或 ROI 约束排除。

### M5 Message Sufficiency Gate

门控输出 `structured_message_complete`、缺口原因和置信度。结构化消息只有同时满足以下条件才可直接输出：

- 弹窗 scope 与 owner/context 可识别；
- 至少有非空主体消息，或明示该弹窗只有标题／图形；
- 标题、正文和关键事实没有明显截断；
- 结构内阅读顺序可解释；
- 没有树—图不同步或跨通道矛盾；
- 不存在关键图像文本只在 screenshot 中可见的证据。

缺口枚举：`missing`、`merged`、`ambiguous`、`contradictory`、`stale`、`owner_mismatch`、`visual_only_text`、`unknown`。

不得把 gate 简化为“树为空才调用视觉”。

### M6 Visual Message Completer

只在 gate 触发时处理 popup ROI：OCR、layout reading order、图标／警告语义和必要的 VLM transcription。视觉模块只能提出带证据定位的文本／关键事实候选，不能提出或执行点击动作。

使用 frozen model、prompt、OCR version 和 decoding configuration。记录 visual call count、latency、cost 与每条候选的 confidence。

### M7 Evidence Aligner and Message Composer

对齐结构节点、OCR span 和视觉候选：

1. 去重但保留原始文本；
2. 对金额、日期、否定、对象和后果采用严格冲突检测；
3. 通道一致时按可访问阅读顺序合成；
4. 关键冲突无法解决时弃答，不多数投票臆断；
5. 输出可读纯文本、关键事实列表和逐片段 evidence URI。

### M8 Confidence and Abstention

置信度应校准为“存在性与消息均可靠”的选择性风险，而不是模型 token probability。以下任一情况触发弃答或降覆盖：

- popup scope 不确定；
- 截图或结构不可读／过期；
- 关键金额、时间、对象或否定发生冲突；
- 关键消息仍不可观察；
- 样本在安全边界之外。

## 5. 训练与开发

- 先以规则和冻结模型建立无训练 baseline，避免把通用 VLM 能力冒充方法贡献。
- 若训练 gate，只使用 training split，特征必须来自动作前 observation。
- App、popup template、SDK/CMP、UI framework、OS family 与 near-duplicate group 不得跨 split。
- 校准阈值只在 validation split 冻结。
- 人工树腐蚀只做压力测试，不能替代真实暴露缺口。

## 6. 真值与标注

v1 最小真值：

- `popup_present_gt`；
- `message_text_gt`；
- `critical_facts_gt[]`；
- `message_text_observability`；
- 每条真值的 evidence URI。

正样本消息按屏幕可观察内容和合理阅读顺序转录，不补写应用意图。正式 validation/test 由两名标注者盲法独立标注并裁决。`message_semantically_correct` 与 `critical_hallucination` 由独立裁决得到；字符串 Exact Match／Character F1 只作辅助。

结构暴露缺口不由截图 A/B 盲标直接推断。截图消息 gold 完成后，另以冻结
structure bundle 对照最终 message gold，做 method-blind structure–visual gap
audit；两名独立审计者和第三位仲裁者记录 `structured_message_complete_gt`、
`gap_reasons_gt`、结构中缺失的 critical facts 与 host-text contamination。该
sidecar 只用于数据属性、分层分析与 gate 诊断，不回流 pre-gold prediction，也
不替代 VPMA。

## 7. 指标

### 7.1 主指标

```text
positive popup: VPMA = presence_correct
                       AND message_semantically_correct
                       AND NOT critical_hallucination

no-popup:       VPMA = presence_correct
```

Abstain 不能当作正确 no-popup。主结果同时给出 `VPMA` 与 coverage，防止通过大量弃答提高条件准确率。

### 7.2 分项指标

- Popup Presence precision／recall／Macro-F1；
- Message Semantic Correctness；
- Message Exact Match 与 Character F1；
- Critical Information Recall；
- Critical Hallucination Rate；
- Coverage／Abstention；
- Visual Fallback Rate；
- p50/p95 latency 与模型成本。

所有指标按 platform、owner、popup kind、exposure gap、locale、UI framework 和 message complexity 分组，并报告置信区间。

## 8. Baseline 与消融

Baselines：structure-only、OCR-only、screenshot-only VLM、always-on structure+vision、MG-PU、human-readable-message oracle。

Ablations：no vision、always vision、empty-tree-only gate、no owner/context、no sync check、no contradiction check、no critical-fact constraint。

比较必须使用完全相同的冻结 observation、split 和预算。任何 baseline 也不得执行点击。

## 9. 错误分类

- presence false negative／false notification；
- popup/host text contamination；
- missing title/body；
- wrong reading order；
- dropped negation；
- wrong amount/date/object/condition；
- critical hallucination；
- stale cross-channel fusion；
- unnecessary visual call；
- avoidable abstention。

## 10. 进阶 Recovery 层

后续可以在独立 `dismissal_recovery_advanced` profile 中研究动作执行和 `D ∧ C_tech/C_a11y ∧ T`。该 profile 需要新的权限、风险策略、动作后观察和回证，不得将 v1 item 回填后伪装为独立 episode，也不得用 `VPMA` 推导 Recovery 成功。

## 11. Kill criteria

- MG-PU 与 structure-only 的 VPMA 置信区间重叠且成本更高；
- always-on 在等预算下稳定优于 gate；
- 真实缺口子集太小，收益只来自人工腐蚀；
- 分组隔离后增益消失；
- VPMA 增益伴随更高 critical hallucination 或不可接受的 coverage 降低；
- iOS 无真实设备观察却试图声称跨平台；
- 无目标用户研究却试图声称体验改善。
