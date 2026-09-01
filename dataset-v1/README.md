# Popup Episode Union Dataset v1：弹窗消息判断 Profile

当前数据 contract 的主任务是 `popup_message_judgment_v1`：给定移动端动作前 observation，判断是否存在弹窗，并输出可读消息或弃答。v1 不执行点击或关闭。

## 并集与扩展

- 14 篇既有论文：90 个原子字段；
- 我方既有方法：165 个原子字段；
- `source_to_item_crosswalk.json`：255/255 条有来源映射；
- `message_judgment`：当前 v1 新增的 44 个协议字段，单独标为
  `v1_profile_extension`，不伪装成论文来源字段；
- 单 item 完整可追溯视图：90 + 165 + 44 = 299 行。

保留动作和幻灯片 14 的 `D/C_tech/C_a11y/B/T` 五级回证，以及派生指标
`VTR_tech/A_VTR`，是为了文献兼容和后续 advanced profile；它们在 v1 中必须为
`null/not_applicable`，不是主指标。

## v1 item

```text
identity + provenance + scenario + environment
→ one or more action-free observations
→ cross-platform structured/raw/visual evidence
→ message_judgment labels/gap_ground_truth/prediction/gate/evaluation/eligibility
→ feedback notification
→ no action
```

必须满足：

- `action_attempts=[]`；
- 决策为 `no_action` 或 `abstain`；
- prediction 引用动作前 observation；
- popup/message gold 与 evidence 一致；
- screenshot-message gold 与 structure–visual gap audit 分开；gap audit 只能在 message gold 后运行，且审计者看不到方法输出；A/B audit record 必须绑定冻结结构 candidate、完整 message-gold batch 和公开的 structured-bundle commitment；
- v1 D/C_tech/C_a11y/B/T/VTR 均为 null；
- synthetic fixture 不进入训练、经验指标或体验结论。

## 主指标

`VPMA` 在正样本要求 presence 正确、消息语义正确、没有关键编造；在负样本只要求 presence 正确。Abstain 的 VPMA 为 null，并必须与 coverage 一起报告。

配套指标：Popup Presence Macro-F1、message semantic correctness、Exact Match、Character F1、critical-information recall、critical-hallucination rate、abstention/coverage、visual-call rate 与 latency。

## 文件

- [`schema/item.schema.json`](./schema/item.schema.json)：v1 profile-aware 单 item schema；
- [`schema/v1_message_qa_rules.json`](./schema/v1_message_qa_rules.json)：6 个 v1 QA gate；
- [`schema/source_to_item_crosswalk.json`](./schema/source_to_item_crosswalk.json)：冻结的 255 条来源映射；
- [`data/item.template.json`](./data/item.template.json)：positive v1 模板；
- [`data/items.schema-fixture.jsonl`](./data/items.schema-fixture.jsonl)：positive、no-popup、abstain 三条 synthetic fixture；
- [`ITEM_UNION_EXAMPLE.md`](./ITEM_UNION_EXAMPLE.md)：从公开 catalog、crosswalk、template 和 fixture 动态生成的单-item 299 行完整视图（255 个来源字段 + 44 个 V1 profile 扩展字段）；明确非经验、非 gold、no-action；
- [`candidates/popsweeper_candidates_n120.jsonl`](./candidates/popsweeper_candidates_n120.jsonl)：固定 seed 的 120 条真实来源候选；只有 presence 标签，消息标注待完成，原图不随仓库分发；
- [`candidates/popsweeper_candidates_n120.summary.json`](./candidates/popsweeper_candidates_n120.summary.json)：2105 张来源图片的清点与 60 positive/60 negative 抽样配额；
- [`../sources/SOURCE_LEDGER.md`](../sources/SOURCE_LEDGER.md)：PopSweeper/RICO 校验、join、数量差异与第三方媒体发布边界；
- [`scripts/materialize_schema_fixture.py`](./scripts/materialize_schema_fixture.py)：fixture 生成器；
- [`scripts/build_item_union_example.py`](./scripts/build_item_union_example.py)：生成并检查单-item union 视图，不读取 private 媒体；
- [`scripts/popsweeper_source_audit.py`](./scripts/popsweeper_source_audit.py)：归档完整性、安全与成员清点；不解压；
- [`scripts/build_popsweeper_candidate_manifest.py`](./scripts/build_popsweeper_candidate_manifest.py)：只读 ZIP 元数据并生成 adapter-only 候选清单；
- [`scripts/export_annotation_media.py`](./scripts/export_annotation_media.py)：校验两份归档 SHA-256、全部 ZIP 成员路径和冻结 pilot→候选 member 精确映射后，向 gitignored 本地目录导出标注媒体；
- [`scripts/validate_dataset.py`](./scripts/validate_dataset.py)：验证器；
- [`ANNOTATION_GUIDE.md`](./ANNOTATION_GUIDE.md)：v1 标注协议；
- [`annotation-pilot/STRUCTURE_VISUAL_GAP_AUDIT.md`](./annotation-pilot/STRUCTURE_VISUAL_GAP_AUDIT.md)：message gold 后的结构暴露缺口 sidecar；
- [`android-capture/README.md`](./android-capture/README.md)：正式 Android 同步截图 + AccessibilityService snapshot 的 CAP-001 合同、终结器和零样本公开状态；
- [`VALIDATION_REPORT_V1_MESSAGE.md`](./VALIDATION_REPORT_V1_MESSAGE.md)：当前验证报告。

## 运行

在项目根目录用 canonical Python：

```bash
.venv/bin/python3 popup-solution/dataset-v1/scripts/export_annotation_media.py \
  --candidates popup-solution/dataset-v1/candidates/popsweeper_candidates_n120.jsonl \
  --pilot-manifest popup-solution/dataset-v1/annotation-pilot/manifests/pilot_batch_30.jsonl \
  --popsweeper-archive .tmp/source-cache/popsweeper-basic.zip \
  --popsweeper-sha256 90b7c5cfe3e78bfd8e19b0fda0884cd1f6b03086cb31c91d57eaadbe4d1b942c \
  --rico-archive .tmp/source-cache/rico-semantic-annotations.zip \
  --rico-sha256 c5c11d750cb9505e45a0ee57f2bb6186d6448f005bd8731615181310aeea0d70 \
  --output-dir popup-solution/dataset-v1/work/annotation-media/pilot-batch-30 \
  --pilot-count 30
.venv/bin/python3 popup-solution/dataset-v1/scripts/materialize_schema_fixture.py
.venv/bin/python3 popup-solution/dataset-v1/scripts/validate_dataset.py
.venv/bin/python3 -m unittest discover -s popup-solution/tests -v
```

正式标注只使用冻结的 `pilot_batch_30.jsonl`，并保留 `PMJ-PILOT-001` 至 `PMJ-PILOT-030`。`--candidate-sample` 仅供显式诊断，不得替代冻结 pilot 或生成另一组正式 N=30。导出的 JPG、RICO semantic JSON/PNG、逐项元数据与本地 manifest 均位于 `work/annotation-media/`，禁止加入 Git。

当前 `pass` 只表示 synthetic fixtures 通过已实现断言。N=120 清单是带真实来源 provenance 的**待标注候选集**，尚无 message gold，不能进入 VPMA 或消息指标；真实 Android/iOS item 和目标用户证据仍未产生。
