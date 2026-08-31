# Popup Episode Union Dataset v1：弹窗消息判断 Profile

当前数据 contract 的主任务是 `popup_message_judgment_v1`：给定移动端动作前 observation，判断是否存在弹窗，并输出可读消息或弃答。v1 不执行点击或关闭。

## 并集与扩展

- 14 篇既有论文：90 个原子字段；
- 我方既有方法：165 个原子字段；
- `source_to_item_crosswalk.json`：255/255 条映射；
- `message_judgment`：为当前 v1 新增、单独计数的 profile 协议字段。

保留动作、D/C/T、VTR-tech、A-VTR 是为了文献兼容和后续 advanced profile；它们在 v1 中必须为 `null/not_applicable`，不是主指标。

## v1 item

```text
identity + provenance + scenario + environment
→ one or more action-free observations
→ cross-platform structured/raw/visual evidence
→ message_judgment labels/prediction/gate/evaluation/eligibility
→ feedback notification
→ no action
```

必须满足：

- `action_attempts=[]`；
- 决策为 `no_action` 或 `abstain`；
- prediction 引用动作前 observation；
- popup/message gold 与 evidence 一致；
- v1 D/C/T/VTR 均为 null；
- synthetic fixture 不进入训练、经验指标或体验结论。

## 主指标

`VPMA` 在正样本要求 presence 正确、消息语义正确、没有关键编造；在负样本只要求 presence 正确。Abstain 的 VPMA 为 null，并必须与 coverage 一起报告。

配套指标：Popup Presence Macro-F1、message semantic correctness、Exact Match、Character F1、critical-information recall、critical-hallucination rate、abstention/coverage、visual-call rate 与 latency。

## 文件

- [`schema/item.schema.json`](./schema/item.schema.json)：v1 profile-aware 单 item schema；
- [`schema/v1_message_qa_rules.json`](./schema/v1_message_qa_rules.json)：6 个 v1 QA gate；
- [`schema/source_to_item_crosswalk.json`](./schema/source_to_item_crosswalk.json)：冻结的 255 条来源映射；
- [`data/item.template.json`](./data/item.template.json)：positive v1 模板；
- [`data/items.schema-fixture.jsonl`](./data/items.schema-fixture.jsonl)：positive、no-popup、abstain 三条 synthetic fixture；
- [`scripts/materialize_schema_fixture.py`](./scripts/materialize_schema_fixture.py)：fixture 生成器；
- [`scripts/validate_dataset.py`](./scripts/validate_dataset.py)：验证器；
- [`ANNOTATION_GUIDE.md`](./ANNOTATION_GUIDE.md)：v1 标注协议；
- [`VALIDATION_REPORT_V1_MESSAGE.md`](./VALIDATION_REPORT_V1_MESSAGE.md)：当前验证报告。

## 运行

在项目根目录用 canonical Python：

```bash
.venv/bin/python3 popup-solution/dataset-v1/scripts/materialize_schema_fixture.py
.venv/bin/python3 popup-solution/dataset-v1/scripts/validate_dataset.py
```

当前 `pass` 只表示 synthetic fixtures 通过已实现断言；真实 Android/iOS 数据集和目标用户证据仍未产生。
