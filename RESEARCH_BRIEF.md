# 面向视障人士的移动弹窗恢复：Research Brief

> 当前结论：论文应研究“可操作性暴露缺口下的可验证任务恢复”，而不是泛化地研究“结构化 UI＋视觉关弹窗”。
> 状态：`provisional`；尚未做外部跨模型审阅、系统查新、真实 iOS 闭环或目标用户实验。

## 一句话问题

对依赖 TalkBack、VoiceOver 等屏幕阅读器的视障人士，普通且可合法退出的弹窗可能阻断原任务；当关键退出入口在结构化可访问性表示中缺失、合并、歧义或不可操作时，如何按需使用视觉恢复正确动作，并证明用户的原任务已经真正恢复？

## 背景表述

建议写：

> 对依赖 TalkBack、VoiceOver 等屏幕阅读器的视障人士（以盲人和低视力用户为主体），任务阻断弹窗及其不完整的可访问性暴露可能增加恢复时间、错误操作和任务放弃风险。现有自动化对可访问性树、平台协议或视觉方法各有依赖，但树中“存在节点”不等于存在语义明确且可执行的退出路径，视觉定位成功也不等于任务恢复。

在没有目标用户研究或真实遥测前，不写“长时间无法消除、极大影响体验”已经被本文证明。

## 研究边界

- 平台：首期 Android 与 iOS；移动 Web 可作为扩展层单独报告。
- 目标人群：使用 TalkBack、VoiceOver 等屏幕阅读器操作移动设备的视障人士；技术实验与真实用户体验评估分开报告。
- 对象：阻断正常任务、低风险且可合法关闭的普通弹窗。
- 完整闭环：**识别弹窗 → 选择并执行解除动作 → 回证原任务恢复**。
- 排除：CAPTCHA、风控、PIN、生物识别、支付、安装、删除、设备管理及其他需要人工意图或安全确认的流程。
- 未知、敏感或没有安全退出动作的样本必须 `abstain/handoff`。

## 问题锚点

当前方法的残余失败不是“树为空”这么简单，而是结构化表示可能出现：

1. 关键动作入口没有独立节点；
2. 子节点被框架合并到父节点；
3. role、name、text 或 action 语义不完整／不一致；
4. 节点存在但不可点击、不可命中或不支持目标动作；
5. 弹窗候选与宿主页面候选混在一起；
6. owner/package/bundle/window/context 不匹配；
7. 树与截图不同步或采集工具失败。

黑盒条件下只能标注“未单独暴露”；若要断言系统合并、平台过滤或开发者缺陷，必须有可控 fixture、参考树或源码证据。

## 方法主线

工作名：**Actionability-Gap-Gated Recovery**。

```text
协议事件 / owner-context / 可访问性树
                ↓
平台原始字段 + 跨平台规范字段 + presence mask
                ↓
判断是否存在语义明确、可执行且 owner 正确的退出路径
        ├─ 有：使用结构化动作
        └─ 无/歧义：仅对弹窗区域调用 OCR/VLM grounding
                ↓
候选重排 + 低风险策略或 abstain
                ↓
协议动作 > 元素动作 > 坐标动作
                ↓
D ∧ C_a11y ∧ T 回证
```

- **D — Dismissal**：弹窗视觉标识与语义节点／窗口均消失。
- **C_tech — Technical context recovery**：正确 owner/context 恢复，原被阻断目标重新可操作。
- **C_a11y — Accessible context recovery**：满足 C_tech，且屏幕阅读器焦点回到原目标或合法后继目标；若朗读状态可观测，下一段朗读与恢复后的任务一致。
- **T — Task postcondition**：原任务的业务后置条件成立。

主指标：

\[
\mathrm{VTR\text{-}tech}=P(D \land C_{tech} \land T)
\qquad
\mathrm{A\text{-}VTR}=P(D \land C_{a11y} \land T)
\]

如果只做到树为空才调用视觉，方法新颖性不足；门控必须覆盖非空但 merged、ambiguous、non-actionable 和 owner-mismatch 的情况。

## 数据集设计

评测单元是完整 `episode`，不是一张截图：

```text
原任务与触发动作
→ 弹窗前/中/后观察
→ 结构化树与截图候选
→ 动作尝试
→ D/C_tech/C_a11y/T 回证与副作用
```

数据实体包括：`scenario`、`episode`、`observation`、`element_item`、`action_attempt`、`outcome`、`annotation`。

不要将 Android 与 iOS 原始字段硬展平。保存：

- 公共层：owner/context、role/class、name/text/value、stable id、action capability、state、geometry、task context；
- 原始层：`android_raw`、`ios_raw`、`dom_raw`、`visual_raw`；
- provenance、presence mask、人工真值和预测值。

严格纳入的 6 篇文献只覆盖 Android 与移动 Web，没有 iOS 闭环，因此 iOS 字段当前只是待实测工程候选。详细字段见 [`DATASET_SCHEMA.md`](./DATASET_SCHEMA.md)。

## 随机化 × N

使用分层、配对的 episode 设计：

```text
platform × owner × popup kind × exposure tier × action topology
```

- 随机化方法执行顺序、异步延迟、locale、主题、方向、字体缩放；
- 受控 fixture 可改变按钮顺序和视觉样式；
- 每种方法从同一设备快照和 App 状态开始；
- 按 App、UI framework、CMP/SDK、模板族和 OS 版本分组切分；
- 加入“无弹窗但看起来像弹窗”的负样本；
- `N` 由 pilot 方差和功效分析决定，不提前拍脑袋；
- 真实缺口为主，人工树腐蚀只做压力测试。

## 三组核心实验

### E1：缺口刻画

测量 tree-only 在不同缺口类型下的 valid-close-item recall、残余失败率和平台差异。

### E2：端到端主实验

在等 episode、等动作预算和等模型预算下比较：

- 无弹窗处理器；
- 平台协议／watcher；
- tree-only；
- screenshot-only VLM；
- naive always-on fusion；
- 本方法；
- oracle locator/action 上界。

主看 A-VTR，并将 VTR-tech 单独报告；同时报告 detection、valid-action、False Intervention、Harmful Action、abstention/coverage、焦点恢复、额外导航步数和延迟。

### E3：必要性与回证消融

- 去掉视觉；
- 去掉门控，始终调用视觉；
- 门控只判断空树；
- 去掉 owner/context 检查；
- 去掉屏幕阅读器焦点检查；
- 只看截图变化；
- 只验证弹窗消失 D。

## 否证条件

- tree-only 与本方法置信区间重叠且成本更低：视觉机制没有成立。
- always-on fusion 在等预算下稳定优于门控：门控不构成贡献。
- App/模板隔离后增益消失：存在泄漏或模板记忆。
- iOS 没有真实 D/C_tech/T 技术闭环：不能声称跨 Android/iOS 技术验证；没有 D/C_a11y/T 或真实用户实验时，不能声称跨平台视障用户恢复。
- 出现敏感或破坏性误确认：不能声称可自主部署。
- 没有目标用户研究：不能声称显著改善真实用户体验。

## 论文贡献的安全写法

当前可以写：

1. 形式化移动弹窗的 **accessibility actionability gap**，把成功定义为原任务可验证恢复。
2. 计划构建并公开一个成对记录结构化表示、像素、合法动作集合、VTR-tech 与 A-VTR 回证的 Android/iOS benchmark。
3. 检验缺口门控是否在等预算下优于 tree-only、vision-only 和 naive fusion。

当前不能写：

- 第一个提出弹窗问题；
- 第一个公开弹窗数据集；
- 第一个结构化＋视觉方法；
- 指标已经优于其他方法；
- 已显著改善残障人士体验。

论文最好只有一个主贡献：**缺口感知的可验证恢复策略**。数据集是支撑贡献，“首次提出背景”不作为独立贡献。

## 当前三个硬门

1. **iOS gate**：真实结构读取、动作执行、VTR-tech 与可观测 A-VTR 回证是否在目标场景可行。
2. **pilot gate**：真实 tree-only residual failure 是否足够大，门控是否优于 always-on fusion。
3. **evidence gate**：若以盲人和低视力用户体验为核心动机，需要目标用户参与和可访问的研究流程。

完整初版 Proposal 见 [`refine-logs/round-0-initial-proposal.md`](./refine-logs/round-0-initial-proposal.md)，本地预审见 [`refine-logs/PROVISIONAL_LOCAL_REVIEW.md`](./refine-logs/PROVISIONAL_LOCAL_REVIEW.md)。
