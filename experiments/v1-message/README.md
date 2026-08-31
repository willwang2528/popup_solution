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
| `structured` | 只拼接 popup scope 内的 accessibility/UIAutomator/XCUI/DOM 等结构化文本；不读取 gold 或视觉候选。 |
| `visual-adapter` | 读取冻结的 OCR/VLM prediction JSONL；本代码不调用在线模型。 |
| `mg-pu` | Message/Actionability-Gap-Gated perception-uplift router；非空树若出现 `merged/non_actionable/ambiguous/contradictory/stale/...` 仍可调用视觉。 |
| `always-visual` | 每个 item 都调用冻结 visual adapter。 |
| `empty-tree` | 只有无结构节点或无结构消息时调用视觉。 |
| `random-matched` | 用 SHA-256(`seed:item_id`) 的稳定排序随机选择 item，调用数严格匹配 MG-PU。 |

路由只决定使用哪一个**感知 prediction**，不产生 action candidate 或执行动作。

本地 macOS Vision OCR adapter 见 [`ocr/README.md`](./ocr/README.md)。其正式 30 图运行只证明 OCR 管线可执行：全屏 OCR 不能判断 popup presence，因此所有条目均安全弃答；逐图派生文本因隐私风险保持私有，公开仓库只保留无文本聚合摘要。

## 人工金标解锁前的冻结

真实 pilot 的结构化输入由 [`features/`](./features/) 生成。原始本地 manifest 中的来源目录标签、source ID 和 archive path 均可能泄漏 `ads/no_ads`，因此 feature adapter 只投影 `pilot_item_id`，按固定本地目录读取 RICO 结构。逐节点文本、resource ID 和 bounds 写入 Git 忽略的私有 JSONL；公开文件只保留 30 items、22 available、8 missing、186 nodes 及 bundle hash。

[`pregold/`](./pregold/) 在人工 A/B 标注和 adjudication 之前冻结 structure-only 与 MG-PU 的逐项输出。正式运行只接收私有结构特征和经隔离 adapter 转换的模型视觉候选，不读取 raw pilot manifest，不生成 metrics。当前聚合结果为：

- structure-only：15 judged、15 abstain、0 visual call；
- MG-PU candidate：30 judged，其中 2 条使用显式 popup scope 内结构，28 条调用冻结视觉候选；
- 所有结果均为 `no_action`、`human_gold_used=false`、`scored=false`、`paper_result_eligible=false`。

这里的 Model-B 输出只用于证明预金标工作流可冻结；因为精确模型身份与执行复现信息不完整，它明确不是正式论文 baseline，也不能支持性能比较。

## 输入

`--items` 支持两种冻结 JSONL：

1. `dataset-v1/schema/item.schema.json` 的 v1 union item；
2. `dataset-v1/annotation-pilot/manifests/pilot_batch_30.jsonl` 的 pilot manifest。

非 synthetic 的完整 union item 只有在 `eligible_for_v1_*_metric=true`、无 exclusion reason、标签至少含一个非空证据 URI，且相应 presence/message/critical-facts 标签都有 human-role、`adjudicated`、带裁决者与非空证据 URI 的 annotation 时才进入指标；model/source label 即使伪装成 `real_app` 也会被排除。

若输入 pilot manifest，必须同时通过 `--annotations` 提供已完成、已 resolved 的 `adjudication_output.schema.json` JSONL。连接键固定为 `pilot_item_id`；不会用显示顺序、文件名或 `source_sampling_label` 冒充人工 gold。待裁决、`uncertain`、`unusable` item 保留 exclusion reason，不进入指标。

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

## 输出与口径

每次运行固定输出：

- `predictions.jsonl`：一 item 一 prediction，无动作字段；
- `metrics.json`：VPMA、presence confusion/precision/recall/F1/Macro-F1、message exact/normalized/token-F1、coverage、visual-call rate、critical-information recall、critical hallucination；
- `run_manifest.json`：method、seed、输入 SHA-256、路由计数、排除项和声明边界。

口径：

- positive item 的 abstain 计为正类 FN，但不冒充 predicted no-popup；negative item 的 abstain 只作为负类 miss；
- message 指标以 popup-positive gold 为分母，弃答不会被 complete-case filtering 隐藏；
- 有完整、方法特异的人工语义裁决时 VPMA 可用 `adjudicated`；否则明确写为 `normalized_exact_proxy`；
- `critical_fact_set_proxy` 只检查预测关键事实是否超出 gold 集合，不冒充完整人工 hallucination 审核；
- 同时报告 `vpma.rate_on_covered` 与 `vpma.overall_success_rate`，避免靠大量弃答抬高条件结果。

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
