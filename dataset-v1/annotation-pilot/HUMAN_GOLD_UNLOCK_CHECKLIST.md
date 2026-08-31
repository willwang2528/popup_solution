# Human-gold 解锁检查表

状态：**NO-GO（2026-09-01）**。现有 30-item 批次、盲标模板、adapter evidence 与 agreement 工具已经就绪，但以下门槛未全部满足，因而不能开始可计分实验，也不能把来源目录名、OCR 或模型输出当作 gold。

## 开标前门槛

- [x] loopback-only 隔离 viewer 已实现并通过反泄漏测试：只接受规范化 `adapter_item_handle`，只展示授权截图，不读取或渲染 coordinator metadata。
- [ ] Coordinator 在隔离权限下分别启动 A/B viewer，并只交付随机 URL 与 `view_session_id`；A/B 不获得 repo 或 adapter 根目录文件权限。
- [x] 私有目录 `dataset-v1/annotation-pilot/private/` 已进入 Git ignore。
- [x] 已创建本地私有工作副本：目录权限 `0700`、A/B 与 adjudication 工作文件权限 `0600`；这些文件均被 Git ignore，不会原地填写 tracked templates。
- [ ] PI 在查看 A/B 输出前冻结 pilot 接受/返工阈值。
- [ ] 冻结“全部 30 项 final adjudication”流程：分歧项裁决；一致项也由第三位真实人复核确认。

## 不能由模型代填

A/B 人工字段：annotator pseudonym、presence、message text/observability、semantic slots、confidence、真实 view session、证据笔记、三项 blindness attestation、真实开始/结束时间。

Adjudicator 人工字段：adjudicator pseudonym、全部 `*_final`、decision rationale、`evidence_rechecked_via_adapter=true`、resolved time。

模型 preannotation、OCR、source sampling label 与 agreement report 都不得填充这些字段，也不得提前展示给 A/B。

## 完成后的硬验收

- A/B 各 30 条 completed；item 集完全一致且均为唯一 ID；A/B pseudonym 不同。
- 60/60 `adapter_viewed=true`；60/60 `raw_image_copied=false`；180/180 blindness attestation 为 true。
- 所有时间戳合法，完成时间不早于开始时间；`paired_items=30`。
- 全部 30 项都有 completed adjudication output；所有 resolved 项重新查看 adapter evidence。
- `cannot_resolve` 项不得进入 metrics。
- 私有输出持续被 Git ignore，权限保持 `0700/0600`，且不含原图、base64、source label 或带标签的源路径。

## 待 PI 预冻结的 provisional 阈值建议

这些阈值是审计建议，不是当前已经批准的研究事实：

- presence observed agreement ≥ 0.90；Cohen's κ ≥ 0.80；κ 因退化分布不可定义时不自动通过；
- jointly-popup comparable items ≥ 10，否则扩充 pilot；
- normalized message agreement ≥ 0.85；exact message agreement ≥ 0.70；
- semantic-slot exact-set ≥ 0.75；mean Jaccard ≥ 0.85；
- 每位 annotator 的 `uncertain + unusable` ≤ 3/30；final `cannot_resolve` ≤ 3/30。

即使全部通过，也只解锁技术 benchmark，不构成视障用户体验改善或 recovery 成功证据。
