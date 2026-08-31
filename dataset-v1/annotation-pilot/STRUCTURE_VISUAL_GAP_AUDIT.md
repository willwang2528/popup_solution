# Structure–visual message-gap audit v1

这个 audit 补的是“结构化 UI 表示究竟遗漏、合并或污染了哪些弹窗消息”证据。它不是原来的截图消息 A/B 盲标，也不得替代该盲标。

## 顺序与隔离

1. 两位真实标注者先只看截图，独立完成 popup presence、message 与 critical facts；第三位真人完成原有消息 gold 仲裁。
2. 所有方法输出和视觉调用在 gold 前已经冻结。
3. 另两位审计者只看：已冻结的结构表示、对应截图、最终 screenshot-message gold 和证据适配器；不看方法名称、route、prediction、分数或结果。
4. A/B 独立记录遵循 [`gap_independent_audit_record.schema.json`](./schemas/gap_independent_audit_record.schema.json)，并用 `structured_candidate_ids` 绑定冻结结构 bundle 中真实存在的同 item 节点。第三位 gap adjudicator 处理分歧；最终行必须绑定两条实际独立审计记录的实算 SHA-256、唯一 message-gold batch SHA-256 和预冻结 structured bundle SHA-256。
5. [`gap_adjudication.py`](../../experiments/v1-message/popup_eval/gap_adjudication.py) 不接受孤立的占位 hash：它重新验证完整 message-gold rows、真实 structured-feature rows、公开冻结的 bundle commitment、每项恰好一条 A/B record 以及最终 adjudication row。六组 item 必须严格一一对应；缺失、重复、未知 ID、同一 A/B 身份、不同 gold/structure batch、方法字段、跨 item candidate 或逻辑矛盾都会拒绝整批。

## 标注对象

- `structured_evidence_available`：结构快照是否实际存在并可读；
- `structured_message_text_final`：仅按结构中可观察内容重建的消息，不补写截图内容；
- `structured_message_complete_final`：相对 screenshot-message gold 是否完整；
- `gap_reasons_final`：`missing / merged / ambiguous / contradictory / stale / owner_mismatch / visual_only_text / host_text_contamination / unknown`；
- `critical_facts_missing_from_structure_final`：截图消息 gold 中在结构表达里缺失的金额、日期、对象、否定、限制或后果；
- `host_text_contamination_final`：结构重建是否混入宿主页面文本；
- `tree_screenshot_synchronized_final`：能否证明树与截图来自同一稳定状态。

`structured_message_complete_final=true` 时不得同时标 gap reason、缺失事实或 host contamination。结构不存在时必须标 `missing`。证据无法可靠对齐时用 `cannot_resolve`，不得猜测。

程序可以验证两条记录具有不同 pseudonymous auditor、完整 attestation、独立内容和 hash 绑定，但不能仅凭 pseudonymous ID 证明背后一定是两个真人。coordinator 仍须在私有会话与账号审计中核对真人身份和独立操作；公开摘要只表述“已记录人工声明”，不得把声明本身写成已验证的人体实验事实。

## 用途边界

该 sidecar 只用于：数据集 exposure-gap 属性、分层误差分析、gate 的事后诊断。它不能回流到 pre-gold prediction，也不能在 test set 上训练或调阈值。主指标仍是 popup presence + message judgment 的 VPMA；gap audit 不是 Recovery、用户体验或“方法优于基线”的替代证据。

逐项结构文本、截图引用、审计者身份和 rationale 属于私有数据。公开发布仅允许整批 hash、状态计数和 gap reason 聚合，仍固定 `scored=false`、`paper_result_eligible=false`，直到正式实验的其他门槛全部满足。
