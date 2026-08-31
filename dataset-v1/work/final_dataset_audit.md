# Popup Episode Union Dataset v1 最终复审

> 日期：2026-08-31
> 审阅方式：只读检查正式 schema、字段账本、crosswalk、QA、fixture、manifest 与文档；验证器在 `/tmp` 副本中运行，未修改项目内验证结果或数据。
> 结论：**union contract 已完成；schema 尚不能冻结；empirical dataset 尚未产生。**

## 1. 三层验收结论

| 层次 | 结论 | 依据 |
|---|---|---|
| 字段并集与 episode contract | **通过** | 90 个论文原子字段、165 个我方方法字段，共 255 个唯一 source field；255/255 均有非空 canonical pointer，且指针存在于 `item.schema.json`。 |
| Schema 冻结 | **不通过，保持 provisional** | Android/iOS capability pilot 尚未完成；没有 iOS episode；活动 QA 文件仍保留已过时的 5 个未解决 gap；dependency-free validator 没有执行全部 23/6 门。 |
| Empirical dataset | **未产生** | 当前仅 1 条 `synthetic_schema_fixture`，真实 App、controlled fixture、iOS 记录均为 0；fixture 被明确排除训练、指标和用户体验声明。 |

## 2. 实际验证运行

为遵守“只新增本审计文件”，先把 `dataset-v1` 完整复制到临时目录，再使用项目解释器执行同一验证器：

```text
<project>/.venv/bin/python3
  <temporary-audit-copy>/dataset-v1/scripts/validate_dataset.py
```

实际结果：

```json
{
  "status": "pass",
  "item_count": 1,
  "source_field_counts": {
    "literature": 90,
    "our_method": 165,
    "crosswalk_total": 255
  },
  "qa_contract_counts": {
    "item_gates": 23,
    "dataset_gates": 6
  },
  "errors": [],
  "warnings": [
    "dataset contains no empirical real-app episodes yet",
    "dataset contains no iOS capability or episode record yet"
  ],
  "empirical_status": "pending_real_device_collection"
}
```

该 pass 的准确解释是：**当前 synthetic fixture 通过 schema 形状、presence/provenance、引用关系及已实现的逻辑检查。它不是实测数据通过验收。**

## 3. 90 / 165 / 255 与 crosswalk

独立于验证器计数，直接比对了源字段集合：

- `literature_field_union.json`：90 条、90 个唯一 `field_path`；
- `our_method_fields.json`：165 条、165 个唯一 `field_path`；
- `source_to_item_crosswalk.json`：90 条 `literature_14` ＋ 165 条 `our_method`，共 255 条；
- literature 源集合与 crosswalk 集合：无缺项、无多项；
- method 源集合与 crosswalk 集合：无缺项、无多项；
- `field_catalog.json` 的两个集合与两份源提取完全一致；
- crosswalk 有 307 个 pointer 引用，255 条记录均至少有一个 pointer；
- dependency-free validator 对每个 pointer 做 schema existence 检查，未发现无效指针。

因此，“union-contract-complete”在以下限定下成立：

> 255 个来源字段已被完整登记，并映射到单一 episode schema 的 canonical 字段；同义字段可以共享 canonical pointer，一个来源字段也可按预测、真值、执行或回证语义映射到多个 pointer。

它不表示 255 个字段都已在真实设备上可观测，也不表示各平台 raw 字段无损等价。

## 4. 上轮 5 个 gap 的实际状态

### GAP-001：episode-wide observability

**结构上已补齐。** Root 已强制 `observability`，包含 `field_status` 与 `measurement_channel`；验证器遍历 item leaf，要求每个字段具有状态和通道。fixture 的全局/局部 presence-provenance 检查通过。

### GAP-002：255 条显式 crosswalk

**已补齐并通过集合核对。** 90/165 两个源集合均无 unmapped、extra 或 duplicate source key；所有 canonical pointer 均存在。

### GAP-003：capability profile

**结构上已补齐。** Root 已强制 `capability_profile`，覆盖 structured read、action execution、焦点/朗读可观测性、技术/无障碍闭环和 evidence refs。

但能力本身尚未经验验证：当前只有 `verified_fixture`，没有 Android target-device capability 记录，也没有 iOS capability/episode。

### GAP-004：provenance、retry、feedback

**结构上已补齐。** 已加入：

- `raw_capture_hashes`、`collector_and_model_versions`、`episode_evidence_uris`、`evidence_level`；
- `verification.safety.retry_budget/retry_count/retry_exhausted`；
- root `feedback.status/message/handoff_options/delivered`。

fixture 也物化了相应字段，但这些值的 evidence level 是 `synthetic_schema_fixture`，不构成设备证据。

### GAP-005：跨字段与数据集级规则

**部分补齐，尚未达到“全部 QA 门已机器执行”。** 验证器确实实现了：

- duplicate key 与 schema subset；
- observation/candidate/attempt 引用关系；
- global/local presence-provenance；
- Android/iOS/mobile Web raw 通道基础检查；
- ordinary-low-risk 与 sensitive abstain 基础规则；
- gate tau/delta、owner、执行性、安全性、同步条件；
- visual fallback 候选与安全性；
- retry 次数与 budget；
- D/C_tech/C_a11y/T、VTR-tech、A-VTR 三值推导；
- synthetic/paper/controlled fixture 的基础隔离；
- split group overlap。

但主程序对 `schema/qa_rules.json` 只核对“23 个 item gate、6 个 dataset gate”的数量，并没有逐门解释和执行。至少以下活动 QA 要求尚未完整机器化：

- eligible empirical item 的 artifact 可解析性、hash、媒体类型、redaction 与权限完整性；
- mobile Web 宿主 OS/浏览器/真实 AT 的完整门；
- 主真值双人标注和分歧裁决；
- target-user claim 的伦理、知情同意、补偿和隐私证据；
- real-app 与 controlled-fixture 报告是否被错误池化；
- A-VTR coverage、分层报告与 release disposition；
- `quality` 各字段的独立重算与回填。

因此当前 validator 应描述为“schema fixture 的结构与关键逻辑 validator”，不能描述为“全部 23/6 QA 门的执行器”。

## 5. 三值公式、安全、fixture 与 split 变异测试

在内存副本上做了四个负向变异，没有写入项目文件：

| 变异 | 预期 | 实际 |
|---|---|---|
| 将 components 均为 true 的 fixture `A_VTR` 改为 false | 发现公式不一致 | **捕获** |
| 将 scope 改为敏感但保留 execute/autonomous attempt | 发现未 abstain/违规动作 | **捕获** |
| 将 synthetic fixture 设为 main-metric eligible | 发现 empirical eligibility 违规 | **捕获** |
| 两个 item 共享 group 但分入 train/test | 发现 group 泄漏 | **捕获** |

三值公式实现符合当前契约：任一已观测 conjunct 为 false 则 false；全部 true 才为 true；其余为 null。C_a11y 不由 C_tech 直接替代，A-VTR 不由 VTR-tech 推断。

split 负测还会拒绝 train/test item 的 null `sdk_or_cmp_group_id`，符合当前 group 完整性要求。

## 6. Synthetic fixture 与“非实测”披露

披露充分且一致：

- `README.md` 首行状态为 `union-contract-complete / schema-provisional / empirical-data-pending`；
- `DATASET_CARD.md` 明确“真实设备数据尚待采集”；
- `DATASET_MANIFEST.json` 记录 real-app=0、controlled-fixture=0、synthetic=1；
- fixture 的 `record_kind`、split、source origin 与 evidence level 均为 synthetic/schema fixture；
- 三个 eligibility 全为 false；
- quality notes 明确所有观测为 synthetic，禁止进入 train/validation/test 和指标；
- validator 输出两个 warnings 和 `pending_real_device_collection`。

fixture 中的 `VTR_tech=true`、`A_VTR=true` 只是用于测试公式与 schema；因为 eligibility 均为 false，不是实验结果。对外展示时应始终同时展示 record kind 与 eligibility，避免截取指标字段造成误解。

## 7. 阻断 schema 冻结的问题

### B1. 活动 QA 文件仍保留过时 gap 声明

`schema/qa_rules.json` 的 `known_schema_gaps` 仍把 GAP-001 至 GAP-005 写成未解决，其中 GAP-002 甚至仍称“没有显式 crosswalk”。这与当前 schema 和 README 的完成状态直接冲突；同一文件还把这些标为 `blocker_before_schema_freeze` 等严重级别。

在更新为 `resolved/partially_resolved`、附证据并保留实际剩余项之前，QA contract 自身仍声明 schema 不可冻结。

### B2. 23/6 是契约数量，不是全部执行覆盖率

验证器 pass 只证明已编码子集通过。若发布材料把 `qa_contract_counts: 23/6` 表述为“29 门全部执行通过”，属于过强声明。冻结前要么补齐逐门执行及 per-gate result，要么明确列出 automated/manual/release-time gate 状态。

### B3. Capability pilot 尚未发生

schema 版本仍是 `1.0.0-provisional`，README、Dataset Card 和 manifest 都要求 capability pilot 后冻结；当前没有 iOS capability/episode，也没有 real-device Android/TalkBack 闭环记录。因此 schema 只能作为采集候选，不能宣告 Android/iOS 字段能力已冻结。

### B4. README 引用的验证报告不存在

README 列出 `VALIDATION_REPORT.md`，当前目录只有 `validation-result.json`，没有该 Markdown 文件。这不影响本次机器 pass，但会阻断按 README 清单完成的可审计交付。

## 8. 最终判定

### Union contract 是否完成？

**是，按“来源字段完整登记＋canonical pointer 存在”的定义完成。** 90/165/255 计数、唯一性、源集合一致性及 pointer existence 均已核对通过。

### Schema 是否可以冻结？

**否。** 当前应继续标为 `schema-provisional`。最小冻结前置项：

1. 更新活动 QA 的 5 个 gap 状态；
2. 明确 23/6 门的 automated/manual 覆盖并生成逐门结果；
3. 完成目标 Android/TalkBack 与 iOS/VoiceOver capability pilot；
4. 解决 README 中缺失的验证报告或修正文档清单；
5. 依据 pilot 冻结 schema、N、group 粒度、split seed、policy 与 calibration 版本。

### Empirical dataset 是否已经产生？

**否。** 当前只有一个不可训练、不可评测的 synthetic schema fixture。没有真实设备 episode、真实 App cohort、iOS record、样本规模、经验指标或目标用户结果。

## 修复后复核

> 复核日期：2026-08-31
> 本节仅复核指定的四项修复；此前结论中 capability pilot 未完成、schema 仍为 provisional、empirical dataset 未产生，均不变。

| 复核项 | 判定 | 证据 |
|---|---|---|
| `known_schema_gaps` 不再过时 | **PASS** | GAP-001、GAP-002、GAP-004 已标为 provisional/union-contract 层面的 resolved；GAP-003 准确保留 capability pilot 待验证；GAP-005 准确标为 partially resolved，并指向仍需人工或发布期检查的范围。 |
| `qa_implementation_coverage` 完整覆盖 29 门 | **PASS** | QA contract 为 23 个 item gate＋6 个 dataset gate，共 29 个唯一 ID；覆盖表为 5 `automated_full`＋17 `automated_partial`＋7 `manual_release`，共 29 个唯一 ID；与 contract 集合完全相等，无重复、遗漏或额外 ID。 |
| Validator 区分 contract count 与实施覆盖 | **PASS** | 使用项目解释器在临时副本实跑得到 `status: pass`；输出分别给出 `qa_contract_counts: 23/6`、`qa_implementation_coverage: 5/17/7/29`，并明确 `validation_scope: schema_shape_and_documented_automated_assertions_only`。 |
| `VALIDATION_REPORT.md` 存在且不误写 fixture | **PASS** | 文件已存在；报告明确写明 empirical dataset 未产生、唯一记录为不可训练且不可评测的 synthetic schema fixture，并声明 validator pass 不代表真实设备有效或 29 门全部自动通过。 |

**本轮四项修复总判定：PASS。** 原 B1、B2、B4 已修复；这不构成 schema freeze 或 empirical dataset 完成的判定。
