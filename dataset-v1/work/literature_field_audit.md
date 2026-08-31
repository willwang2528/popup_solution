# 已有 14 篇论文方法字段并集：本地审计

## 结论

- 从 `papers.jsonl` 的 `structured_items`、`visual_items`、`context_items` 中拆出并去重 **90** 个原子字段；每个 `normalized_field` 词项恰好映射一次。
- 论文角色严格保持为 **6 篇 core experimental seed** 与 **8 篇 schema/method reference**；字段级 `paper_ids` 已按两组分开。
- 阶段分布：discovery 34，action 17，verification 19，context 20。
- 来源角色分布：core-only 41，reference-only 33，core+reference 16。
- 字段证据状态分布：inferred_from_local_source 10，mixed 12，ppt_only_candidate 2，reported 66。
- 14 篇论文均至少贡献一个字段；core 覆盖 6/6，reference 覆盖 8/8。

## 证据纪律

1. `reported` 只对应项目内已核对原文记录；`inferred_from_local_source` 保留本地筛选/笔记边界；`ppt_only_candidate` 不升级为原文事实。
2. `platform` 是唯一从论文顶层元数据扩展到 14 篇的字段；其余字段的 `paper_ids` 均直接来自逐篇 item 的 `normalized_field`。
3. 原子化仅拆分字符串中的 ` + `；没有把论文未报告的 enabled、focus order、utterance 或 task recovery 填入并集。
4. `role/name/id` 保留为 HotMobile 的复合对象；没有据此声称三个子字段在其他平台都可用。
5. PPT 第 5 页混标图没有进入 2018 iOS 测试论文的字段证据。

## 关键空白

- **无视障用户闭环字段**：14 篇均未把 TalkBack/VoiceOver 焦点、朗读及原任务恢复作为主要评测。
- **无严格 iOS seed**：严格 6 篇只覆盖 Android 与移动 Web；iOS 字段来自 reference 方法。
- **弱回证不能升级**：WhisperTest 的画面变化、SSLDetecter 的界面相似度、网络状态、命令送达都不能独立证明弹窗消失。
- **平台字段不等价**：Android hierarchy、iOS UIA/XCTest element 与 DOM 的 name/role/geometry 只是公共别名，原始 provenance 必须保留。
- **一个 PPT-only 核心来源**：Abandon All Hope 的本地字段仍需原文补证。

## 机器检查

- JSON 解析、90 个 `field_path` 唯一性、必需键、阶段枚举、requiredness 枚举、证据集合与论文集合一致性：均已通过本地 `jq` 检查。
- 字段路径唯一：生成时已断言。
- 必需键：生成时已断言每项含 `field_path`、`type`、`requiredness`、`paper_ids`、`method_stage`、`evidence_status`、`notes`。
- 角色清单：6+8=14，且字段引用只允许来自该清单；与 90 个源 `normalized_field` 原子词项的集合比对无缺项、无多项。
