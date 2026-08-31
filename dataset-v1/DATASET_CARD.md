# Dataset Card：Popup Message Union Dataset v1

## 基本信息

- 目标人群：使用 TalkBack、VoiceOver 等屏幕阅读器的盲人和低视力移动用户；
- 任务：弹窗存在性与消息判断；
- 方法输入：结构化 UI／可访问性表示，必要时加 screenshot ROI；
- 方法输出：popup/no-popup/abstain、可读消息、关键事实、置信度与证据；
- v1 禁止动作：不点击、不关闭、不修改应用状态。

## Intended use

- 测量移动弹窗消息在结构化可访问性表示中的暴露缺口；
- 训练／评测 structure-only、vision-only、always-on fusion 与 message-gap-gated 方法；
- 比较 Android、iOS 和扩展移动 Web 的消息覆盖与判断性能；
- 分析 critical-information omission 与 hallucination。

## Out of scope

- CAPTCHA、风控、身份认证、支付、权限安全控制、人工审核；
- 自动关闭或替用户做选择；
- 从消息准确率推断弹窗已消失、焦点已恢复、原任务已恢复；
- 在没有目标用户研究时声称真实用户体验改善。

## 数据来源与字段

数据 item 采用 14 篇已有论文的 90 个字段与我方既有方法 165 个字段的语义并集，共 255 条可审计 crosswalk。v1 另加 `message_judgment` profile；该扩展单独计数，避免改写历史来源证据。

保存平台原始层、跨平台规范层、截图／OCR、候选、provenance、presence status、标注和 advanced recovery 兼容字段。iOS 字段在真实目标设备 capability probe 前仍是候选，不能用框架文档替代实测。

## 标注与质量

- 动作前 observation 先冻结并持久化 prediction，再解锁 gold；
- validation/test 语义真值由两名标注者独立完成并裁决；
- message text 不翻译，不删除否定、金额、日期、对象、条件或后果；
- evidence 保存 URI、hash、media type、capture channel、redaction status；
- 六类 group 防止 App／模板／SDK 等泄漏。

## Metrics

主指标 `VPMA`；配套报告 presence Macro-F1、正类 recall、false-notification rate、message semantics、Exact Match、Character F1、critical-information recall、critical-hallucination rate、coverage、visual calls、latency 和分组置信区间。

## 当前版本与限制

- Schema：`1.1.0-provisional`；
- 当前仅有 3 条 synthetic schema fixture：positive/no-popup/abstain；
- 已冻结 120 条 PopSweeper 来源候选（来源目录标签为 60 `ads` / 60 `no_ads`；每类 45 numeric + 15 named；seed `20260901`）。这些目录标签只用于分层抽样，不是人工 popup presence gold；90 条 numeric 候选均验证有 RICO semantic JSON/PNG，message gold 仍为 pending，且 raw image 采用 adapter-only、不在仓库中再分发；
- real-app item：0；controlled fixture item：0；iOS item：0；
- 255 条来源 crosswalk 保持完整；
- v1 QA 4 个 full-automated、2 个 partial-automated；发布前仍需人工证据、隐私、权限和标注门。

因此当前产物是 **collection-ready contract + frozen source-candidate manifest**，不是公开实测 benchmark，也不是方法效果证据。

## Advanced compatibility

动作、Dismissal、`C_tech`、`C_a11y`、`T`、`VTR-tech`、`A-VTR` 继续存在，但只属于未来 `dismissal_recovery_advanced` profile。v1 不允许这些字段出现成功值。
