# Actionability-Gap-Gated Recovery：方法规格 v0.1

> 目标人群：使用 TalkBack、VoiceOver 等屏幕阅读器操作移动设备的视障人士，主要包括盲人和低视力用户。
> 状态：`provisional`；这是可实现规格，不是实验结果或跨模型验收结论。

## 0. 证据输入

- 现有 PPT 的 14 篇论文已逐篇采集到 [`../data-collection/papers.jsonl`](../data-collection/papers.jsonl)。
- 按“发现—真实动作—弹窗特异动作后回证”边界，6 篇进入 core experimental seed，8 篇只作为 schema/method reference。
- 严格 6 篇没有 iOS 闭环；iOS 字段必须经过真实 capability probe 后才能冻结。
- 14 篇均未把 TalkBack/VoiceOver 焦点、朗读和视障用户原任务恢复作为主要评测，因此 `C_a11y` 是本研究必须新增、不能从旧指标替代的回证层。
- 字段并集、平台映射及 PPT 第 5 页来源混标警告见 [`../data-collection/FIELD_UNION.md`](../data-collection/FIELD_UNION.md)。

## 1. 唯一主张

当结构化可访问性表示无法提供**语义明确、可执行、属于正确 owner/context 的低风险退出路径**时，系统才按需调用视觉补全动作候选；成功必须通过面向视障用户上下文的 `D ∧ C_a11y ∧ T` 回证。

方法的贡献不是“结构化 UI＋视觉”，而是：

1. 识别非空但不可操作的 accessibility actionability gap；
2. 用同一个候选评分器决定“直接走结构化动作、调用视觉、还是 abstain”；
3. 把屏幕阅读器焦点恢复纳入任务恢复证书。

## 2. 边界

### 自动处理范围

```text
close
cancel
later
skip
acknowledge
back（仅在已知不会退出原任务时）
outside_tap（仅在已验证语义下）
```

### 必须 abstain / handoff

```text
CAPTCHA / 风控
PIN / 生物识别 / 身份认证
支付 / 安装 / 删除 / 设备管理
隐私或权限的正向授权
语义未知或没有安全退出路径的弹窗
```

## 3. 输入与输出

### 输入

```yaml
task_context:
  goal:
  blocked_step:
  blocked_target:
  allowed_action_policy:
platform_context:
  platform:
  foreground_owner:
  window_or_context:
  assistive_technology:
  screen_reader_focus_before:
structured_observation:
  protocol_event:
  raw_tree:
  normalized_candidates: []
visual_observation:
  screenshot:
  popup_roi:
```

视觉输入默认不进入主路径，只有门控触发后才使用。

### 输出

```yaml
decision:
  action_semantics:
  target_candidate_id:
  execution_channel:
  confidence:
  gap_reasons: []
  visual_fallback_used:
  abstain:
  rationale_trace:
verification:
  dismissal:
  accessible_context_recovery:
  task_postcondition:
  accessible_verified_task_recovery:
```

## 4. 统一候选表示

每个协议、结构化或视觉候选都映射到 `UnifiedActionCandidate`：

```yaml
candidate_id:
source_channel: protocol | accessibility | uiautomator | xcui | dom | ocr | detector | vlm
owner:
window_or_context:
role_or_class:
name_or_text:
value_or_hint:
stable_id:
supported_actions: []
enabled:
clickable:
hittable:
visible:
focusable:
bounds:
hierarchy_path:
field_presence_mask: {}
field_provenance: {}
raw_ref:
```

平台原始字段必须保留；统一候选只是决策层投影，不替代 Android/iOS/DOM 原始结构。

## 5. 系统模块

```text
M1 Observation Collector
        ↓
M2 Platform Normalizer
        ↓
M3 Shared Actionability Scorer / Gate
   ├─ sufficient → structured/protocol candidate
   ├─ gap        → M4 Selective Visual Completer → rescore
   └─ unsafe     → abstain
        ↓
M5 Low-risk Policy + Executor
        ↓
M6 Accessible Recovery Verifier
        ↓
M7 Screen-reader Feedback Adapter
```

只有 M3 是计划训练的新组件。M1、M2、M4、M5、M6、M7 复用平台接口、冻结模型或确定性契约，不分别包装成论文创新点。

### M1 Observation Collector

并行采集：

- protocol/alert event；
- foreground owner、window/context；
- Android UIAutomator/Accessibility 或 iOS XCUI accessibility hierarchy；
- TalkBack/VoiceOver 配置与可获得的焦点状态；
- 时间同步的 screenshot。

若 tree 与 screenshot 时间戳或 UI fingerprint 不一致，标 `stale_or_tool_failure`，不把它归为平台暴露缺陷。

### M2 Platform Normalizer

执行两层映射：

```text
platform raw fields
    → common semantic fields
    + presence mask
    + provenance
```

它不能丢弃平台原始树，也不能把 Android `button/text` 与 iOS `label/type` 强行视为同一原始属性。

### M3 Shared Actionability Scorer / Gate

给任务上下文 (q) 和候选 (c_i)，评分：

\[
s_i=f_\phi(q,\ owner_i,\ semantics_i,\ actions_i,\ state_i,\ geometry_i,\ presence_i,\ provenance_i)
\]

结构化路径充分的必要条件：

```text
max(s_i) ≥ τ
∧ top1 - top2 ≥ δ
∧ owner/context known and consistent
∧ action supported and executable
∧ action belongs to low-risk policy
∧ tree/screenshot not stale
```

任一条件失败即产生 `gap_reasons`，触发视觉或 abstain。

门控必须识别：

- `not_separately_exposed`；
- `merged`；
- `ambiguous`；
- `non_actionable`；
- `owner_mismatch`；
- `stale_or_tool_failure`；
- 多候选低 margin；
- 与安全动作白名单冲突。

若只实现“树为空则调用 VLM”，该方法不满足本规格。

### M4 Selective Visual Completer

仅在门控触发时：

1. 确定 popup ROI；
2. OCR 提取文本与 bbox；
3. detector/VLM 生成候选控件、语义和坐标；
4. 将视觉候选映射回 `UnifiedActionCandidate`；
5. 与结构化候选一起重新评分。

VLM 冻结使用；它只负责候选生成与语义补全，不直接决定敏感动作，也不单独宣告成功。

### M5 Low-risk Policy + Executor

执行通道优先级：

```text
protocol dismiss/cancel callback
> structured element action
> platform watcher action
> grounded coordinate tap
> verified Back/outside tap
```

本研究自动动作策略优先：`close/cancel/later/skip/acknowledge`。正向授权、同意条款、购买和破坏性动作不进入自主执行集合。

### M6 Accessible Recovery Verifier

#### D — Dismissal

```text
visual popup marker gone
∧ semantic popup node/window gone
```

#### C_a11y — Accessible context recovery

```text
owner/context restored
∧ blocked target visible and operable
∧ screen-reader focus restored to the original target or a valid successor
∧ next spoken context is consistent with the resumed task（若平台可观测）
```

#### T — Task postcondition

```text
original task business postcondition satisfied
```

主指标：

\[
\mathrm{A\text{-}VTR}=P(D \land C_{a11y} \land T)
\]

若平台暂时无法机器读取屏幕阅读器焦点，必须同时报告：

- `VTR-tech = D ∧ owner/context restored ∧ target operable ∧ T`；
- `A-VTR` 的可观测子集或真实用户验证结果；
- 不得用 `VTR-tech` 冒充视障用户体验恢复。

### M7 Screen-reader Feedback Adapter

成功后向视障用户提供最小、非打扰式反馈，例如：

```text
“弹窗已关闭，已返回「搜索按钮」。”
```

失败或 abstain 时说明原因和可选人工动作。该模块是产品与实验契约，不是新的训练贡献。

## 6. 训练设置

### 标注

- 正样本：任务条件下可接受的低风险退出动作集合；允许多答案。
- hard negatives：宿主页面控件、广告素材中的伪关闭符号、正向授权按钮、错误 owner 候选、不可执行合并节点。
- abstain：未知语义、高风险动作、owner 不确定或全部候选低置信。

### 损失

\[
L=L_{rank}+\lambda_1L_{abstain}+\lambda_2L_{calibration}
\]

- `L_rank`：同一 episode 内正负候选 pairwise/listwise ranking；
- `L_abstain`：是否应自动执行的二分类损失；
- `L_calibration`：Brier loss 或训练后 temperature scaling，使阈值可解释。

### 训练阶段

1. **Stage 0**：确定性 rule scorer，建立可复现 tree-only baseline。
2. **Stage 1**：只训练结构化候选 scorer，冻结阈值与 calibration protocol。
3. **Stage 2**：加入 gap episode 的视觉候选，但保持 OCR/VLM backbone 冻结。
4. **Stage 3**：在 App、模板、SDK 和 OS 隔离 split 上冻结 τ、δ 与 action policy。

## 7. 推理伪代码

```text
observe task, owner/context, tree, screenshot, screen-reader state
candidates = normalize(protocol + structured candidates)
scores = scorer(task, candidates)

if unsafe_context or no_low_risk_policy:
    return abstain

if structured_is_sufficient(scores, τ, δ, owner, actionability):
    decision = top_structured_candidate
else:
    visual_candidates = visual_complete(popup_roi)
    candidates = merge(candidates, visual_candidates)
    decision = rescore_or_abstain(candidates)

execute(decision)
result = verify_D_Ca11y_T()

if result fails and one preregistered alternative exists:
    reobserve and try once
else if result fails:
    abstain_and_handoff()

announce_result_to_screen_reader()
```

## 8. 核心基线与消融

### 基线

- no handler；
- protocol/watcher；
- tree-only rule/model；
- screenshot-only VLM；
- always-on tree+vision fusion；
- 通用移动 GUI Agent；
- oracle locator/action。

### 必须消融

- no vision；
- always vision / no gate；
- empty-tree-only gate；
- no owner consistency；
- no abstain；
- D-only verification；
- no screen-reader focus check；
- visual-change-only verification。

## 9. 首轮实现顺序

1. 完成 PPT 14 篇论文的字段采集与 evidence matrix。
2. 冻结 `UnifiedActionCandidate` 和 episode schema。
3. 构建 Android/iOS capability probe，验证哪些字段真实可采。
4. 做 rule-based tree-only 与 always-on vision 两个 baseline。
5. 实现 shared scorer/gate。
6. 先跑小规模 feasibility pilot，再决定 N、训练规模和用户研究。

## 10. 停止条件

- tree-only 与本方法 A-VTR/VTR-tech 置信区间重叠且成本更低；
- always-on fusion 等预算下稳定优于门控；
- App/模板隔离后增益消失；
- iOS 无法获得合法的执行与 `C_a11y` 回证路径；
- 屏幕阅读器焦点恢复无法测量且没有真实视障用户评估；
- 出现敏感、破坏性或错误 owner 的自动动作。

任一条件成立时，缩小论文主张或停止对应路线，不用扩大模型掩盖问题。
