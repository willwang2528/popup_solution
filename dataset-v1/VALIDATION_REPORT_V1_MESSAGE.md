# Popup Message Union Dataset v1 验证报告

> 日期：2026-08-31
>
> 判定：**v1 message-only contract 通过已实现验证；真实设备经验数据仍未产生。**

## 1. 范围

当前 profile 为 `popup_message_judgment_v1`。验证目标是：

- 只读取动作前观察；
- 输出 popup presence、message、critical facts 或 abstain；
- `action_attempts=[]`；
- D/C/T/VTR 均为 `null/not_applicable`；
- synthetic fixture 不进入经验指标或用户体验结论。

旧 [`VALIDATION_REPORT.md`](./VALIDATION_REPORT.md) 记录 schema 1.0 Recovery 契约的历史验证；本报告取代它成为当前 v1 状态说明，但不改写历史文件。

## 2. 机器验证

项目 canonical Python 执行：

```text
.venv/bin/python3 popup-solution/dataset-v1/scripts/build_crosswalk.py
.venv/bin/python3 popup-solution/dataset-v1/scripts/materialize_schema_fixture.py
.venv/bin/python3 popup-solution/dataset-v1/scripts/validate_dataset.py
```

结果：

```text
status: pass
schema: 1.1.0-provisional
fixtures: 3 synthetic items (positive, no-popup, abstain)
source-field union: 90 literature + 165 ours = 255
v1 message QA: 4 automated_full + 2 automated_partial
errors: 0
warnings: 2
```

两条预期警告：尚无 empirical real-app item；尚无 iOS capability/episode item。

## 3. 已验证的不变量

- v1 无 action attempt、无 post-action/task-check observation；
- popup、blocking、message 和 observability 的条件关系一致；
- prediction 引用同 item 动作前 observation；
- abstain 不携带伪 prediction，也不获得 VPMA；
- visual fallback 标志与调用次数一致；
- presence correctness、critical-information recall 与 VPMA 可从原子字段重算；
- v1 不允许 D/C/T/VTR 成功值；
- synthetic/paper-reconstruction item 不具备 v1 经验指标资格；
- 255 条来源字段全部映射到仍存在的 canonical pointer。

另外执行了七类负向变异：把 decision 改为 `execute`、注入 action attempt、伪造 VPMA、在 v1 写入 D 成功、将 source observation 改为 post-action、让 synthetic fixture 获得经验指标资格、制造视觉调用计数冲突。七类均被验证器拒绝；随后原始 fixtures 再次通过。

## 4. Fixture 隔离

三条 fixture 均满足：

```text
record_kind = synthetic_schema_fixture
split = schema_fixture
eligible_for_v1_presence_metric = false
eligible_for_v1_message_metric = false
eligible_for_advanced_recovery_metric = false
eligible_for_user_experience_claim = false
```

它们只测试 contract，不是训练数据、实验结果或用户证据。

## 5. 可复现 SHA-256

| Artifact | SHA-256 |
|---|---|
| `data/items.schema-fixture.jsonl` | `1898d32683ae5d093957047263abf1cf48e1a9d26679394938ee488a451bf1e4` |
| `schema/source_to_item_crosswalk.json` | `912c2b77e91e65a612bed51e776e93763457d73c246c716b9532bf872caa71ff` |
| `schema/item.schema.json` | `35490b44b640b2a45f08c5fb00b1f0b5bdf2ebb14d6420dd221cba573f80d4b0` |
| `schema/field_catalog.json` | `10f8b5801d69765055ed3a935d88d532a722a86b9163ac3bbd0029a846a9f8b9` |
| `schema/v1_message_qa_rules.json` | `908ec1a13f50d60b8fa1b16a72730fce8603548c45a007f2014947dd97a8f623` |
| `scripts/validate_dataset.py` | `9a998e59ec3650d5100dd260cecfc1dfe2008e42f6ff66e5e5a0c9fabd163136` |

## 6. 未完成门

正式采集前还需：

1. Android/TalkBack 与 iOS/VoiceOver 只读 capability pilot；
2. 两名标注者的 message semantics／critical hallucination 协议试标；
3. screenshot/tree 权限、隐私、脱敏与发布检查；
4. 根据 pilot 的 paired effect、cluster size 与 coverage 冻结 `N`；
5. App/template/SDK/UI framework/OS family/near-duplicate group split 回证。

因此正确交付名称是 **collection-ready v1 message contract + synthetic fixtures**，不是公开实测 benchmark。
