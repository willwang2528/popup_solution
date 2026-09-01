# 面向视障人士的移动弹窗消息判断：Research Brief

> 当前结论：v1 研究“可访问性消息暴露缺口下的弹窗消息判断”，不执行关闭动作，也不把 Recovery 作为主任务。
> 状态：`provisional`；尚未完成系统查新、真实跨平台数据采集或目标用户研究。

## 一句话问题

对依赖 TalkBack、VoiceOver 等屏幕阅读器的视障人士，当移动端弹窗的标题、正文或关键信息在结构化可访问性表示中缺失、合并、异构呈现或相互矛盾时，能否通过结构优先、视觉兜底的方法，可靠判断弹窗是否存在并生成正确、完整且不编造关键信息的可读消息？

## 背景与边界

任务阻断弹窗及其不完整的可访问性暴露可能增加视障用户理解当前界面的困难。该影响是研究动机；在没有目标用户研究或真实遥测前，不写成本文已经证明的用户体验改善。

v1：

- 平台以 Android 与 iOS 为主，移动 Web／WebView 单独分组；
- 只处理普通、获授权观察、非安全绕过的弹窗；
- 只判断存在性并生成消息；
- 不点击、关闭、确认、拒绝或修改应用状态；
- 对不确定、敏感、图像不可读或证据矛盾的样本允许弃答。

CAPTCHA、风控、身份认证、权限安全控制、支付确认、人工审核等不进入 v1。Dismissal、焦点恢复、原页面恢复和原任务恢复为进阶层。

## 问题锚点：Accessibility Message Gap

结构化表示可能非空，却仍不能形成可靠的弹窗消息：

1. 标题、正文或操作后果没有暴露；
2. 多个子节点被合并，阅读顺序或语义边界丢失；
3. Android 与 iOS 的 role、name、label、text、value、hint 表达不一致；
4. 屏幕中的关键金额、时间、对象、警告或取消条件只存在于像素中；
5. 宿主页面文本与弹窗文本混在一起；
6. 树与截图不同步，或不同通道互相矛盾。

黑盒条件下只标注可观察到的 `missing/merged/ambiguous/contradictory/stale`；“系统过滤”或“开发者缺陷”等因果标签需要受控 fixture、参考树或源码证据。

## 方法：Message-Gap-Gated Popup Understanding（MG-PU）

```text
owner/context + 可访问性树／UI hierarchy
                 ↓
弹窗检测 + 结构化消息重建
                 ↓
Message Sufficiency Gate
       ├─ 完整且一致：直接输出
       ├─ 缺失/合并/矛盾：弹窗 ROI OCR／视觉补全
       └─ 仍不可靠：abstain
                 ↓
结构与视觉证据对齐、去重、排序
                 ↓
输出存在性、可读消息、关键事实、置信度与证据
```

门控不只检查“树是否为空”，而要判断：是否找到弹窗证据，标题／正文是否覆盖，关键事实是否缺失，阅读顺序是否合理，owner/context 是否一致，树与截图是否新鲜同步，以及通道间是否矛盾。

视觉兜底只补全消息，不生成点击坐标，不触发动作。输出应可直接交给屏幕阅读器或上层产品，但 v1 实验只验证消息本身。

## 数据与 item

一个 v1 item 是一次只读消息判断记录：

```text
scenario + 同步观察
→ 结构化原始字段／规范字段 + screenshot
→ popup/message 人工真值
→ 方法预测、门控与证据
→ VPMA 与分项指标
```

每个 item 继续保存已有论文方法与我方方法字段的并集：公共规范层、`android_raw`、`ios_raw`、`dom_raw`、`visual_raw`、provenance、presence mask、人工标注和预测。动作与恢复字段作为 advanced compatibility layer 保留，但 v1 样本不要求其有值。

关键真值包括：`popup_present_gt`、`message_text_gt`、`critical_facts_gt`；关键预测包括：`popup_present_pred`、`message_text_pred`、`critical_facts_pred`、confidence、abstained、structured sufficiency、visual fallback 和 evidence URI。

## 指标

对 popup 正样本：

\[
\mathrm{VPMA}=P\land M\land\neg H
\]

- `P`：弹窗存在性判断正确；
- `M`：人工双标／裁决确认消息语义正确；
- `H`：是否出现会改变用户理解或决策的关键编造。

对无弹窗负样本，`VPMA=P`。主报告 `VPMA`，并报告：

- popup detection precision／recall／F1；
- message semantic correctness rate；
- critical-information recall；
- critical-hallucination rate；
- coverage／abstention；
- visual fallback rate、latency 与成本；
- Android／iOS、owner、popup kind、exposure tier、语言和 UI framework 分组结果。

自动字符串指标只能作为辅助；消息语义正确性和关键编造必须有盲法人工裁决协议。

## v1 核心实验

### E1：消息暴露缺口刻画

比较可见弹窗内容与结构化表示，测量标题、正文、关键事实和阅读顺序的覆盖率，并按平台与缺口类型分组。

### E2：主实验

在相同 item 和模型预算下比较：

- structure-only；
- screenshot-only OCR／VLM；
- always-on structure+vision；
- MG-PU gated structure+vision；
- human-readable-message oracle 上界。

主看 `VPMA`。任何方法均不得点击弹窗。

### E3：消融

- 去掉视觉；
- 始终调用视觉；
- 门控只判断空树；
- 去掉 owner/context；
- 去掉树—图同步检查；
- 去掉跨通道矛盾检测；
- 去掉关键事实约束。

## 随机化 × N

采用分层、配对设计：

```text
platform × owner × popup kind × exposure tier × language × message complexity
```

同一 item 对所有方法复用完全相同的冻结观察；方法顺序随机化。按 App、模板族、SDK/CMP、UI framework 和 OS family 分组切分，加入相似非弹窗负样本。`N` 由 pilot 方差、目标置信区间宽度和功效分析决定，不预先拍脑袋。

## 否证条件

- structure-only 与 MG-PU 的 `VPMA` 置信区间重叠且前者成本更低：视觉兜底没有成立。
- always-on 在等预算下稳定优于门控：门控不构成贡献。
- App／模板分组隔离后增益消失：可能是泄漏或模板记忆。
- 增益来自更高 hallucination 或更低 coverage：不能声称更可靠。
- iOS 没有真实设备观察：不能声称完成跨 Android／iOS 验证。
- 没有目标用户研究：不能声称真实用户体验已经改善。

## 贡献口径

当前可作为待检验目标：

1. 形式化移动弹窗的 accessibility message gap；
2. 构建并计划公开一个 Android／iOS 弹窗消息判断数据集，保留结构、视觉、原始平台字段与证据；
3. 检验 message-gap gating 是否在等预算下优于 structure-only、vision-only 和 always-on fusion。

当前不能写成既定事实：第一个提出问题、第一个公开数据集、指标已经优于其他方法、已改善视障人士体验。

## 进阶研究

在 v1 之后可逐级研究：安全动作建议、授权后的弹窗消除，以及幻灯片 14 的五级回证 `D/C_tech/C_a11y/B/T` 与派生指标 `VTR_tech/A_VTR`。每一级都需独立权限、安全策略和回证；不得用 v1 消息准确率替代 Recovery 证据。
