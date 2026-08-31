# 弹窗问题研究

本目录是后续研究的主入口。研究目标收拢为：面向使用 TalkBack、VoiceOver 等屏幕阅读器的视障人士，在正常、获授权的软件使用或测试流程中，可靠地处理阻断任务的普通弹窗，并恢复、完成原始任务。

## 当前入口

1. [`RESEARCH_RULES.md`](./RESEARCH_RULES.md)：从飞书 revision 46 原样同步的研究章程；后续研究开始前必须先读。
2. [`AGENTS.md`](./AGENTS.md)：把研究章程转化为仓库级执行约束。
3. [`RESEARCH_BRIEF.md`](./RESEARCH_BRIEF.md)：问题锚点、方法主线、实验与贡献口径。
4. [`DATASET_SCHEMA.md`](./DATASET_SCHEMA.md)：episode 数据模型、跨平台字段、随机化与标注协议。
5. [`refine-logs/FINAL_PROPOSAL.md`](./refine-logs/FINAL_PROPOSAL.md)：当前最佳完整 Proposal，状态为 `provisional`。
6. [`refine-logs/PROVISIONAL_LOCAL_REVIEW.md`](./refine-logs/PROVISIONAL_LOCAL_REVIEW.md)：本地同模型家族预审与剩余风险。
7. [`refine-logs/DATA_COLLECTION_LOCAL_AUDIT.md`](./refine-logs/DATA_COLLECTION_LOCAL_AUDIT.md)：14 篇采集与方法规格的同模型家族只读审计。
8. [`data-collection/papers.jsonl`](./data-collection/papers.jsonl)：PPT 14 篇论文的逐篇机器可读证据记录。
9. [`data-collection/FIELD_UNION.md`](./data-collection/FIELD_UNION.md)：跨 Android、iOS、移动 Web 的字段并集、provenance 与证据边界。
10. [`method/METHOD_SPEC.md`](./method/METHOD_SPEC.md)：Actionability-Gap-Gated Recovery 方法、训练、推理与回证规格。
11. [`dataset-v1/README.md`](./dataset-v1/README.md)：90 个论文字段＋165 个我方方法字段的 episode 数据集、255 条 crosswalk、QA 门与非实测 schema fixture。

## 核心问题

完整链路必须分别解决：

1. 发现弹窗；
2. 识别弹窗的所属方、类型与意图；
3. 选择合法且语义正确的动作；
4. 通过对应执行通道完成操作；
5. 验证弹窗已消失；
6. 恢复原任务上下文；
7. 验证原任务的业务后置条件。

面向视障人士还必须验证：屏幕阅读器焦点回到原目标或合法后继目标，且下一段朗读与恢复后的任务上下文一致（在平台可观测或真实用户研究中验证）。

仅命中坐标、点击按钮或观察到弹窗消失，不视为端到端解决。

## 研究边界

- 包含：App、系统、浏览器与 WebView 中会阻断任务的 UI 弹窗。
- 包含：检测、归因、决策、执行、验证、上下文恢复与任务完成。
- 不包含：绕过 CAPTCHA、风控、身份认证、权限或平台安全控制。
- 不把视觉变化、元素消失或单次点击成功直接等同于任务恢复。
- 不把 Appium/XCUI/UIAutomator 能读取元素等同于 TalkBack/VoiceOver 用户真实可达、可聚焦或可理解。
- 没有目标用户实验时，只能报告技术恢复，不宣称真实视障用户体验已经改善。

## 本仓库材料

- [`data-collection/`](./data-collection/)：PPT 14 篇论文的字段与证据采集。
- [`method/`](./method/)：当前方法规格。
- [`dataset-v1/`](./dataset-v1/)：字段并集、单 episode schema、fixture 与 QA。
- [`refine-logs/`](./refine-logs/)：proposal 演化与本地审阅记录。

原始论文 PDF、PPT 和上游 ARIS 工作区未复制进本仓库；机器可读记录保留了来源定位与证据等级。后续研究提交以 Git 历史作为版本追踪入口。
