# 14 篇 PPT 论文的字段并集与方法输入

> 目标人群：使用 TalkBack、VoiceOver 等屏幕阅读器的视障人士。
> 状态：`provisional`；字段来源已限定在现有 PPT、项目内论文原文与本地筛选证据，尚未经过 Android/iOS capability probe。

## 1. 采集结论

- PPT 共列出 14 篇移动端弹窗相关工作。
- 按“发现弹窗—实际执行解除动作—弹窗特异动作后回证”三阶段边界，6 篇可作为 `core_experimental_seed`，其余 8 篇只作 `schema_method_reference`。
- 严格 6 篇覆盖 Android 与移动 Web；没有一篇 iOS 工作满足严格闭环。
- 14 篇工作均未把 TalkBack/VoiceOver 焦点恢复、朗读恢复或视障用户原任务恢复作为主要评测对象。因此这些字段来自本研究问题，而不是文献已经证明有效的字段。

## 2. 统一字段并集

### 2.1 任务、用户与上下文

```text
task_goal
blocked_step
blocked_target
task_postcondition
allowed_action_policy
target_population
assistive_technology + version/config
platform + os/device/oem/app/version/ui_framework
foreground_owner
window_or_context
locale/theme/orientation/font_scale
observation_timestamp
tree_screenshot_sync_status
```

这些字段用于回答“弹窗属于谁、阻断了哪个步骤、允许做什么”。论文常只记录 App、Activity 或页面；视障用户、屏幕阅读器和受阻任务需要本研究补采。

### 2.2 结构化 UI / 可访问性字段

```text
source_channel
owner/package/bundle/host
window/activity/context/iframe
role/class/tag/element_type
name/text/label/content_description/value/hint/placeholder
resource_id/accessibility_id/widget_id
supported_actions
visible/enabled/clickable/hittable/focusable
checkable/checked/selected/scrollable
bounds/frame/position/size/z_index
parent/sibling_index/tree_depth/hierarchy_path
field_presence_mask
field_provenance
raw_platform_node
```

这里不能把 Android `text/content-description/class`、iOS `label/value/elementType` 和 DOM `textContent/tag` 当作同一组原始字段。公共层只表达语义、动作能力、状态、几何、owner 与 provenance；原始层必须完整保留。

### 2.3 视觉字段

```text
screenshot/frame_sequence
popup_roi + popup_bbox
candidate_bbox + tap_coordinate
ocr_text + ocr_bbox
icon_or_control_class
detector_or_vlm_confidence
overlay/dimming/occlusion_ratio
frame_difference/image_hash/histogram_similarity
matched_structured_item_id
model/prompt/version
```

视觉字段用于补全未单独暴露、被合并或语义不足的候选，不直接证明候选属于正确 owner，也不直接证明动作安全。

### 2.4 动作与执行字段

```text
action_semantics
target_candidate_id
selection_strategy
candidate_rank + confidence + margin
gap_reasons
policy_decision
execution_channel
selector_or_coordinate
command_delivered + execution_error
attempt_index + retry_count + latency
abstained + handoff_reason
```

PPT 中出现的动作策略包括：协议语义、确定性多步路径、词表/正则/类型规则、已知类型固定动作、语义相似度、视觉/VLM 判断、遍历/探索。它们需要保留为基线或 provenance，不能合成一个没有来源的标签。

### 2.5 解除与恢复回证字段

```text
visual_popup_gone
semantic_popup_gone
owner_context_restored
blocked_target_visible
blocked_target_operable
screen_reader_focus_before/after
focus_restored_to_blocked_target_or_successor
utterance_before/after
spoken_context_consistent
task_postcondition_satisfied
persistent_state_satisfied
side_effect_detected
cross_app_jump
evidence_uris
```

主回证分解为：

```text
D = visual_popup_gone ∧ semantic_popup_gone
C_a11y = owner/context restored
         ∧ blocked target operable
         ∧ screen-reader focus restored
         ∧ spoken context consistent（若可观测）
T = task postcondition satisfied
A-VTR = D ∧ C_a11y ∧ T
```

若屏幕阅读器焦点不可机器观测，只能报告 `VTR-tech` 及 `A-VTR` 的可观测子集，不能把前者写成视障用户体验恢复。

## 3. 平台原始字段映射

| 公共语义 | Android 原始候选 | iOS 原始候选 | 移动 Web 原始候选 |
|---|---|---|---|
| owner | `package`、window owner | `bundleId`、active application | origin、top frame、iframe src |
| context | Activity、window/type、native/WebView | application/window/alert、native/WebView | document、frame/iframe、CMP |
| role/type | `class`、role | `elementType` / XCUI type | tag、ARIA role |
| accessible name | `text`、`content-description` | `label`、identifier、value | textContent、aria-label、title |
| stable locator | `resource-id`、hierarchy path | identifier、predicate、hierarchy path | id、selector、DOM path |
| actionability | clickable、enabled、focusable、actions | enabled、hittable、traits/actions | visible、enabled、DOM event/action |
| geometry | bounds、size、position、z | frame、normalized rect | DOMRect、viewport、z-index、fixed |
| state | checked、selected、scrollable | value、selected、enabled | checked、selected、expanded、style |
| visual complement | screenshot、OCR、detector bbox | screenshot、OCR、detector bbox | screenshot、OCR、detector bbox |

iOS 列目前是待 capability probe 验证的工程候选。测试框架能读取的 XCUI/Appium page source 不等于 VoiceOver 实际焦点顺序或朗读内容。

## 4. 面向视障人士必须新增的字段

现有 14 篇论文没有系统覆盖以下变量，本数据集必须单独采集：

```text
assistive_technology
screen_reader_focus_before
screen_reader_focus_after
focus_order_trace
utterance_before
utterance_after
focus_restored_to_blocked_target_or_valid_successor
extra_navigation_steps_after_dismissal
unexpected_focus_loss
user_handoff_required
recovery_time
wrong_action
task_abandonment
```

其中焦点、朗读与真实体验指标应区分为：平台可机器观测、测试夹具可观测、真实用户标注。自动化日志不能代替真实视障用户实验。

## 5. 缺口与失败标签

不能从黑盒现象直接断言“系统过滤”或“开发者缺陷”。先记录可观测标签：

```text
separately_exposed
not_separately_exposed
merged
semantic_missing
action_missing
ambiguous
non_actionable
owner_mismatch
stale_or_tool_failure
visual_only
unknown_cause
```

只有在 fixture、参考树、源码或系统文档提供证据后，才能进一步标注 `framework_merge`、`platform_filter_or_limit`、`developer_exposure_defect`。

## 6. 论文到数据集的纳入原则

### Core experimental seed

以下 6 篇可提供弹窗 episode、字段或基线的核心证据：

1. Exploring the Cookieverse / BannerClick；
2. The TCF Doesn't Really A(A)ID；
3. Understanding the Sneaky Patterns of Pop-up Windows in the Mobile Ecosystem / POKER；
4. How Do Mobile Apps Violate the Behavioral Policy of Advertisement Libraries?；
5. Abandon All Hope Ye Who Enter Here；
6. VLM-Fuzz。

它们仍不都具备强回证：Cookieverse 为人工截图核验，POKER 为评估级 dismissed 统计，TCF A(A)ID 偏持久化/重启间接回证。

### Schema / method reference

其余 8 篇可以补充通道、字段、弱基线与失败边界，但不能写成已有端到端闭环：

1. WhisperTest；
2. The OK Is Not Enough；
3. Freely Given Consent?；
4. SSLDetecter；
5. PopSweeper；
6. Dynamic iOS Privacy Analysis；
7. An Approach for iOS Applications' Testing；
8. DiOS。

## 7. PPT 证据质量警告

PPT 第 5 页的示例图存在来源混标：图中 DiOS 旧 UI Automation hierarchy 与现代 XCUITest 示例被放在 “iOS Applications' Testing · 2018” 标注下。该图不进入这篇论文的字段实证；这篇论文当前只保留 PPT 文本与本地筛选记录共同支持的 `UIAElement → center coordinate → tap`，并标为 `local_note_verified`。DiOS 的字段以项目内原文为准。

## 8. 对我们方法的直接约束

1. 门控条件必须检查语义、可执行性、owner/context、置信 margin、安全动作策略和时序一致性；不能只检查“树是否为空”。
2. 视觉只在 actionability gap 出现时补全候选，并与结构化候选一起重新评分。
3. 平台原始字段、presence mask 和 provenance 必须保留，不能声称无损跨平台统一 schema。
4. 自动动作限于低风险退出语义；权限正向授权、支付、身份认证和破坏性动作必须 abstain。
5. 成功必须同时验证弹窗解除、无障碍上下文恢复和原任务后置条件。

逐篇、可机器读取的来源记录见 [`papers.jsonl`](./papers.jsonl)；浏览摘要见 [`papers.csv`](./papers.csv)。
