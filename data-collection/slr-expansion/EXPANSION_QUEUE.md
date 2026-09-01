# SLR 扩展队列审计

| Source | 角色 | 候选字段数 | 对 V1 的直接价值 | 当前并集状态 |
|---|---:|---:|---|---|
| CHI 2026 mixed-method study | SLR index | 0 | 约束 novelty；提供 P1-P31 索引与 MCAG taxonomy | 未进入 255 |
| A11yScan, ICSE 2025 | direct source | 5 | dialog scenario、runtime context、event + screenshot | 未进入 255 |
| TIMESTUMP, ICSE 2025 | direct source | 8 | 三时点结构、动态变化、焦点／live-region、消息属性变化 | 未进入 255 |

这张表只表示字段候选已经有全文定位，不表示数据 schema 已扩展，也不表示已有 PMAB 结果。

## 下一步机械合并要求

- 解析 13 个候选 `normalized_field` 词组；
- 与冻结 90 个 literature field 做 token-level exact mapping；
- 将重复项标为 `existing_alias`，真正新增项标为 `new_candidate`；
- 生成版本化的 proposed union，不修改现有 `literature_field_union.json`；
- 经 reviewer 审查后才决定是否进入 Dataset V1.1。
