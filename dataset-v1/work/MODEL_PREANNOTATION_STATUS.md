# Pilot 30 model preannotation status

本页只记录两个独立模型对冻结 30 图的工作流预标注状态。它们用于检查标注协议是否可执行、定位需要人工裁决的困难项；**不是人工 gold，不进入 κ、VPMA、方法对比或论文结果**。

## 输入与盲法

- A、B 分别按独立模板顺序逐图查看本地 adapter 截图。
- 两者均未读取 coordinator manifest、`source_sampling_label`、对方输出、OCR 输出或任何 gold 字段。
- 原始截图未复制进 JSONL 或仓库；每条均标记 `not_human_gold=true`、`metric_eligible=false`。

## 描述性结果

| 预标注 | popup | no_popup | uncertain | unusable |
|---|---:|---:|---:|---:|
| Model A | 19 | 10 | 1 | 0 |
| Model B | 19 | 11 | 0 | 0 |

两份输出在 presence label 上有 29/30 条相同。唯一不同项为 `PMJ-PILOT-020`：A=`uncertain`，B=`no_popup`。这只是模型间描述性一致，不是人工标注者一致性，也不能据此决定最终标签。

## 后续处理

人工 A/B 必须继续按 blind protocol 独立标注，不能看到这些模型输出。只有真实人工完成、协议一致性计算和 evidence-rechecked adjudication 后，记录才可能成为后续评测 gold。

对应文件：

- `model-preannotation-a.jsonl`
- `model-preannotation-a-summary.md`
- `model-preannotation-b.jsonl`
- `model-preannotation-b-summary.md`
