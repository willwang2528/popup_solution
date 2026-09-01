# 正式多重比较与质量—覆盖—成本分析

本目录冻结 V1 正式主比较之后的统计口径，防止看到真人 gold 或实验结果后再选择
有利的比较族、分层或成本轴。它只服务于弹窗存在与可见消息判断，不执行点击、关闭、
Recovery 或用户体验评估。

## 冻结注册表

[`FORMAL_ANALYSIS_REGISTRY_V1.json`](./FORMAL_ANALYSIS_REGISTRY_V1.json) 已在真人
gold 为 0、正式结果为 0 时冻结，SHA-256 为：

```text
74b70152c7049b69c798f24128086d6bc66bdb0bfa68dafbb9a51f0a6a634d17
```

注册表逐条绑定方法和 operating point，而不仅是自由文本 ID：

- 唯一主端点仍是 MG-PU 对 seeded random-K 的 K50 paired VPMA，不做多重校正；
- 5 个预命名次级比较组成一个 Holm family，`alpha=0.05`；次级 claim gate 同时要求 Holm 校正后 `p<0.05` 和原始 paired cluster-bootstrap 95% CI 在 effect 方向不跨 0；
- 10 个预命名探索性分层组成一个 BH-FDR family，`q=0.10`；
- 18 个预命名方法／operating-point 组成质量—覆盖—成本点集；
- Pareto 分别以 `visual_calls`、`decoded_pixels` 和
  `monetary_cost_microunits` 为成本轴，同时最大化 VPMA 与 coverage。

若某项少于 5 个独立 App/template groups，输入必须把 `raw_p_value` 置为 `null`；
工具只保留描述性 effect/CI，并把该项按校正输入 `p=1` 处理，禁止显著性或 discovery
主张。这样不会因为删掉低 group-count 项而缩小多重比较 family。

每条 Holm 输出还固定写出
`ci_adjustment_status=unadjusted_per_comparison_cluster_bootstrap_95ci`，禁止未来报告把
原始逐比较 CI 误称为 multiplicity-adjusted CI。

## Fail-closed 后处理器

[`popup_eval/formal_analysis.py`](./popup_eval/formal_analysis.py) 要求注册表 hash、
formal K50 result、次级结果、探索性分层结果与 Pareto 点全部精确覆盖。缺项、重复项、
未知项、方法／operating-point 调包、注册表漂移、活动 Action/Recovery、非法 p 值、
不完整成本轴或非私有路径都会整批拒绝。

```bash
../.venv/bin/python3 experiments/v1-message/popup_eval/formal_analysis.py \
  --analysis-registry experiments/v1-message/private/analysis-registry.private.json \
  --expected-registry-sha256 74b70152c7049b69c798f24128086d6bc66bdb0bfa68dafbb9a51f0a6a634d17 \
  --formal-k50-result experiments/v1-message/private/formal-k50.private.json \
  --secondary-results experiments/v1-message/private/secondary.private.jsonl \
  --subgroup-results experiments/v1-message/private/subgroups.private.jsonl \
  --pareto-points experiments/v1-message/private/pareto.private.jsonl \
  --output experiments/v1-message/private/formal-analysis.private.json
```

输出目录权限为 `0700`、文件为 `0600`，禁止覆盖。receipt 绑定所有输入 hash，但始终
保持 `superiority_claim_authorized=false`、`paper_result_eligible=false`；最终论文主张
仍需真实 CAP-001、真人 G1/G2、冻结预测、实际预算账本和完整发布审计。

## 当前状态

- 注册表：已冻结；
- 实现测试：7/7；
- 真实 secondary/subgroup/Pareto 行：0；
- 正式分析 receipt：0；
- 经验优势或数据集完成主张：不允许。
