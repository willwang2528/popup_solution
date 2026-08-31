# PPT 数据采集与方法规格：本地独立审计

> 审计类型：同模型家族、只读、`provisional`。
> 结论：未发现硬阻断；可作为 capability probe 与 feasibility pilot 的研究起点，不能视为跨模型验收或实验通过。

## 已核对

- `papers.jsonl` 为 14 篇、14 个唯一 ID，CSV 的 ID 与 strict 标记一致。
- strict 6 与既有 census 完全对应：Cookieverse、TCF A(A)ID、POKER、HotMobile 2018、Abandon All Hope、VLM-Fuzz。
- 角色计数为 6 篇 `core_experimental_seed`、8 篇 `schema_method_reference`。
- 人群、边界与指标一致：使用 TalkBack/VoiceOver 的视障人士；只自动处理普通低风险退出动作；高风险流程 abstain/handoff。
- `VTR-tech = D ∧ C_tech ∧ T` 与 `A-VTR = D ∧ C_a11y ∧ T` 已分开；前者不能代替视障用户体验结论。
- 没有把“第一个”“已公开”“已经优于基线”“已改善体验”写成当前事实。

## 已修正的歧义

`ppt_slides` 现已在 schema 中定义为“论文出现或被讨论的页”，不是 primary-evidence 标记。PPT 第 5 页的 DiOS/现代 XCUITest 混标图仍可作为“出现页”记录，但不能作为 2018 iOS Testing 的实证；真实 provenance 只看 `source_evidence` 与 `collection_notes`。

## 剩余硬门

1. iOS 严格闭环论文为 0，必须先跑真实 capability probe。
2. Abandon All Hope 当前为 `ppt_only`，获得本地全文前不能扩写字段和样本量。
3. 14 篇均未评测 TalkBack/VoiceOver 焦点、朗读与视障用户任务恢复；A-VTR 需要新采集和目标用户研究。
4. 方法尚未跑 pilot，不能声称优于 tree-only、vision-only 或 always-on fusion。
5. 未对弹窗研究调用外部 Claude；当前审计不具备 cross-family 接受状态。
