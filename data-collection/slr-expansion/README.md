# CHI 2026 SLR 扩展队列

此目录保存 PPT 14 篇冻结采集之外的新来源。它解决“发现新论文后如何进入 item 并集”的审计问题，但**当前不改写**已经发布的 255 字段合同。

## 状态语义

- `slr_index`：综述／taxonomy 只作为来源索引和标签对齐依据，不直接贡献原始 observation 字段；
- `direct_field_source`：已从原论文全文定位候选字段，但尚未完成去重、平台映射、crosswalk 与 schema 回归；
- `candidate_not_in_frozen_union`：字段不属于当前 255 字段合同，任何文档都不得把它计入现有并集。

## 当前队列

1. CHI 2026 mixed-method study：索引 31 篇移动 screen-reader 自动干预工作，约束 novelty，并把 A11yScan／TIMESTUMP 引入扩展链；
2. A11yScan（ICSE 2025）：补充 dialog 所属 UI scenario、runtime component context、Accessibility Event 与 screenshot；
3. TIMESTUMP（ICSE 2025）：补充 before／during／after node tree、动态内容类别、accessibility focus、event/live-region 与消息属性变化。

## 进入下一版 item union 的门

候选字段只有同时满足以下条件才可升级：

1. 公开全文或官方 artifact 中有逐字段 locator；
2. 与当前 90 个文献原子字段机械去重并保留 source provenance；
3. 对齐 Android/iOS 规范字段，不能把 Android API 名称外推到 iOS；
4. 更新 `source_to_item_crosswalk` 的新版本，而不是覆盖冻结的 255 条；
5. schema validator、manifest hash 与文档计数全部通过；
6. 仍严格遵守 V1：只评弹窗存在与消息，动作／Recovery 字段只能标为 advanced。

当前三个 source 的 `included_in_255_field_contract` 均为 `false`。
