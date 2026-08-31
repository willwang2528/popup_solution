# Popup Episode Union Dataset v1 验证报告

> 日期：2026-08-31
> 最终判定：**字段并集与单 episode contract 完成；schema 保持 provisional；真实设备经验数据尚未产生。**

## 1. 交付状态

| 层次 | 状态 | 准确含义 |
|---|---|---|
| 来源字段并集 | 通过 | 14 篇 PPT 论文的 90 个原子字段与我方方法的 165 个原子字段全部登记。 |
| Crosswalk | 通过 | 255/255 个来源字段均映射到 `item.schema.json` 中存在的 canonical pointer；无遗漏、无重复来源键。 |
| 单 item 契约 | 通过 | 一个 item 表示一次完整弹窗恢复 episode，覆盖触发、观察、候选、决策、动作与 D/C/T 回证。 |
| Schema 冻结 | 未通过 | Android/TalkBack 与 iOS/VoiceOver capability pilot 尚未完成，版本保持 `1.0.0-provisional`。 |
| Empirical dataset | 未产生 | 当前只有 1 条不可训练、不可评测的 synthetic schema fixture；real-app 与 controlled-fixture item 均为 0。 |

## 2. 最终机器验证结果

项目解释器执行：

```text
.venv/bin/python3 popup-solution/dataset-v1/scripts/validate_dataset.py
```

结果：

```text
status: pass
validation_scope: schema_shape_and_documented_automated_assertions_only
items: 1 synthetic schema fixture
source fields: 90 literature + 165 ours = 255
QA contract: 23 item gates + 6 dataset gates
QA implementation: 5 automated_full + 17 automated_partial + 7 manual_release
errors: 0
warnings: 2
```

两条警告是预期且必须保留的事实：

1. 尚无 empirical real-app episode；
2. 尚无 iOS capability 或 episode 记录。

这里的 `pass` 只证明当前 fixture 通过 schema 形状和验证器已编码的断言，不表示 29 个门全部自动通过，也不表示方法已经在真实设备上有效。

## 3. QA 覆盖解释

逐门覆盖记录在 `schema/qa_implementation_coverage.json` 与 `work/qa_coverage_map.md`：

- `automated_full`：5 门；
- `automated_partial`：17 门；
- `manual_release`：7 门。

仍需人工或发布流程执行的门为：

```text
ITEM-005 artifact integrity
ITEM-008 mobile-Web host context
ITEM-019 annotation/adjudication
DATASET-003 cohort-separated reporting
DATASET-004 A-VTR coverage reporting
DATASET-005 stratified/cluster-aware reporting
DATASET-006 release permission/privacy/disposition
```

独立复审指出的过时 schema-gap 描述已修正：GAP-001、002、004 在 provisional contract 中已解决；GAP-003 仍等待 capability pilot；GAP-005 仅部分解决，禁止声称“全门机器验收”。

## 4. Fixture 隔离

`data/items.schema-fixture.jsonl` 的唯一 item 被固定为：

```text
record_kind = synthetic_schema_fixture
split = schema_fixture
eligible_for_training = false
eligible_for_main_metric = false
eligible_for_user_experience_claim = false
```

fixture 中的真值只用于测试三值公式、引用关系、presence/provenance 和跨平台字段容器；不能被摘取为实验结果。

## 5. 可复现性

重新生成 crosswalk 与 fixture 后，前后 SHA-256 完全一致：

| Artifact | SHA-256 |
|---|---|
| `data/items.schema-fixture.jsonl` | `376cc1220aa885145b02b26c2f5f944409c8739da87de706781c1e661058b577` |
| `schema/source_to_item_crosswalk.json` | `bf614319ad52ef2eaf18dd45b10d44c4deffe250eeeb7b85388d9399a0120466` |
| `schema/item.schema.json` | `65d864c32ef0d13c6e0e66bc73e8422024335376bc12cb3f14f344b9c66796e7` |
| `schema/field_catalog.json` | `fa14720141b8d750ed610fdc4683e8ae5741156c85f43227cffa8c07f1763105` |
| `schema/qa_rules.json` | `3f653c094423644b153a949e1c17a8bbddb356e072d0a51ec2ab6103eb9c2120` |
| `schema/qa_implementation_coverage.json` | `c10810dc7e93e5687d85ccec1ea10d20b704b51faa9dd658ae8ea418347df83f` |
| `provenance/paper_method_coverage.json` | `dd6214db88ff2713403b94ae018a49dfcd49405a8a8d7aba49b53527cb5cf47a` |
| `scripts/validate_dataset.py` | `f29ff32da9234a5470fcd2c673ce4a9eec77da9c404e971c8e5398cbe54ae0e4` |

独立审计还对 A-VTR 三值公式、敏感弹窗自主动作、synthetic fixture 经验资格和 split group 泄漏做了负向变异；四类违规均被验证器捕获。

## 6. 下一冻结门

正式采集前仍需：

1. 运行 Android/TalkBack 与 iOS/VoiceOver capability pilot；
2. 根据 pilot 的可观测率、失败率、cluster size 与配对效应方差做功效分析并冻结 `N`；
3. 冻结 group 粒度、split seed、policy、tau/delta 与模型/动作预算；
4. 采集 real-app episode，再执行完整标注、裁决、隐私授权和发布门。

在这些条件完成前，本交付的正确名称是“**collection-ready union contract + synthetic schema fixture**”，不是公开实测 benchmark。
