# PPT 论文内容数据采集

本目录对已验收 PPT 中的 14 篇论文做结构化采集，服务于两件事：

1. 从已有工作中提取结构化 UI、视觉、动作与回证字段的可追溯并集；
2. 为当前 Message-Gap-Gated Popup Understanding v1 与后续 advanced Recovery 层冻结输入、标签、基线与证据边界。

> v1 范围修订：当前主实验只做弹窗存在性与消息判断，不执行解除动作。本文献目录继续保留动作和回证字段，是为了忠实记录已有方法并兼容后续进阶研究，不代表它们仍是 v1 必需字段。

来源 PPT 为 ARIS 工作区中的 `mobile弹窗问题调研-v1-formatted-v2.pptx`：论文总览位于第 2 页，方法与回证位于第 3–18 页。独立仓库不复制该 PPT；本目录保留其派生记录、来源定位与证据等级。

当前首轮采集结果：14/14 篇完成；6 篇为 `core_experimental_seed`，8 篇为 `schema_method_reference`；证据等级为 10 篇 `full_text_verified`、3 篇 `local_note_verified`、1 篇 `ppt_only`。

## 文件

- [`collection.schema.json`](./collection.schema.json)：每篇论文的机器可读采集 schema。
- [`papers.jsonl`](./papers.jsonl)：14 篇论文的逐篇采集记录；一行一篇。
- [`papers.csv`](./papers.csv)：便于浏览的核心字段摘要。
- [`COLLECTION_SUMMARY.json`](./COLLECTION_SUMMARY.json)：计数、平台覆盖、证据等级、质量警告与校验状态。
- [`FIELD_UNION.md`](./FIELD_UNION.md)：论文字段并集、来源和能否进入我们数据集的判断。
- [`../method/METHOD_SPEC.md`](../method/METHOD_SPEC.md)：由采集结果反推的方法规格。

## 两层纳入规则

### Core experimental seed

论文必须同时提供：

1. 识别当前弹窗或其操作入口；
2. 在设备、模拟器或移动 Web 环境中实际执行解除动作；
3. 动作后提供弹窗特异回证。

只有满足三阶段的论文能直接作为实验 episode、字段和基线的核心来源。

### Schema / method reference

未满足严格三阶段的 PPT 论文仍可用于：

- 补充 Android/iOS/DOM 的候选字段；
- 定义视觉、协议和执行通道；
- 构造弱回证基线；
- 说明失败边界。

它们不能被写成“已有端到端闭环证据”。

## 证据等级

```text
full_text_verified   已核对项目内 PDF/full text 的方法、实验或结果页
local_note_verified  已核对项目内证据笔记或筛选记录，尚未复核完整原文
ppt_only             当前只由 PPT 支撑，必须保留这一限制
```

## 采集纪律

- 所有字段必须附项目内证据路径及页码或行号。
- `ppt_slides` 只表示论文在 PPT 中出现或被讨论的页，不代表该页所有图文都是可采信原始证据；实证等级以 `source_evidence` 和 `collection_notes` 为准。
- 不把“clicked/command sent/画面变化”写成真实任务恢复。
- 不把测试框架能读到的 XCUI/Appium page source 等同于视障人士使用 VoiceOver 时的真实焦点和朗读体验。
- 黑盒样本只能标 `not_separately_exposed`；系统合并、过滤或开发者缺陷需要 fixture、源码或参考树确认。
- 严格论文字段并集目前只覆盖 Android 与移动 Web；iOS 字段单列为待真实采集验证的工程候选。
- 不访问或导入任何被项目政策排除的旧 GUI Agent Memory 工作区。
- PPT 第 5 页存在来源混标：DiOS hierarchy 与现代 XCUITest 示例不能作为 2018 年 *An Approach for iOS Applications' Testing* 的实证；机器记录已隔离该图，只保留可追溯文本与筛选证据。

## 面向视障人士新增的采集字段

v1 必须补采：

- `assistive_technology`：TalkBack / VoiceOver 及版本；
- `popup_present_gt/pred`；
- `message_text_gt/pred`、`critical_facts_gt/pred`；
- message observability、structure sufficiency、visual fallback、confidence、abstain 与 evidence；
- `message_semantically_correct`、`critical_hallucination` 与 `VPMA`。

以下字段保留为 advanced Recovery 层，不是 v1 纳入门槛：

- `screen_reader_focus_before`、`screen_reader_focus_after`；
- `utterance_before`、`utterance_after` 或可验证的朗读摘要；
- `focus_restored_to_blocked_target`；
- `extra_navigation_steps_after_dismissal`；
- `user_handoff_required`；
- 真实用户实验中的恢复时间、错误动作和任务放弃。

其中真实用户体验字段只能通过合规的目标用户研究获得，不能由自动化日志或 v1 消息准确率替代。
