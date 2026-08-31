# Refinement Report

**Problem**：无障碍辅助技术场景下，结构化可访问性表示不完整或不一致时的移动弹窗恢复
**Initial approach**：结构化 UI＋视觉兜底；基于既有文献字段并集构建人工数据集并随机化 × N
**Date**：2026-08-31
**External review rounds**：0
**Local provisional score**：7.1 / 10
**Verdict**：REVISE / PROVISIONAL

## Problem Anchor

> 移动端设备在无障碍模式下，读取可访问性树时，无法100%消除弹窗问题，导致体验受到极大影响。

操作化后，研究目标是：在普通低风险弹窗造成结构化可访问性信息缺失、合并、歧义或不可执行时，通过缺口门控按需调用视觉，提高 `D ∧ C ∧ T` 意义下的 Verified Task Recovery，同时控制误干预、错误动作与延迟。

## 主要收紧结果

1. 将“无法 100%”改成可测的 tree-only residual failure rate。
2. 将“结构化＋视觉”改成唯一主机制 **Actionability-Gap-Gated Recovery**。
3. 将样本单位从截图改成完整 popup episode。
4. 将宽表并集改成“平台原始层＋公共规范层＋presence mask＋provenance”。
5. 将成功条件冻结为 `D ∧ C ∧ T`，不再以坐标命中、命令发送或画面变化替代任务恢复。
6. 将三个“第一个”降级为待查新、待发布、待实验验证的候选主张。
7. 明确严格 6 篇没有 iOS，跨平台已验证主张需过独立 iOS gate。
8. 明确没有目标用户研究时，不能声称已改善盲人或低视力用户体验。

## Output Files

- 用户入口：[`../RESEARCH_BRIEF.md`](../RESEARCH_BRIEF.md)
- 数据 schema：[`../DATASET_SCHEMA.md`](../DATASET_SCHEMA.md)
- 初版完整 Proposal：[`round-0-initial-proposal.md`](./round-0-initial-proposal.md)
- 当前最佳 Proposal：[`FINAL_PROPOSAL.md`](./FINAL_PROPOSAL.md)
- 本地同家族预审：[`PROVISIONAL_LOCAL_REVIEW.md`](./PROVISIONAL_LOCAL_REVIEW.md)
- 恢复状态：[`REFINE_STATE.json`](./REFINE_STATE.json)

## Review Status

```yaml
review_independence: same-family
acceptance_status: provisional
external_disclosure: not_sent
```

`research-refine` 的正式 cross-family acceptance 需要真实 Claude MCP 调用和完整 trace。项目当前的自动外部披露授权只覆盖 ProbeBeforeReuse，不覆盖弹窗研究，因此本轮没有外发材料，也没有把 Codex 预审包装成跨模型验收。

## Remaining Weaknesses

- iOS 的结构读取、动作执行和任务后置条件回证尚未在目标场景跑通。
- 目标用户的真实恢复时间、错误率和任务放弃没有直接证据。
- 还未验证门控是否能稳定识别非空结构缺口并优于 always-on vision。
- 公共数据集仍需完成截图/UI 树版权、隐私、脱敏和许可证检查。
- 精确新颖性主张仍需在当前边界下做系统查新。

## Next Steps

1. 先做小规模 Android+iOS feasibility pilot，冻结采集能力与 VTR oracle。
2. 从真实 episode 估计 tree-only residual failure 和缺口分布。
3. 比较 tree-only、vision-only、always-on fusion 与 gated recovery。
4. pilot 通过后再做功效分析、正式 N 与公开发布计划。
5. 如用户授权向外部 Claude 披露本次弹窗研究材料，再继续同一 `research-refine` 状态完成 cross-family review。
