# v1 Popup-Message Judgment Contract（最小提案）

> 状态：multi-agent design proposal，随后已实现到 schema 1.1。当前权威契约见 `../README.md`、`../schema/item.schema.json` 与 `../VALIDATION_REPORT_V1_MESSAGE.md`；实现采用 VPMA 为主 item-level 指标，同时保留本提案中的 presence 与字符串分项指标。255 条 source-field crosswalk 保持不变。

## 1. 结论

v1 的主任务应从“执行关闭并证明恢复”降为一个**无动作的弹窗消息判断任务**：给定动作前的移动端观察，判断当前是否存在阻断性弹窗；若存在，输出其可见/可读消息。v1 不自动点击、不声称弹窗已消失，也不声称屏幕阅读器焦点、原页面或原任务已恢复。

建议引入两个 profile：

- `popup_message_judgment_v1`：v1 必需；止于判断或安全 abstain。
- `dismissal_recovery_advanced`：进阶；沿用现有 action、D、C、T、VTR-tech、A-VTR 契约。

论文与报告中的 v1 claim 应写成“popup-message judgment”，不能写成 “recovery”。

## 2. v1 数据单元与边界

一个 v1 item 仍是一个 episode，以保持既有 group、split、provenance 和 `90 + 165 = 255` 字段并集可追溯；但 v1 episode 在**模型产出判断/通知后终止**：

```text
触发或自然到达页面
→ 同步采集动作前截图/结构化表示/屏幕阅读器可观测信号
→ 判断 popup message / no popup / abstain
→ 可选地向用户展示消息
→ 结束（不执行关闭动作）
```

`action_attempts` 必须为空。任何用于生成 v1 prediction 的证据都必须早于人工或自动关闭动作，避免 post-action leakage。

## 3. 最小 item contract

### 3.1 必需公共元数据

复用现有字段，不另造同义字段：

| 语义 | 现有落点 |
|---|---|
| item、record kind、split 与六类 leakage group | `identity` |
| 来源、artifact、hash、权限、隐私与版本 | `provenance` |
| platform、设备/App、locale 与 driver | `environment` |
| TalkBack/VoiceOver 配置与可观测性 | `assistive_technology` |
| 唯一动作前观察 | `observations[]`，`phase=pre_action` |
| 原始截图、tree/DOM、OCR/朗读 | `observations[].artifacts` 及各 raw channel |
| 标注、证据与裁决 | `annotations[]` |
| 缺失原因与测量通道 | `observability` |

v1 不应为了满足旧的完整恢复 schema 而伪造 `blocked_target_gt`、合法关闭动作、D/C/T 或用户恢复结果。

### 3.2 必需 gold labels

建议增加一个 profile-local 对象 `message_judgment.labels`。所有键必须出现，条件不成立时使用 `null`，并在 `observability.field_status` 给出原因。

```json
{
  "popup_present_gt": true,
  "blocking_gt": true,
  "message_text_gt": "Special offer",
  "message_text_observability": "complete"
}
```

字段语义：

- `popup_present_gt: boolean`：当前动作前观察中是否存在独立于宿主内容、会打断或覆盖当前交互上下文的 popup message。它是 v1 唯一无条件主标签，并复用现有 `observations[].popup.present_gt`。
- `blocking_gt: boolean | null`：当 `popup_present_gt=true` 时必填；无 popup 时为 `null`。复用现有 `observations[].popup.blocking_gt`。
- `message_text_gt: string | null`：按阅读顺序拼接的弹窗主体消息原文；不翻译、不补写不可见内容。只有文本可观察时非 null。
- `message_text_observability: complete | partial | not_observable | not_applicable`：有 popup 时说明消息是否完整可见/可读；无 popup 时为 `not_applicable`。

`popup kind`、owner、bbox、action semantics、安全出口、暴露原因可继续保留，但不应成为 v1 主指标的必需标签。它们属于分层分析或 advanced profile。

条件不变量：

```text
popup_present_gt = false
  => blocking_gt = null
  => message_text_gt = null
  => message_text_observability = not_applicable

message_text_gt != null
  => popup_present_gt = true
  => message_text_observability in {complete, partial}
```

### 3.3 必需 prediction

```json
{
  "status": "judged",
  "popup_present_pred": true,
  "message_text_pred": "Special offer",
  "confidence": 0.92,
  "source_observation_id": "obs.popup",
  "model_or_rule_version": "...",
  "latency_ms": 120
}
```

- `status: judged | abstain`。
- `popup_present_pred: boolean | null`：`abstain` 时必须为 null；否则必填。
- `message_text_pred: string | null`：仅在预测存在 popup 且系统确实能读取消息时输出；不得用臆测文本替代不可观测内容。
- `confidence: number | null`：`judged` 时为 `[0,1]`；其定义、校准集和阈值需冻结。
- `source_observation_id`：必须解析到同 item 的动作前 observation。
- `model_or_rule_version`：冻结模型、prompt、规则或其 hash。
- `latency_ms`：从 observation 就绪到 prediction 生成；不含人工标注时间。

用户可见输出可以由 prediction 确定性生成，例如“检测到弹窗：Special offer”或“未检测到弹窗”。该输出是通知，不是恢复成功消息。

## 4. Evidence contract

每个可进入正式指标的 item 至少满足：

1. `popup_present_gt` 有一条或多条动作前 evidence 引用；正样本需圈定 popup 区域或对应结构节点，负样本需提供稳定后的完整屏幕/结构上下文，不能把“单一通道没找到”直接标成 no-popup。
2. `message_text_gt` 的每个文本片段可追溯到 screenshot/OCR、accessibility tree、DOM 或经授权的屏幕阅读器 utterance；多个通道冲突时保留原始值并裁决，不能静默覆盖。
3. evidence 具备 `uri`、`sha256`、`media_type`、`capture_channel`、`redaction_status`、timestamp 与 observation 引用。
4. 正式 validation/test 的语义标签由两名标注者独立完成，分歧在 main-metric eligibility 前裁决；fixture oracle 仅用于 controlled/synthetic fixture。
5. prediction 连同版本、时间戳和 source observation 在解锁 gold label 前持久化。

## 5. v1 metrics

### 5.1 主指标

`Popup Presence Macro-F1`：对 `popup_present_gt ∈ {true,false}` 计算二分类 macro-F1。必须同时报告正类 recall 与 no-popup false-notification rate，避免只靠类别比例得到好结果。

### 5.2 条件消息指标

只在 `popup_present_gt=true` 且 `message_text_observability=complete` 的独立分母上报告：

- `Message Exact Match`：Unicode NFKC、首尾/连续空白归一化后完全一致；不移除否定词、金额、日期或按钮文案。
- `Message Character F1`：用于中英文和 OCR 小误差；不能替代 Exact Match。

`partial` 与 `not_observable` 单独报告 coverage，不进入 complete-text 主分母。

### 5.3 选择性判断与运行成本

- `coverage = judged / eligible_items`；
- `selective_presence_accuracy`：只在 `status=judged` 的 item 上计算，同时给出 coverage；
- `abstention_rate`；
- p50/p95 `latency_ms`。

禁止把 abstain 当作正确 no-popup，也禁止从可观察结果中删除误判样本。

### 5.4 可选联合指标

`Joint Message Judgment` 仅作为次指标：

```text
no-popup item: popup_present_pred == false
popup item:    popup_present_pred == true
               AND normalized message_text_pred == message_text_gt
```

其分母只能是 complete-text eligible items；不要把它命名为 D、Recovery、VTR 或 A-VTR。

## 6. Eligibility contract

建议用任务特定资格，避免继续重载现有含义不清的 `eligible_for_main_metric`：

```json
{
  "eligible_for_v1_presence_metric": true,
  "eligible_for_v1_message_metric": true,
  "eligible_for_advanced_recovery_metric": false,
  "eligible_for_user_experience_claim": false,
  "exclusion_reasons": []
}
```

`eligible_for_v1_presence_metric=true` 当且仅当：

- `record_kind ∈ {real_app, controlled_fixture}`；synthetic schema fixture 与 paper reconstruction 永远为 false；
- gold presence 已裁决且 evidence 可解析、hash/权限/隐私合格；
- prediction 使用冻结版本，并在任何 action 前产生；
- `action_attempts=[]`；
- 六类 leakage group 与 split gate 通过。

`eligible_for_v1_message_metric=true` 还要求：

- `popup_present_gt=true`；
- `message_text_observability=complete`；
- `message_text_gt` 非空且裁决完成。

`eligible_for_advanced_recovery_metric` 只有执行动作并满足 advanced D/C/T 证据契约时才可为 true。

v1 默认 `eligible_for_user_experience_claim=false`。即使消息判断准确，也不能推出用户体验改善或原任务恢复；若未来有目标用户、伦理/同意/隐私材料，只能单独评估“消息通知的可用性”，不能据此声称 Recovery。

## 7. Advanced recovery 的降级方式

在 `popup_message_judgment_v1` profile 下：

```text
action_attempts = []
dismissal.visual_popup_gone = null
dismissal.semantic_popup_gone = null
D = null
C_tech = null
C_a11y = null
T = null
VTR_tech = null
A_VTR = null
```

这些 null 的 presence reason 应为 `not_applicable`（该 profile 未执行动作），不是 `false`、空对象或 `collection_failed`。现有 `ITEM-014` 至 `ITEM-018` 只在 `dismissal_recovery_advanced` 时适用；v1 validator 不应要求 post-action/task-check observation。

若未来补做 advanced run，应创建新的 method-specific episode 并沿用相同 scenario/group/split；不得回填 v1 prediction 后再把同一记录伪装成独立恢复实验。

## 8. 保持 `90 + 165 = 255` 不变的迁移规则

1. 不删除、不重命名、不重算 `schema/source_to_item_crosswalk.json` 的 255 条来源记录。
2. 不把 profile 字段混称为新的“论文/我方方法来源字段”。保留：

   ```text
   source_field_union = 90 literature + 165 our_method = 255
   v1_profile_extension_fields = separately counted protocol fields
   ```

3. 现有 action、dismissal、C/T、VTR、feedback、capability 与 raw-platform 字段继续留在 union schema；只是由 profile 决定 requiredness。
4. 下一 schema 版本宜用 `oneOf`/`if-then`：公共 provenance/observation 层始终必需；v1 分支要求 `message_judgment` 且禁止动作；advanced 分支要求完整 current episode chain。
5. 现有 synthetic fixture 可标为 `dismissal_recovery_advanced` 并保持原值不变；另建 v1 fixture 时必须是新 item，且仍不得进入经验指标。
6. 在 profile-aware validator 上线前，现有 `verification.eligibility.eligible_for_main_metric` 对 v1 item保持 `false`，避免旧工具把它误解释为恢复主指标；v1 使用上面的任务特定 eligibility。

## 9. 最小新增 QA gates

- `V1-MSG-001`：gold label 条件关系与 presence/provenance 一致。
- `V1-MSG-002`：prediction 引用动作前 observation，且 `action_attempts=[]`。
- `V1-MSG-003`：正/负样本 evidence、双标与裁决满足契约。
- `V1-MSG-004`：presence、text、abstention 与 coverage 指标由原子字段重算。
- `V1-MSG-005`：任务特定 eligibility 由 QA 重算，synthetic/paper reconstruction 为零贡献。
- `V1-MSG-006`：六类 group 防泄漏、权限、隐私与 artifact disposition 继续沿用现有 dataset gates。

## 10. 验收标准

实现完成应同时满足：

- 一个 positive、一个 no-popup hard negative、一个 abstain fixture 均可验证；
- v1 fixture 无动作、无 post-action observation，D/C/T/VTR 全为 null 且不会触发恢复公式错误；
- v1 指标能从 gold/prediction 独立重算，且 false notification 不会被 abstain/过滤掩盖；
- 原 255 条 crosswalk 仍为 `90/165/255`、无缺失、canonical pointer 检查不回退；
- 文档与结果不再把 v1 判断任务称为 Recovery，也不把消息投递成功称为弹窗消失或原任务恢复。
