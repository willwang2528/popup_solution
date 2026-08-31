# 面向视障人士的弹窗恢复数据集 Schema（草案）

> 状态：`provisional`。严格文献并集只覆盖 Android 与移动 Web；iOS 字段为待真实采集验证的工程候选。

## 1. 数据单元

不要把“item”同时用来指论文、字段、控件和样本。本文统一使用：

- `scenario`：一个任务、受阻步骤、弹窗触发条件与预期后置条件。
- `episode`：从触发到执行与回证的一次完整运行，是主评测单元。
- `observation`：episode 中某一时刻的截图、结构化表示和 owner/context。
- `element_item`：一个结构化或视觉候选元素。
- `action_attempt`：一次候选动作及其执行记录。
- `outcome`：弹窗、上下文、原目标和任务后置条件的结果。
- `annotation`：人工真值、置信度、分歧与裁决证据。

一张截图不是独立 episode；同一 episode 的所有帧、树、动作和回证必须进入同一 split。

## 2. 为什么不能做“所有字段并成一个大表”

Android View/Compose、iOS XCUI、Web DOM 与视觉候选无法无损统一。数据应同时保存：

1. **平台原始层**：`android_raw`、`ios_raw`、`dom_raw`、`visual_raw`；
2. **公共规范层**：只表达跨平台可比较的 owner、语义、动作能力、状态、几何与任务上下文；
3. **presence mask 与 provenance**：说明字段是否存在、从哪个通道获得、是否由人工补标。

公共层的规范对象不是简单的 `button` 或 `text`，而是：

```text
owner + semantic role + accessible name
+ action capability + state + geometry + task context
```

## 3. 实体定义

### 3.1 `scenario`

```yaml
scenario_id:
target_population: blind_and_low_vision
task_goal:
blocked_step:
trigger_action:
blocked_target_gt:
task_postcondition_gt:
scope_label: ordinary_low_risk_popup
allowed_action_set_gt: []
abstain_allowed_gt:
fixture_or_real_app:
```

### 3.2 `episode`

```yaml
episode_id:
scenario_id:
method_id:
seed:
platform: android | ios | mobile_web
os_version:
oem_or_device:
app_or_package:
app_version:
ui_framework:
locale:
theme:
orientation:
font_scale:
assistive_technology:
assistive_technology_config:
screen_reader_focus_order_uri:
screen_reader_utterance_trace_uri:
driver_and_adapter_version:
started_at:
ended_at:
```

### 3.3 `observation`

```yaml
observation_id:
episode_id:
phase: before | popup | after | relaunch
timestamp:
screenshot_uri:
tree_uri:
foreground_owner:
window_or_context:
tree_screenshot_sync_status:
popup_present_gt:
popup_bbox_gt:
```

### 3.4 `element_item`

```yaml
item_id:
observation_id:
platform:
source_channel: protocol | accessibility | uiautomator | xcui | dom | ocr | detector | vlm
owner_type:
package_or_bundle:
window_or_context:
role_or_class:
name_or_text:
value_or_hint:
resource_or_accessibility_id:
clickable:
enabled:
hittable:
visible:
focusable:
checkable:
checked_or_toggle:
selected:
bounds_normalized:
z_or_layer:
sibling_index:
tree_depth:
parent_id:
supported_actions: []
field_presence_mask: {}
field_provenance: {}
action_semantics_gt:
is_valid_close_target_gt:
exposure_status_gt:
matched_visual_region_id:
android_raw: {}
ios_raw: {}
dom_raw: {}
visual_raw: {}
```

### 3.5 `action_attempt`

```yaml
attempt_id:
episode_id:
observation_id:
attempt_index:
action_semantics_pred:
target_item_id_pred:
execution_channel:
locator_or_coordinate:
confidence:
rationale_trace:
command_delivered:
execution_error:
latency_ms:
```

### 3.6 `outcome`

```yaml
episode_id:
visual_popup_gone:
semantic_popup_gone:
owner_context_restored:
blocked_target_operable:
screen_reader_focus_before:
screen_reader_focus_after:
focus_restored_to_blocked_target_or_successor:
utterance_before:
utterance_after:
spoken_context_consistent:
task_postcondition_satisfied:
side_effect_detected:
cross_app_jump:
abstained:
handoff_reason:
verified_technical_task_recovery:
accessible_verified_task_recovery:
evidence_uris: []
```

其中：

```text
verified_technical_task_recovery = D ∧ C_tech ∧ T
accessible_verified_task_recovery = D ∧ C_a11y ∧ T
D = visual_popup_gone ∧ semantic_popup_gone
C_tech = owner_context_restored ∧ blocked_target_operable
C_a11y = C_tech
         ∧ focus_restored_to_blocked_target_or_successor
         ∧ spoken_context_consistent（若平台可观测）
T = task_postcondition_satisfied
```

### 3.7 `annotation`

```yaml
annotation_id:
target_entity_type:
target_entity_id:
annotator_id_pseudonymous:
label_name:
label_value:
confidence:
evidence_uri:
adjudication_status:
adjudicator_id_pseudonymous:
```

## 4. 文献字段并集与来源

严格纳入论文及三阶段边界见 [`COLLECTION_SUMMARY.json`](./data-collection/COLLECTION_SUMMARY.json) 与 [`papers.jsonl`](./data-collection/papers.jsonl)。

| 工作 | 可复用的观察／动作／回证字段 |
|---|---|
| Cookieverse / BannerClick | DOM tag、text、visible、父子路径、`z-index`、`position=fixed`、viewport、iframe、button/input/div、Accept/Reject/Settings、交互前后截图 |
| TCF A(A)ID | package/app、CMP ID、`text`、`content-description`、button/toggle、滚动、目标语义、SharedPreferences、`IABTCF_*` 持久化值 |
| POKER | screenshot、popup bbox、YOLO 类别/置信度、遮罩比例、候选 bbox、XML clickable、GUI tree/text/position、触发动作、界面转移、clicked component、package、OCR |
| HotMobile 2018 | `resource_id`、`content_description`、`text`、class/type、bounds/size/position/z、children、Activity、host package、状态图、Back 后目标状态 |
| Abandon All Hope | 原生 View/WebView 来源、关键词、checkbox、Accept/Reject 候选、动作后重启、dialog 是否仍存在、数据行为 |
| VLM-Fuzz | class、text、clickable、scrollable、sibling index、widget ID/placeholder、Activity、UI tree diff、layout bbox、host state、action sequence、transition/replay |

本独立仓库不复制论文全文和上游筛选缓存；可公开审计的派生证据集中在：

- [`papers.jsonl`](./data-collection/papers.jsonl)
- [`FIELD_UNION.md`](./data-collection/FIELD_UNION.md)
- [`paper_method_coverage.json`](./dataset-v1/provenance/paper_method_coverage.json)

## 5. iOS 字段的证据状态

严格 6 篇中没有 iOS 闭环工作。WhisperTest 虽在 iOS 真机读取可访问性／OCR 并执行动作，但其回证只证明 syslog 或画面变化，没有证明弹窗解除，因此不能把其字段写成“严格 6 篇实验并集”。证据等级与边界记录见 [`papers.jsonl`](./data-collection/papers.jsonl) 与 [`FIELD_UNION.md`](./data-collection/FIELD_UNION.md)。

以下仅作为待验证工程候选：

```text
element_type / role
label / name
identifier / accessibility_identifier
value / toggle state
frame / bounds
enabled / visible / exists / hittable
parent / path / index
active bundle_id / SpringBoard / system-alert marker
supported action / target semantics
```

冻结 iOS schema 前必须：

1. 在目标 iOS 版本和设备上真实采集；
2. 区分 XCTest/Appium page source 与 VoiceOver 用户实际焦点、朗读和操作体验；
3. 至少完成真实 `D ∧ C_tech ∧ T` 技术闭环；若要声称改善视障用户体验，还需完成 `D ∧ C_a11y ∧ T`；
4. 明确哪些字段只存在于测试框架，不能作为量产辅助能力声明。

## 6. 暴露缺口标签

```text
complete
not_separately_exposed
merged_confirmed
missing_confirmed
ambiguous
non_actionable
owner_mismatch
filtered_confirmed
developer_defect_confirmed
tool_failure
unknown
```

黑盒观察到“树中没有独立节点”时，只能标 `not_separately_exposed`。只有具备可控 fixture、源码或平台参考树，才能标 `merged_confirmed`、`filtered_confirmed` 或 `developer_defect_confirmed`。

## 7. 分层随机化 × N

### 主分层

```text
platform × owner × popup_kind × exposure_tier × action_topology
```

- `platform`：Android、iOS；移动 Web 可作为扩展层单独报告。
- `owner`：app、system、browser/webview；高风险安全 owner 排除或仅用于 abstain 测试。
- `popup_kind`：onboarding、ad、update、error、consent notice、ordinary alert 等低风险类型。
- `exposure_tier`：完整暴露、部分/合并暴露、无可操作节点。
- `action_topology`：单步关闭、多步骤低风险退出、Back/outside tap、无安全自动动作。

### 受控随机因素

- 方法执行顺序；
- 异步出现延迟；
- locale；
- light/dark theme；
- orientation；
- font scale；
- fixture 中的按钮顺序与视觉样式。

只组合平台上真实可出现的 cell。主测试集优先使用真实平台行为；人工树腐蚀和合成遮挡只进入压力测试。

### N 与重复

- 先用 pilot 估计方差，再做功效分析；不预设拍脑袋的 N。
- 每个 scenario 对全部方法做配对运行，每次恢复相同设备快照、App 数据、权限和同意状态。
- 确定性方法也需多次冷启动以覆盖异步出现；VLM 固定模型、提示、温度与公开 seed。
- 以 app/scenario 聚类计算置信区间，不能把多帧当作独立样本。

### Split 防泄漏

按以下 group 隔离训练、验证和测试：

- package/app；
- UI framework；
- CMP/SDK；
- popup template family；
- OS version。

加入“没有弹窗但视觉上像弹窗”的负样本，测量 False Intervention。

## 8. 标注协议

- 至少双人独立标注，分歧由第三人裁决。
- 标注“可接受动作集合”，而非强制唯一答案；任务上下文决定首选动作。
- 单独记录 `abstain` 是否可接受。
- categorical labels 报告一致性；bbox 报告 IoU/中心偏差；动作与结果以设备回证为主。
- 人工标注者不能仅凭树缺失猜测系统合并、过滤或开发者缺陷。
- 若声称改善盲人或低视力用户体验，必须另做目标用户参与的可访问性研究；人工标注数据集不能替代用户研究。

## 9. 主评测端点

```text
Detection precision / recall
Valid-close-item recall
Valid-action accuracy
Real dismissal success
Owner/context recovery
Blocked-target recovery
Task postcondition success
Technical Verified Task Recovery (D ∧ C_tech ∧ T)
Accessible Verified Task Recovery (D ∧ C_a11y ∧ T)
Screen-reader focus restoration
Spoken-context consistency
Extra navigation steps after dismissal
Task abandonment by target users
False Intervention
Harmful Action
Side-effect / cross-app-jump rate
Abstention / coverage
Attempts / latency
Visual fallback invocation rate
Structured+visual incremental gain
```

所有指标按平台、App、缺口类型和弹窗类型分组报告，并给出聚类置信区间。

## 10. 公开发布前检查

- 截图和树文本脱敏，禁止真实通知、联系人、照片、支付、认证和账号数据进入公开集。
- 核对 App 内容、图标、截图和论文衍生数据的再分发权利。
- 发布数据卡、采集版本、字段 provenance、标注协议、已知缺口和删除请求流程。
- 在真实公开链接、许可证和下载回证完成前，只能写“计划公开”，不能写“公开数据集”。
