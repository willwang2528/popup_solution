# Popup Episode Union Dataset v1

> 状态：`union-contract-complete / schema-provisional / empirical-data-pending`。90 个论文原子字段与 165 个我方方法字段已全部建立 crosswalk；正式 schema 仍需 Android/iOS capability pilot 后冻结。当前唯一 item 是不进入实验统计的 synthetic schema fixture，没有把虚构值表述为真实设备观测。

## 一句话定义

一个 `item` 是一次完整的移动端弹窗恢复 episode：

```text
原任务状态 → 弹窗触发 → 结构化与视觉观察 → 候选与门控 → 动作执行 → D / C_a11y / T 回证
```

每个 item 同时容纳：

1. PPT 14 篇既有论文实际使用过的结构化、视觉、上下文、动作和弱/强回证字段并集；
2. 我们 `Actionability-Gap-Gated Recovery` 方法新增的 actionability gap、owner、安全策略、按需视觉、abstain 和无障碍恢复字段；
3. Android、iOS、移动 Web 的平台原始字段，以及跨平台规范字段；
4. `presence` 与 `provenance`，用于表达字段不存在、不可观测、不适用、采集失败或人工标注，避免用 `null` 混淆不同原因。

## 文件

- `DATASET_MANIFEST.json`：字段、cohort、item 数、验证状态与 `N` 冻结条件。
- `schema/item.schema.json`：一个 episode item 的 provisional 结构契约。
- `schema/field_catalog.json`：字段来源、类型、阶段、证据等级及必填策略。
- `schema/source_to_item_crosswalk.json`：`90 + 165 = 255` 个源字段到 canonical item JSON Pointer 的无遗漏映射。
- `schema/qa_rules.json`：23 个 item 门、6 个 dataset 门与三值逻辑公式的完整契约。
- `schema/qa_implementation_coverage.json`：逐门记录当前验证器的全自动、部分自动与人工/发布时覆盖范围。
- `data/item.template.json`：采集时复制的全字段模板。
- `data/items.schema-fixture.jsonl`：一个只用于测试 schema 的合成 fixture，不进入训练或评测。
- `provenance/paper_method_coverage.json`：14 篇论文到字段/方法阶段的映射。
- `DATASET_CARD.md`：范围、采样、切分、隐私与发布边界。
- `ANNOTATION_GUIDE.md`：标注和裁决规则。
- `scripts/validate_dataset.py`：零第三方依赖的结构与已实现关键逻辑验证器；其 `pass` 不等于 29 门全部自动通过。
- `scripts/materialize_schema_fixture.py`：生成带完整 presence/provenance 的非实测 fixture。
- `VALIDATION_REPORT.md`：本轮验证结果。

## item 的强制层次

```text
identity
provenance
scenario
environment
assistive_technology
capability_profile
observations[]
candidates[]
decision
action_attempts[]
verification
feedback
observability
annotations[]
quality
```

所有层次必须出现。平台不适用或当前不可观测的字段也保留键，并在局部 `presence` 与 episode 级 `observability.field_status` 中说明原因。

## 统计边界

- `record_kind=synthetic_schema_fixture` 的 item 永远不得进入训练、验证、测试或论文指标。
- 主评测只允许 `record_kind=real_app` 或预注册的 `controlled_fixture`。
- 同一 scenario、App/package、弹窗模板族、CMP/SDK 和近重复视觉不得跨 split。
- 一张截图或一个 frame 不是独立样本；episode 是最小统计单元。
- `A-VTR` 只有在 `D ∧ C_a11y ∧ T` 均有可接受证据时成立；`VTR-tech` 不得替代视障用户恢复结论。

## QA 覆盖边界

当前 29 个契约门中，5 个已完整自动化、17 个部分自动化、7 个必须由独立人工或发布流程检查。验证器的 `pass` 只表示 schema 形状和已编码断言通过；不会证明 artifact 授权、双人标注/裁决、伦理同意、发布分层或 release disposition 已通过。

## 当前不能声称

- 当前 fixture 不是公开实测 benchmark；
- iOS 字段是待 capability probe 验证的工程候选，不代表 VoiceOver 可实际读取全部字段；
- 没有真实设备 episode 与目标用户研究时，不能声称方法改善了视障人士体验；
- 不能把坐标命中、命令送达、截图变化或单独的弹窗消失写成完整任务恢复。
