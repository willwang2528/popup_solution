# Round 1 Review：PPT 第 14 页纠偏后的本地严格审阅

> Date：2026-09-01
>
> Review independence：same-family
>
> Acceptance status：provisional
>
> CALIBRATION：none

## External reviewer status

已调用 `mcp__claude_review__review_start`，但主机拒绝将本弹窗课题的 proposal、method spec 和 PPT evidence 发送给外部 Claude。当前长期披露授权只覆盖 ProbeBeforeReuse，不覆盖 popup-solution。本轮没有重试、绕过或改用其他外部模型。

失败轨迹：`.aris/traces/research-refine/2026-09-01_run01/`（项目本地，不进入公开仓库）。

因此本文件不能构成 cross-family acceptance。

## Weighted scores

| Axis | Weight | Score | Evidence |
|---|---:|---:|---|
| Problem Fidelity | 0.15 | 9.5 | 已明确承认不可观测边界、非统一化和 V1 no-action |
| Method Specificity | 0.25 | 8.0 | gate、输入输出、冲突与 abstain 可实现；模型／threshold 尚未冻结 |
| Contribution Quality | 0.25 | 7.0 | popup-specific benchmark 有潜力；广义“first”被既有工作削弱 |
| Frontier Leverage | 0.15 | 7.0 | frozen VLM/OCR 用于视觉补全合理，但不是新模型 |
| Feasibility | 0.10 | 6.0 | 有可下载 P1 source，但无 adb/emulator/simctl、OCR runtime 和真实 iOS |
| Validation Focus | 0.05 | 8.5 | 主比较、等预算、kill criteria 和五级回证边界清楚 |
| Venue Readiness | 0.05 | 6.5 | 尚无 empirical item、baseline 或结果；用户研究主张受限 |

**Weighted composite：7.6／10**

**Verdict：REVISE**

## GAP

当前 proposal 已接近一个可执行的 benchmark + selective-fusion 研究，而不再是“做一个万能弹窗解决器”。主要差距不是叙事，而是证据：现在只有 schema、source-field union 和 synthetic fixtures，没有一个可进入主指标的真实 item；方法也没有冻结 backbone、prompt、threshold 或等预算结果。Screen Recognition 已覆盖从 pixels 补 accessibility metadata，CHI 2024/2026 已覆盖 screen-reader popup/problem 背景，因此只有 popup-specific 数据、gap taxonomy、VPMA/coverage 和 selective visual gate 的实测组合可能形成贡献。没有这些 empirical artifacts，proposal 仍停留在 7–8 分区间。

## Drift warning

**NONE for current V1 scope.**

需要持续拒绝两类漂移：

1. 把 message-level recovery 扩成自动点击／完整任务恢复；
2. 因“first”风险而退化成纯通用 accessibility metadata generation。

## Simplification opportunities

1. 把 dominant contribution 固定为 PMAB measurement/benchmark；MG-PU 是唯一 supporting method。
2. V1 只保留三类 baseline family，不加入 end-to-end RL、multi-agent voting 或新训练 backbone。
3. Android anchor 先完成；iOS 没有 capability 时分阶段发布，不用 placeholder 数据撑跨平台。

## Modernization opportunities

1. 使用 frozen VLM 做 popup ROI transcription／critical-fact candidate，不训练新视觉模型。
2. 将 gate 评价为 selective prediction／risk–coverage–cost，而不是只报平均准确率。
3. 保留 raw platform fields 和 provenance，不强行把 Android/iOS 压成有损统一 schema。

## Blocking action items

1. 下载并校验 PopSweeper archive，核验 annotation/ID/RICO join。
2. 产生至少 30 个真实 candidate 并完成双人 annotation pilot。
3. 实现 structure-only、OCR-only／visual 和 always-on 三个强 baseline。
4. 冻结 MG-PU 的 exact gate、model、prompt 和 budget。
5. 在 group-disjoint test 上运行预注册主比较。
6. 获得本课题外部 Claude 披露授权后再做 cross-family review；否则永久保持 provisional。
