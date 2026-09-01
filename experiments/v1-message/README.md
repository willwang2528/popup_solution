# v1 Popup Message Evaluation

这是 `popup_message_judgment_v1` 的可复现评测骨架。它只读取冻结 JSONL，输出弹窗存在性与消息指标；**不包含也不调用点击、关闭、坐标、selector、Back 或任务恢复动作**。

当前目录中的 synthetic smoke 数值只证明接口、路由和指标可运行。所有相关 prediction、metrics 与 manifest 均写出：

```json
{
  "evidence_level": "synthetic_pipeline_fixture",
  "paper_result_eligible": false
}
```

它们不能进入论文结果表，也不能支持性能、Recovery 或用户体验主张。

## 方法接口

CLI 的 `--method` 支持：

| 方法 | 行为 |
|---|---|
| `majority` | 仅从显式、互斥的 `--fit-items` 学习 popup prior 和多数消息；预测时不读取评测 item 内容。 |
| `structured` | A1：按遍历顺序拼接整棵 accessibility/UIAutomator/XCUI/DOM 树的可见文本；空结构弃答，不使用 popup ROI/owner oracle，因此保留宿主页面污染弱点。 |
| `the-ok` | A2：固定 The OK Is Not Enough 官方 `b618948` revision 的 Appium 文本规则；只读取 Appium-like 结构通道的 raw element text，显式排除 DOM/protocol 与语义回退。规则未命中时判断 no-popup，缺少 raw text 时弃答。匹配元素的稳定拼接是本研究的 v1 message adaptation。 |
| `visual-adapter` | 读取冻结的 OCR/VLM prediction JSONL；本代码不调用在线模型。 |
| `mg-pu` | Message/Actionability-Gap-Gated perception-uplift router；非空树若出现 `merged/non_actionable/ambiguous/contradictory/stale/...` 仍可调用视觉。 |
| `always-visual` | 每个 item 都调用冻结 visual adapter。 |
| `empty-tree` | 只有无结构节点或无结构消息时调用视觉。 |
| `random-matched` | 用 SHA-256(`seed:item_id`) 的稳定排序随机选择 item，调用数严格匹配 MG-PU。 |

路由只决定使用哪一个**感知 prediction**，不产生 action candidate 或执行动作。

本地 macOS Vision OCR adapter 见 [`ocr/README.md`](./ocr/README.md)。其正式 30 图运行只证明 OCR 管线可执行：全屏 OCR 不能判断 popup presence，因此所有条目均安全弃答；逐图派生文本因隐私风险保持私有，公开仓库只保留无文本聚合摘要。

[`visual/`](./visual/) 定义 B1、C1 与 MG-PU 可共用的 pre-gold visual bank
契约。当前固定参数 Apple Vision 强矩形提议器＋ROI OCR 已生成 30 项冻结启发式 bank：
4 judged、26 abstain；同一固定主机的两次 replay，其 presence 决定、ROI 和消息一致。
这不证明跨 OS／设备模型身份可复现，也不把未过 gold 的方法称为 canonical 或 validated
baseline。finalizer 要求 ready/formal-ready 配置状态、预冻结
item→截图 hash commitment、逐项图片 hash、policy ID、模型配置以及 judged
request/response hash 全部一致；缺任一项即整批拒绝。现有 Model-B 预标注仍不能冒充
该 bank。C1-AO 与 C1-BM 分别表示 always-on accuracy-cost control 和总调用预算匹配
control；B2 PopSweeper exact 仍为 NO-GO。

post-gold structure–visual gap sidecar 也不接收孤立占位 hash：finalizer 会重算
完整 message-gold batch、私有 structured-feature bundle、每项 A/B 独立 audit
record 和最终 adjudication row 的 hash，并验证 candidate 引用、A/B 身份分离和
no-popup/complete/missing 等逻辑。当前没有任何真人 gap audit 行，所有 item 仍为
`pending_audit`。

## 人工金标解锁前的冻结

真实 pilot 的结构化输入由 [`features/`](./features/) 生成。原始本地 manifest 中的来源目录标签、source ID 和 archive path 均可能泄漏 `ads/no_ads`，因此 feature adapter 只投影 `pilot_item_id`，按固定本地目录读取 RICO 结构。逐节点文本、resource ID 和 bounds 写入 Git 忽略的私有 JSONL；公开文件只保留 30 items、22 available、8 missing、186 nodes 及 bundle hash。

[`pregold/`](./pregold/) 在人工 A/B 标注和 adjudication 之前冻结 A1 structure-only、A2 The OK、C1-AO、C1-BM 与 MG-PU 的逐项输出。正式运行只接收私有结构特征和经完整 bank 重算投影的 visual prediction，不读取来源标签，不生成 metrics。当前 heuristic-bank 聚合结果为：

- structure-only：15 judged、15 abstain、0 visual call；
- The OK text rule：10 judged（均为 rule no-match）、20 raw-text-missing abstain、0 visual call；
- C1-AO：6 judged、24 abstain、30 visual calls；
- C1-BM：6 judged、24 abstain、28 visual calls；K 取 MG-PU 冻结调用数并按固定 hash 选择；
- MG-PU：6 judged、24 abstain，其中 2 条使用显式 popup scope 内结构；视觉 adapter 被调用 28 次，4 次形成视觉正判断，24 次由 adapter 弃答；
- 所有结果均为 `no_action`、`human_gold_used=false`、`scored=false`、`paper_result_eligible=false`。

旧 Model-B 输出只保留为工作流历史。新的 visual projection 已绑定 protocol、图片
manifest、完整私有 bank、配置与引擎哈希，工程上只作为冻结的固定阈值启发式
adaptation；但没有真人 gold，因此仍不能支持 accuracy 或性能比较。C1-BM 只匹配
视觉调用成本，不匹配 item 集合或难度；未来比较必须同时披露它与 MG-PU 的视觉
检查集合重叠。

30-item pending-union 现保留稳定的 `identity.pilot_item_id`，因此最终人工
gold、私有结构候选和预金标预测可以在不依赖显示顺序的前提下连接。
The OK adapter 同时支持预金标 `candidate.features.text` 与 union
`candidate.android_raw.text`，避免 schema 物化后 A2 因字段迁移而全体弃答。

## 输入

`--items` 支持两种冻结 JSONL：

1. `dataset-v1/schema/item.schema.json` 的 v1 union item；
2. `dataset-v1/annotation-pilot/manifests/pilot_batch_30.jsonl` 的 pilot manifest。

非 synthetic 的完整 union item 只有在 presence gold 已通过 `eligible_for_v1_presence_metric=true`、无 exclusion reason、至少一个非空证据 URI，并且 presence 标签有 human-role、`adjudicated`、带裁决者与非空证据 URI 的 annotation 时才进入 presence 指标。message 是独立条件分母：只有 `message_text_observability=complete` 且 `eligible_for_v1_message_metric=true` 的正样本还需 message/critical-facts 人工裁决并进入 message 指标。`partial`、`not_observable` 不会删除同一 item 的 presence 证据。model/source label 即使伪装成 `real_app` 也会被排除。

若提供 `--annotations`，CLI 会先执行整批 finalization：人工输出必须与输入
item 构成严格的一对一 `pilot_item_id` 双射，重复、未知、缺失或空白行均
fail-closed。`cannot_resolve` 行必须不携带任何 final label，保留 exclusion
reason，不进入指标。规范化后的私有 gold 行按 ID 排序并生成
`adjudication_batch.batch_sha256`；公开 run manifest 只记录计数和哈希，不写
人工消息内容。连接不会使用显示顺序、文件名或 `source_sampling_label`。

评测适配器会在接纳 gold 前逐字段检查冻结协议／批次、匿名 adjudicator、ISO-8601 裁决时间、语义槽约束与 `evidence_rechecked_via_adapter=true`；缺字段、额外字段或证据未复核均 fail-closed。

`--predictions` 可使用：

- 带 `message_judgment.prediction` 的完整 union item JSONL；或
- 以 `pilot_item_id`（优先）或 `item_id` 为键的扁平冻结 prediction JSONL。

扁平 prediction 最小字段：

```json
{
  "pilot_item_id": "PMJ-PILOT-001",
  "status": "judged",
  "popup_present_pred": true,
  "message_text_pred": "Example message",
  "critical_facts_pred": [],
  "confidence": 0.8,
  "source_observation_id": "obs.before"
}
```

正式 pilot 评分不得在看到 gold 后重新运行 A1/A2/MG-PU。使用：

```bash
../.venv/bin/python3 experiments/v1-message/run_eval.py \
  --items dataset-v1/empirical-pilot/private/pilot-30.pending-union.private.jsonl \
  --annotations /private/path/final-adjudication.jsonl \
  --predictions experiments/v1-message/pregold/private/pilot-30.heuristic-visual-c1.predictions.private.jsonl \
  --method frozen-prediction \
  --frozen-prediction-method-id structured-only-v1 \
  --output-dir /private/path/scored-a1
```

该路径严格检查整批 prediction 覆盖与 `no_action/gold_blind/unscored` 状态，
直接评分冻结行并写出方法 snapshot SHA-256。gold 文本变化不能改变 prediction
hash 或 prediction 内容。

## 语义复核与配对统计

[`schemas/semantic_output_adjudication.schema.json`](./schemas/semantic_output_adjudication.schema.json)
定义方法输出的盲式消息语义复核。每条记录绑定
`(pilot_item_id, method_id, prediction_row_sha256)`；若启用人工 VPMA，则每个
比较方法的所有 eligible positive output 必须完整覆盖，否则拒绝运行，不能把
人工语义判断与字符串 proxy 混在同一比较中。

[`statistics/`](./statistics/) 提供冻结预测后的 exploratory paired scorer：

- 所有方法共用同一 finalized gold batch 与 metric item set；
- strongest/reference baseline 必须由调用者预先显式指定，test 端不自动挑选；
- 私有 group-map 与模型输入隔离，使用 `group_key + content_key` 连通分量；
- 默认 10,000 次、固定 seed、整 cluster 有放回抽样；
- 主统计量是 VPMA overall success 的配对差，`null/abstain` 按失败计；
- 同一 cluster draw 同时重算 coverage、Presence Macro-F1、critical-information recall、critical-hallucination rate 与 visual-call rate；零分母保持 `null`；
- 公开输出不含 item、消息或 source metadata，并永久保持
  `analysis_tier=exploratory_pilot`、`paper_result_eligible=false`。

当前 group-map 为 30 个 singleton cluster，尚不足以证明正式 leakage control；
B1 popup-ROI、B2 exact PopSweeper、C1 共享视觉融合和可复现视觉模型也仍未解锁。因此仓库尚无
正式方法比较数字。

[`popup_eval/formal_item_materializer.py`](./popup_eval/formal_item_materializer.py)
补齐真人 gold 到 formal runner 之间的私有桥接。它复用既有 G1 message-gold
finalizer 与 G2 structure–visual-gap finalizer，要求 source item、G1 final rows、
冻结 structure bundle、每项 G2 A/B audit 和 G2 final rows 全覆盖且 hash 一致；任何
G1 `cannot_resolve/out_of_scope/uncertain/unusable`、G2 对 G1 的实质质疑、活动动作或
Recovery payload 都整批 fail-closed。source 中仅为 union schema 占位的
null／`not_observable` Recovery 容器会在输出投影时删除，不能进入 formal item。

formal source 还必须逐项绑定已终结的 CAP-001 Android 采集证据：
`record_kind=real_app` 本身不够；必须是 `full_device_evidence`、真实设备或 emulator、
隐私复核通过、`AccessibilityService` snapshot、同步差值不超过 3000 ms，并且
capture record、screenshot 与 accessibility snapshot 的 SHA-256 完整一致。历史
PopSweeper/RICO 的 `partial_device_evidence` 即使随后补上真人标签也会整批拒绝。
绑定会保留在 `adjudication_provenance.capture_binding`，正式 runner 会再次校验。

两个 gold hash 均不读取 source item prediction：G1 hash 只覆盖规范化的真人 G1
final rows；G2 hash 只覆盖绑定 G1／structure hash 和两条独立 audit hash 的 G2
final rows。最终 text-bearing item 与 summary 都必须写入 `private/`，权限固定为
`0700/0600` 且禁止覆盖。输出仍是 message-only、`no_action`、未评分、
`paper_result_eligible=false`，可以直接作为 formal K50 runner 的
`--adjudicated-items`，但本身不是实验结果。

```bash
../.venv/bin/python3 experiments/v1-message/popup_eval/formal_item_materializer.py \
  --source-items /ABSOLUTE/private/pending-union.private.jsonl \
  --g1-adjudications /ABSOLUTE/private/g1-final.private.jsonl \
  --structured-features /ABSOLUTE/private/features.private.jsonl \
  --structured-bundle-sha256 <FROZEN_SHA256> \
  --g2-independent-audits /ABSOLUTE/private/g2-a-b.private.jsonl \
  --g2-adjudications /ABSOLUTE/private/g2-final.private.jsonl \
  --output-items /ABSOLUTE/private/formal-items.private.jsonl \
  --output-summary /ABSOLUTE/private/formal-items-summary.private.json \
  --expected-count 30
```

[`pregold/freeze_operating_points.py`](./pregold/freeze_operating_points.py) 现提供
K25/K50/K100 的 pre-gold selected-ID ledger 冻结入口；其 MG-PU severity 排序是
明确的 proposed policy，不是现有 binary gate 或已验证策略，当前也没有生成 formal
ledger。[`popup_eval/formal_k50_runner.py`](./popup_eval/formal_k50_runner.py) 是正式
上游 runner：未来只消费 finalized adjudicated items、两方法冻结预测、逐项语义裁决、
formal group map、budget receipts 与 attestation，递归拒绝 action／Recovery 字段，
并在写出前把 report 交给现有 finalizer 验证。它当前没有读取真实 gold 或生成正式结果。
[`popup_eval/formal_k50.py`](./popup_eval/formal_k50.py) 是主确认端点的 fail-closed
finalizer：它只接受 `mg-pu-k50-v1` 对
`seeded-random-k50-v1`，要求 adjudicated VPMA、formal group map、exact K、共享
10,000 次 cluster bootstrap、相同冻结 hashes，以及逐方法 pixels/tokens/cost
实际预算账本。当前没有真实 finalized item、语义裁决、正式 budget receipt 或 group-map
attestation，因此没有 formal paired report；Holm、BH 与 Pareto 也仍未实现，所以不会产生论文结果。冻结 ledger 与 finalizer
都会重算两种 K 策略的 selected-ID 交集；集合不同时明确输出
`budget_matched_not_item_matched` 及 overlap count/fraction，不能把等 K 误称为
item-matched。

截图消息 gold 本身不能证明结构暴露缺口。独立 sidecar 见
[`STRUCTURE_VISUAL_GAP_AUDIT.md`](../../dataset-v1/annotation-pilot/STRUCTURE_VISUAL_GAP_AUDIT.md)：
它只在 message gold 后比较冻结 structure 与截图消息，绑定两个独立审计记录和
第三人仲裁 hash，且严格禁止读取方法输出。

## 输出与口径

每次运行固定输出：

- `predictions.jsonl`：一 item 一 prediction，无动作字段；
- `metrics.json`：VPMA、presence confusion/precision/recall/F1/Macro-F1、message exact/normalized/token-F1、coverage、visual-call rate、critical-information recall、critical hallucination；
- `run_manifest.json`：method、seed、输入 SHA-256、路由计数、排除项和声明边界。

口径：

- positive item 的 abstain 计为正类 FN，但不冒充 predicted no-popup；negative item 的 abstain 只作为负类 miss；
- message 指标只以 `popup_present_gt=true` 且 `message_text_observability=complete` 的 gold 为分母；`partial`、`not_observable` 和其他不合格项分别计数，仍保留在 presence 指标中；
- 有完整、方法特异的人工语义裁决时 VPMA 可用 `adjudicated`；否则明确写为 `normalized_exact_proxy`；
- `critical_fact_set_proxy` 只检查预测关键事实是否超出 gold 集合，不冒充完整人工 hallucination 审核；
- message 为 `partial` 或 `not_observable` 的正样本其 VPMA 为 `null`，分别报告 `null_message_partial_count` 与 `null_message_unobservable_count`；`null_abstention_count` 只统计实际弃答。同时报告 `vpma.rate_on_covered` 与 `vpma.overall_success_rate`，避免靠大量弃答抬高条件结果。

## 测试

从 `popup-solution/` 目录直接运行，不需要设置 `PYTHONPATH`：

```bash
../.venv/bin/python3 -m unittest discover -s experiments/v1-message/tests -v
```

## Synthetic smoke

以下示例只验证管线：

```bash
../.venv/bin/python3 experiments/v1-message/run_eval.py \
  --items dataset-v1/data/items.schema-fixture.jsonl \
  --method structured \
  --seed 17 \
  --output-dir experiments/v1-message/results/synthetic-smoke/structured
```

视觉方法增加：

```bash
--predictions dataset-v1/data/items.schema-fixture.jsonl
```

多数基线增加互斥 fit fixture：

```bash
--fit-items experiments/v1-message/fixtures/majority-fit.schema-fixture.jsonl
```
