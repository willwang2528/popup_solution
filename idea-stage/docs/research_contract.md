# Research Contract: PMAB-Android

> 当前活跃研究合同。它只保留选中的 benchmark 方向；不把淘汰的统一弹窗解决器、Recovery 或跨平台 V1 重新带回主线。

## Selected Idea

- **Description**：构建 PMAB-Android，一个面向移动弹窗消息判断的公开 measurement benchmark。每个正式 item 同步保存 Android screenshot、真实 AccessibilityService representation、公共规范字段、平台原始字段、G1 可见消息 gold、G2 structure-sufficiency audit、预测和成本记录。MG-PU 仅作为在结构消息不足时分配视觉预算的 supporting policy。
- **Source**：`idea-stage/IDEA_REPORT.md`，Idea #1。
- **Selection rationale**：最符合视障人士 popup-message observability 问题锚、255 字段 union 合同和现有可执行实验链；独立 reviewer 允许进入 feasibility。选择不基于正向 pilot，当前正式经验结果为 0。

## Problem and Observability Ceiling

平台没有暴露到 UI／可访问性树的内容，tree-only 方法原则上读不到。若相同内容在屏幕像素中可见，视觉可补充消息转录；若结构、像素和其他获授权观察均未提供该事实，系统必须 `abstain`，不能从不存在的证据中恢复。V1 不承诺统一化，也不解决所有 popup owner、协议或业务语义。

PPT 第 14 页的五级回证只用于定义局限：V1 不执行关闭，不使用节点消失或截图变化证明 Recovery，也不测 owner/context、业务持久化、屏幕阅读器焦点或原任务后置条件。

## Core Claims

1. **Measurement claim（待验证）**：在满足真实同步 capture、G1/G2 agreement 和 release gate 后，PMAB-Android 可测量可见 popup message 与 Android accessibility representation 之间的可观测缺口。
2. **Dataset claim（待验证）**：在正式 item、人工 gold 和公开 readback 完成后，PMAB-Android 可作为公开、可审计的 popup-message benchmark；当前 255 字段 union 只是合同，不是经验数据集。
3. **Method claim（条件式）**：只有 MG-PU 在相同 item、backbone 和预算下显著优于 strongest baseline，且 coverage／hallucination 不恶化时，才能主张 message-sufficiency allocation 的经验收益。

“第一个提出弹窗问题”已被查新反证，不是当前 claim。允许继续查验的更窄 novelty 命题是：是否已有工作公开了“移动 popup-message gold + 结构暴露 gap + 四族同预算评测”的 exact combination。

## Method Summary

MG-PU 先从冻结的 accessibility representation 重建 popup scope、标题、正文和 critical facts。Message Sufficiency Gate 检查缺失、合并、污染、错序、过期、owner mismatch 与跨通道矛盾；只有结构消息不足时才申请同一冻结 screenshot 的 ROI OCR／视觉补全。结构与视觉证据对齐后输出 presence、message、critical facts、confidence 和 evidence；关键事实仍不可观察或互相冲突时弃答。

方法全程 `no_action`。不输出点击坐标，不调用关闭、确认、拒绝、Back、protocol handler 或业务 API。

## Experiment Design

- **Dataset**：正式 PMAB-Android；启动门为至少 100 个真实同步 Android item、5 个 source/app groups、3 个 popup template families，并覆盖正、负、边界样本。先运行 30-item G1/G2 protocol pilot。
- **Splits**：按 App、template family、near-duplicate、SDK/CMP 与 OS family 分组隔离。
- **Baselines**：structure-only、The OK text-rule adaptation、OCR-only、screenshot-only frozen VLM、always-on fusion、empty-tree gate、seeded random-K。
- **Primary metric**：VPMA + coverage；同时报告 presence Macro-F1、critical-fact precision/recall、critical hallucination、视觉调用、像素、tokens、延迟和成本。
- **Main comparison**：MG-PU K50 vs seeded-random K50；`K=ceil(0.50N)`；10,000 次 group bootstrap；同预算但不同 selected item set 时必须报告 overlap 和解释限制。
- **Compute**：优先 CPU／本地 OCR 与冻结外部 backbone；不训练新 VLM。任何新增付费 API 或 GPU 使用仍受实验计划预算门约束。

## Baselines

| Method | Dataset | Metric | Score | Source |
|---|---|---|---|---|
| Structure-only | PMAB-Android | VPMA / coverage / cost | `not_run` | 本项目冻结 baseline |
| OCR-only | PMAB-Android | VPMA / coverage / cost | `not_run` | frozen OCR adapter |
| Screenshot-only VLM | PMAB-Android | VPMA / coverage / cost | `not_run` | frozen backbone pending |
| Always-on fusion | PMAB-Android | VPMA / coverage / cost | `not_run` | matched observation control |
| Empty-tree gate | PMAB-Android | VPMA / visual budget | `not_run` | simple allocation baseline |
| Seeded random-K | PMAB-Android | VPMA / visual budget | `not_run` | budget control |

## Current Results

| Method | Dataset | Metric | Score | Notes |
|---|---|---|---|---|
| All formal methods | PMAB-Android | all paper metrics | `not_run` | real capture=0；human gold=0；paper result=0 |

Synthetic fixtures、PopSweeper/RICO adapter pilot、pre-gold predictions 和工具测试不能填入此表为经验结果。

## Key Decisions

- Android-only V1；iOS 字段只保留兼容层，不作经验外推。
- benchmark 是 dominant contribution；MG-PU 是 supporting policy，不包装成新 backbone。
- G1 screenshot fact gold 与 G2 structure audit 分离；G2 不得改写 G1。
- 先做 B1 strongest-family comparison，再做 B2/K50 allocation isolation。
- null/negative 结果照实报告；不改预算、阈值或样本口径追逐正结果。
- 没有目标用户研究时，不写 UX 改善；没有动作后多级回证时，不写 Recovery。

## Minimum Convincing Evidence

1. 真实同步 Android capture feasibility 通过：≥5 groups、≥3 template families、三类 strata。
2. G1 presence κ 和 message agreement 达到预注册门；G2 agreement 可支持 gap stratification。
3. 真实 gap positives ≥20 且不由单一 group 支配。
4. B1 strong baselines 在冻结 split、同 observation、同 backbone contract 下完成。
5. K50 比较达到 +2pp、CI>0、coverage/hallucination non-worsening 与实际预算门；否则撤销 superiority。
6. privacy、license、EXIF、redaction、clean-clone 和远端 readback 全部通过后才发布经验数据。

## Status

- [x] Idea selected
- [ ] Real Android feasibility capture
- [ ] Human G1/G2 pilot
- [ ] Baseline reproduced on formal data
- [ ] Main method evaluated on formal data
- [ ] Representative dataset results
- [ ] Full dataset results
- [ ] Ablation studies
- [ ] Empirical public release
- [ ] Paper draft
