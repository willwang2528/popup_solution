# Popup Message Union Dataset：v1 数据模型

> 当前 profile：`popup_message_judgment_v1`
> Schema：[`dataset-v1/schema/item.schema.json`](./dataset-v1/schema/item.schema.json)
> 状态：`1.1.0-provisional`；真实设备数据尚未采集

## 1. 单元与分层

一个 v1 item 是一次**动作前、只读**的弹窗消息判断记录，而不是一次恢复 episode：

```text
scenario + frozen observation
→ structured/raw/visual evidence
→ screenshot message gold + independent structure-gap gold + prediction + gate
→ VPMA / component metrics
→ stop, with action_attempts=[]
```

Schema 同时保留两个层次：

- `popup_message_judgment_v1`：当前必需 profile，止于消息判断／弃答；
- advanced compatibility layer：动作、Dismissal、`C_tech`、`C_a11y`、`T`、`VTR-tech`、`A-VTR`，v1 中全部为 `null/not_applicable`。

## 2. 字段并集

来源字段并集保持冻结：

```text
14 篇论文：90 个原子字段
我方既有方法：165 个原子字段
source-field crosswalk：255 条
v1 message profile：单独计数的协议扩展，不冒充新的论文来源字段
```

公共层与原始层并存：

- 公共层：owner/context、role/class、name/text/value/hint、state、geometry、hierarchy、provenance、presence；
- 原始层：`android_raw`、`ios_raw`、`dom_raw`、`visual_raw`；
- 文献兼容层：候选、动作、视觉、弱回证、持久化与状态转换；
- v1 层：`message_judgment`；
- advanced 层：`decision`、`action_attempts`、`verification`。

不要用跨平台规范化值覆盖平台原始字段，也不要把 Appium／XCUI 能读到的内容直接标成 TalkBack／VoiceOver 可达。

原始 Android `bounds/position` 使用非负 pixel coordinates；
`normalized.bounds_normalized` 只在可信 screen/viewport size 可得时填写。不得用
候选最大坐标猜测屏幕大小。

## 3. `message_judgment` 契约

### Labels

```json
{
  "popup_present_gt": true,
  "blocking_gt": true,
  "message_text_gt": "Special offer. Ends today.",
  "critical_facts_gt": ["special offer", "ends today"],
  "message_text_observability": "complete",
  "evidence_uris": []
}
```

- 无弹窗：`blocking_gt=null`、`message_text_gt=null`、`critical_facts_gt=[]`、observability=`not_applicable`。
- 有弹窗且消息可观察：按阅读顺序忠实转录，不翻译、不补写不可见意图。
- `partial/not_observable` 单独报告 coverage，不进入 complete-message 分母。

### Gap ground truth

`gap_ground_truth` 是 message gold 完成后的独立 sidecar：对照冻结 structure 与
screenshot-message gold，记录 `structured_message_complete_gt`、gap reasons、
结构中缺失的 critical facts、host-text contamination 和树—图同步性。两名审计者
及第三位仲裁者必须看不到方法输出；该字段不得回流 pre-gold prediction。pending
item 统一写 `status=pending_audit`，不能由视觉 route 或模型预标注自动填值。
正式 sidecar 必须同时绑定完整 message-gold rows、预冻结 structured bundle、
两个不同 A/B audit record 及其真实 candidate 引用，不能只提交格式合法的占位 hash。

### Prediction

```json
{
  "status": "judged",
  "popup_present_pred": true,
  "message_text_pred": "Special offer. Ends today.",
  "critical_facts_pred": ["special offer", "ends today"],
  "confidence": 0.92,
  "source_observation_id": "obs.popup",
  "evidence_uris": [],
  "model_or_rule_version": "mg-pu-v1",
  "latency_ms": 120
}
```

`abstain` 时 presence、message 与 confidence 为 `null`，不能把弃答算作 no-popup。

### Gate

记录 `structured_message_complete`、message gap、视觉是否调用、调用次数和树—图同步状态。视觉只补消息，不生成／执行动作。

### Evaluation

记录 `presence_correct`、`message_semantically_correct`、`critical_information_recall`、`critical_hallucination` 和 `VPMA`。字符串相似度不能替代人工语义裁决。

### Eligibility

分别标记 presence metric、message metric、advanced recovery metric 和 user-experience claim 资格。synthetic fixture 与 paper reconstruction 永远不能进入经验指标。

## 4. 不变量

- v1 `action_attempts=[]`；
- v1 decision 为 `no_action/abstain`；
- prediction 只能引用动作前 observation；
- 任何 post-action/task-check observation 都是 v1 违规；
- v1 的 D/C/T/VTR 均为 `null`；
- 所有正值真值与预测都需可解析证据；
- presence、provenance、hash、权限、隐私和 split group 必须可审计。

## 5. Split 与随机化

按以下六类 group 防泄漏：scenario、App、popup template、SDK/CMP、OS family、near duplicate。正式实验再按 platform、owner、popup kind、exposure tier、language、message complexity 分层。

同一个 frozen observation 供所有方法配对运行；不得让后运行方法看到 gold 或其他方法输出。`N` 由 pilot 与功效分析冻结。

## 6. 指标

```text
positive popup: VPMA = presence_correct
                       AND message_semantically_correct
                       AND NOT critical_hallucination
no-popup:       VPMA = presence_correct
```

同时报告 presence precision/recall/Macro-F1、message semantics、Exact Match、Character F1、critical-information recall、critical-hallucination rate、coverage/abstention、视觉调用率和延迟。

## 7. 当前实物

- `data/item.template.json`：正样本 v1 模板；
- `scripts/materialize_schema_fixture.py`：生成 positive/no-popup/abstain 三个 synthetic fixture；
- `data/items.schema-fixture.jsonl`：只用于验证 schema，不是经验数据；
- `schema/v1_message_qa_rules.json`：6 个 v1 profile QA gate；
- `scripts/validate_dataset.py`：依赖-free 结构与跨字段验证。

进阶 Recovery 的旧字段保留为未来兼容，不得改变当前 v1 的成功定义。
