# PMAB V1 查新报告：移动弹窗消息判断

**版本**：2026-09-01 08:16 CST
**任务边界**：移动端；面向依赖 TalkBack／VoiceOver 的视障人士；V1 只判断弹窗是否存在以及弹窗可见消息，不执行关闭，不评焦点、原页面或原任务恢复。
**复核状态**：独立 cross-family Claude reviewer 已完成两轮复核，结论为 `PROCEED_WITH_CAUTION`。这不是论文接收判断，也不是经验结果。

## 结论先行

当前最安全的论文主线是：

> **PMAB: A Benchmark for Popup Message Judgment from Mobile Accessibility Observations**

不能再主张：

- 第一个发现弹窗给屏幕阅读器用户造成问题；
- 第一个同步采集 screenshot 与 accessibility tree；
- 第一个建立移动无障碍问题 taxonomy；
- 已改善视障用户体验；
- V1 已解决弹窗、Recovery 或原任务恢复。

仍可作为待实验验证的贡献候选：

1. 一个公开的 popup-message benchmark：同一 item 保存冻结的移动观察、双人标注的弹窗存在与消息 gold，以及用于验证消息完整性／事实性的 critical-fact anchors；
2. 在相同冻结 observation 与匹配视觉调用预算下，对 structure-only、vision-only、always-on fusion、gap-gated fusion 做配对比较；
3. 把 message-slot sufficiency 作为工程 gate，与 empty-tree 和 random-K 做消融；不把 gate 本身包装成新算法。

## 查新后的直接冲突

| 原主张 | 冲突证据 | 判定 |
|---|---|---|
| 首次提出弹窗问题 | [Pop-Up Focus Functional Specification](https://home.cs.colorado.edu/~DrG/Microsoft-SCOPE-2021/pop-ups.html) 已提出为屏幕阅读器用户识别 pop-up、告知类型与退出机制；移动端用户研究也记录了弹窗／多窗口焦点问题 | **删除** |
| screenshot + tree 采集新颖 | [Abra Mobile Accessibility Snapshots](https://abra.ai/blog/capture-android-and-ios-accessibility-hierarchy-using-abra-snapshots) 已提供 Android／iOS 同步截图、hierarchy 和节点属性查看 | **删除** |
| 移动无障碍 issue taxonomy 新颖 | [CHI 2026 mixed-method study](https://doi.org/10.1145/3772318.3791293) 系统综述 31 篇自动干预工作，并结合盲人用户研究构建 MCAG | **删除** |
| 视觉兜底本身新颖 | [Screen Recognition](https://arxiv.org/abs/2101.04893)、[ScreenAudit](https://arxiv.org/abs/2504.02110)、WhisperTest 与 VLM-Fuzz 均已覆盖像素补全、截图／元数据联合或按需视觉邻域 | **删除** |
| popup-message gold 与同预算评测 | 本轮 ASSETS／W4A／CHI／ICSE／modal／overlay 定向检索未命中“移动 popup + 双人 message/critical-fact gold + 四族同预算结果”的 exact combination | **低—中等 novelty；只能写本轮未命中，不能写世界首次** |

## 对数据集 item 并集的新增约束

CHI 2026 不能直接作为 popup-message item 字段来源；它是索引与 taxonomy 来源。需要对其中与本任务直接相邻的原论文逐篇抽取可核实字段：

- **A11yScan / ICSE 2025**：Activity、Activity-dependent UI scenario（含 dialog／menu／drawer）、Activity-sensitive state、组件 hierarchy、visible／filled／checked 等 runtime context、Accessibility Event 与 screenshot；
- **TIMESTUMP / ICSE 2025**：Activity、screen hierarchy hash、before／during／after observation、resource-id、text、content description、class、clickability、supported action、live-region／动态变化类别；
- **CHI 2026 MCAG**：只用于 gap taxonomy 对齐与相关工作映射，不把 22 类 taxonomy 误写为本项目新贡献。

只有全文字段抽取、source locator、crosswalk 和 schema validator 全部更新后，才能说这些字段已经进入 item 并集。当前 255 字段合同仍是此前 14 篇 PPT 文献与工程字段的冻结版本。

## 冻结的 V1 任务定义

输入：一个冻结移动 UI observation，可包含平台原始 accessibility representation、规范化结构与 screenshot。
输出：

- `popup_present ∈ {yes, no, uncertain}`
- `popup_message`：面向屏幕阅读器用户可直接理解的弹窗消息；无弹窗时为空
- `critical_facts`：消息中的主体、状态／请求、关键条件、否定、风险或后果等最小事实锚点
- `abstain_reason`：证据不足时必须输出

V1 不输出 action，不点击，不用“弹窗消失”作为成功，不评屏幕阅读器焦点与原任务恢复。

## 方法与基线的同预算合同

| 方法族 | 允许输入 | V1 输出 |
|---|---|---|
| Structure-only | 冻结的原始／规范化 accessibility representation | presence + message + critical facts／abstain |
| Vision-only | 冻结 screenshot | 同上 |
| Always-on fusion | 每个 item 同时使用 structure + screenshot | 同上 |
| Gap-gated fusion | 先读 structure；仅当 message-slot sufficiency 不足时调用 screenshot | 同上 |
| Empty-tree gate | 只有结构为空才调用视觉 | 作为简单 gate baseline |
| Random-K | 在匹配 K 次视觉调用预算下随机选择 item | 作为预算对照 |

必须统一 backbone／prompt／解码、冻结 split，并同时报告：

- popup presence macro-F1；
- message critical-fact recall 与 critical hallucination rate；
- valid popup message accuracy／coverage；
- visual-call rate、像素预算与延迟；
- paired cluster bootstrap 置信区间。

不得把 pre-gold prediction 当实验结果。

## Kill / Pivot 条件

- 若完成双人标注后，结构—消息缺口低于预注册阈值或几乎由单一来源解释，主线转为“何时 structure-only 已足够”；
- 若 critical-fact protocol 不能比一般 issue taxonomy 提供额外可验证性，数据集贡献降级为已有工具在 popup 子集上的应用；
- 若 gap-gated 在匹配视觉预算下不优于 strongest baseline，报告负结果，不改预算或口径追逐正结果；
- 若未完成来源许可、隐私审查、双人标注与 IAA 门，不公开媒体和 gold；
- 若 iOS 数据没有独立就绪，不做跨平台经验外推，V1 论文按 Android-only 表述。

## 审计入口

- 查新证据包：`idea-stage/NOVELTY_EVIDENCE_20260901_080500.md`
- 初轮 reviewer trace：`.aris/traces/novelty-check/2026-09-01_run01/001-top3-novelty.*`
- 残余检索复核 trace：`.aris/traces/novelty-check/2026-09-01_run01/002-residual-search-recheck.*`
- reviewer 最终定性：`PROCEED_WITH_CAUTION`
- 数据集 novelty：`LOW-MEDIUM`
- `first_problem_claim`：`DEAD`

## 当前状态

- 查新：完成，结论可用于收窄研究主张；
- 论文结果：0；
- 人工 gold：0；
- 正式 baseline：0；
- 可公开数据集：尚未满足人工标注、隐私／许可与发布门；
- 下一步：把 A11yScan、TIMESTUMP 与 CHI 2026 索引关系加入可审计来源队列，逐字段扩展 item union；并先完成不依赖 gold 的媒体 QA 与标注交接门。
