# Popup Message Annotation Pilot v1

本目录是冻结 N=120 候选集上的 30 条消息标注协议 pilot。它只建立可执行的双人盲标、协议一致性和裁决输入链路；**当前没有人工 message gold，也不分发任何原始图像**。

## 1. 当前状态与边界

- 固定批次：30 条 PopSweeper adapter-only 候选；15 `ads` + 15 `no_ads`，仅用于审计平衡。
- 人工真值：`pending`。来源目录的 `ads/no_ads` 只用于抽样，不是人工 presence/message gold。
- 原始图像：留在获授权的本地源归档，通过 adapter 临时查看；不得复制到模板、报告、Git 或裁决包。
- 允许输出：匿名标注 JSONL、数值一致性报告、无最终标签的裁决输入、经真实人工裁决后产生的裁决输出。
- 禁止输出：模型伪金标、来源标签冒充人工标注、虚构 message 文本、原始截图/裁剪图、token F1 冒充语义正确性。

## 2. 文件

```text
annotation-pilot/
├── manifests/pilot_batch_30.jsonl
├── schemas/
│   ├── annotation_record.schema.json
│   ├── adjudication_input.schema.json
│   └── adjudication_output.schema.json
├── scripts/
│   ├── build_pilot_bundle.py
│   ├── calculate_agreement.py
│   └── serve_blind_viewer.py
├── templates/
│   ├── annotator_a.jsonl
│   ├── annotator_b.jsonl
│   ├── adjudication_input.template.json
│   └── adjudication_output.template.json
└── README.md
```

`manifests/pilot_batch_30.jsonl` 是 coordinator-only 映射，包含源记录和 archive member 定位信息。A/B 只能接收各自模板及一个只解析 `adapter_item_handle` 的查看器，不能读取 coordinator manifest。

## 3. 固定 30 条选择规则

输入是 `../candidates/popsweeper_candidates_n120.jsonl`。先按以下三元组分层：

```text
official_split × source_sampling_label × source_kind
```

每个 label 的 quota：

| Audit split | numeric | recorded frame | 每 label 合计 |
|---|---:|---:|---:|
| train | 7 | 2 | 9 |
| valid | 2 | 1 | 3 |
| test | 2 | 1 | 3 |
| 合计 | 11 | 4 | 15 |

每层用下式排序后取前 `quota` 条：

```text
SHA-256("pmj-pilot30-v1|" + source_record_id)
```

选中项再用下式冻结 coordinator 顺序：

```text
SHA-256("pmj-display-v1|" + source_record_id)
```

因此总分布固定为：15/15 source label、18/6/6 audit split、22 numeric + 8 recorded frame。A/B 模板分别使用独立 hash seed 重排，顺序不同但 item 集合完全相同。

## 4. 双人盲标

### 4.1 Blinding

Annotator A 与 B 必须独立工作，在两份 annotation 都冻结前不得看到：

- 对方的标签、消息或笔记；
- `source_sampling_label`、source path 或含 `ads/no_ads` 的 source ID；
- 模型 prediction、OCR 预标注或 agreement 输出。

完成记录必须将 `blindness_attestation` 三项均设为 `true`。任一项不成立，该记录不能进入协议一致性计算。

`serve_blind_viewer.py` 是 loopback-only 的截图查看器。它从 A/B 盲模板解析规范化 `adapter_item_handle`，按 `pilot_item_id` 直接定位本地截图；不会读取或渲染 `candidate.json`、pilot manifest、source label、RICO metadata、OCR 或模型输出。Coordinator 启动后只把随机 token URL 与 `view_session_id` 交给对应 annotator；annotator 不获得 adapter 根目录或 repo 文件权限。

### 4.2 Presence label

- `popup`：动作前画面存在独立于宿主内容、打断或覆盖当前交互上下文的 popup message。
- `no_popup`：检查完整可见上下文后，没有符合上述定义的 popup。
- `uncertain`：证据可查看，但无法可靠二分。
- `unusable`：adapter/source 损坏、无法加载或证据不足以开展标注。

“树中没找到”“来源目录写了 no_ads”或模型没有检测到都不能单独生成 `no_popup`。

### 4.3 Message transcription

只有 `presence_label=popup` 时才标 message：

- `message_observability=complete|partial`：逐字转录可见/可读主体消息；保留否定、金额、日期、期限、对象和关键按钮语义，不翻译、不补写。
- `message_observability=not_observable`：`message_text=null`、`semantic_slots=[]`。
- `no_popup`：`message_text=null`、`message_observability=not_applicable`、`semantic_slots=[]`。
- `uncertain|unusable`：`message_text=null`、`message_observability=not_observable`、`semantic_slots=[]`。

### 4.4 Semantic slots

每个 slot 为：

```text
slot_type + verbatim value + polarity
```

允许的 `slot_type`：

- `amount`
- `date_time`
- `duration_deadline`
- `action_choice`
- `object_target`
- `permission_data`
- `restriction_negation`
- `consequence`
- `other_critical`

`polarity` 为 `affirmed|negated|conditional|unknown`。只标会改变用户理解或决策的信息；不能用自由改写补足不可见内容。

### 4.5 Evidence

证据只记录 adapter session 与文字定位笔记：

- `adapter_viewed=true`
- 非空 `view_session_id`
- 可选 `region_or_node_notes`
- `raw_image_copied=false`

不得在 JSONL 中嵌入图像、base64、文件复制路径或外发 URL。

## 5. 协议一致性口径

`calculate_agreement.py` 只计算 annotator 间协议一致性，不产生 gold：

1. **Presence Cohen's kappa**：对 `popup/no_popup/uncertain/unusable` 四类计算未加权 κ，同时保存 confusion matrix、observed agreement 与 expected agreement。若期望一致率为 1，κ 输出 `null` 并给 warning。
2. **Message exact agreement**：只在 A/B 都标 `popup` 且都有 message text 的 item 上比较原始字符串完全一致。
3. **Message normalized agreement**：只做 Unicode NFKC、casefold、空白折叠；不删除标点、数字、否定或任何 token。
4. **Semantic-slot agreement**：将 `(slot_type, normalized value, polarity)` 视为集合，报告 exact-set rate 与 mean Jaccard。

semantic-slot exact/Jaccard 是**结构化标注一致性**，不是“消息语义正确率”。任一 slot 分歧会进入 adjudicator 输入；不得用 token F1、embedding 相似度或规则分数自动判定哪一方语义正确。

## 6. Adjudication 输入/输出

### 输入

脚本为全部 A/B 配对 item 生成 `record_status=ready` 的 final-review 输入。存在分歧时，`disagreement_reasons` 记录以下一项或多项；A/B 完全一致时该数组为空，但仍必须由第三位真实 adjudicator 重新查看 adapter evidence 并确认 final：

```text
presence
message_exact
message_normalized
message_observability
semantic_slots
```

输入内保留 A/B 的原始 completed record，`adjudication_status=pending`，不包含任何 `*_final` 字段，也不读取 source sampling label。协议不自动把 A/B 一致转换为 gold。

### 输出

Adjudicator 必须重新通过 adapter 查看证据，再按 `adjudication_output.schema.json` 填写独立输出：

- `adjudication_status=resolved|cannot_resolve`
- `presence_label_final`
- `message_text_final`
- `message_observability_final`
- `semantic_slots_final`
- `decision_rationale`
- `evidence_rechecked_via_adapter=true`
- 匿名 adjudicator ID 与时间戳

只有真实完成且通过 QA 的 `resolved` 输出才能成为后续 adjudicated human gold。空模板、A/B annotation、agreement report、source label、模型预标注都不是 gold。

## 7. 运行命令

所有命令从当前 checkout 的项目根目录运行：

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
ARIS_PYTHON="$PROJECT_ROOT/.venv/bin/python3"
test -x "$ARIS_PYTHON"
```

重新物化并逐字节验证固定批次：

```bash
"$ARIS_PYTHON" popup-solution/dataset-v1/annotation-pilot/scripts/build_pilot_bundle.py \
  --candidates popup-solution/dataset-v1/candidates/popsweeper_candidates_n120.jsonl \
  --output-root popup-solution/dataset-v1/annotation-pilot

"$ARIS_PYTHON" -m unittest \
  popup-solution/tests/test_annotation_pilot_protocol.py -v
```

在 A/B 各自完成并冻结工作副本后计算一致性与裁决输入：

```bash
"$ARIS_PYTHON" \
  popup-solution/dataset-v1/annotation-pilot/scripts/calculate_agreement.py \
  --annotations-a /ABSOLUTE/PRIVATE/PATH/annotator_a.completed.jsonl \
  --annotations-b /ABSOLUTE/PRIVATE/PATH/annotator_b.completed.jsonl \
  --report /ABSOLUTE/PRIVATE/PATH/agreement.json \
  --adjudication-input /ABSOLUTE/PRIVATE/PATH/adjudication-input.jsonl
```

启动 A/B 各自的隔离 viewer（示例为 A；服务只允许 loopback 地址）：

```bash
"$ARIS_PYTHON" \
  popup-solution/dataset-v1/annotation-pilot/scripts/serve_blind_viewer.py \
  --annotations-template popup-solution/dataset-v1/annotation-pilot/templates/annotator_a.jsonl \
  --adapter-root /ABSOLUTE/GIT-IGNORED/annotation-media
```

输出中的随机 URL 与 `view_session_id` 只用于该次人工会话；不要把它们提交到 Git。

当前 checkout 已在 Git-ignored 的 `annotation-pilot/private/` 下建立 `0700/0600` 工作副本。A/B 和 adjudicator 只填写这些私有副本；tracked `templates/` 永远保持空白。

运行本协议全部测试：

```bash
"$ARIS_PYTHON" -m unittest \
  popup-solution/tests/test_annotation_pilot_protocol.py \
  popup-solution/tests/test_annotation_agreement.py -v
```

脚本会拒绝：空白记录、A/B item 集不一致、重复 item、同一 annotator 冒充 A/B、source/model/peer 未盲、no-popup 携带 message、不可观察记录携带语义、复制原图，以及不完整 evidence。

## 8. Pilot 通过条件与后续 N=120

本目录不预填 kappa 阈值或“通过”结论。两位 annotator 完成 30 条并裁决后，研究者应在看 N=120 结果前冻结：

- presence κ 的接受/返工阈值；
- exact/normalized/semantic-slot 分歧的修订规则；
- `uncertain/unusable/not_observable` 的最大容许率；
- 完整 N=120 的 annotator 分配、抽检比例和裁决预算。

如果协议或 slot 定义发生变化，pilot 必须用新 `protocol_version` 重跑；不能用 outcome-driven 修改覆盖已有标注。
