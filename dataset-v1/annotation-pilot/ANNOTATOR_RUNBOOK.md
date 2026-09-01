# A/B 盲标交付手册

状态：工具可交付；尚未启动真实 A/B 会话，human gold 仍为 0。

## Coordinator 准备

1. 运行 `check_human_annotation_readiness.py`，只接受
   `ready_for_real_human_annotation`。
2. 为 A、B 分配不同的匿名 pseudonym；不要在文件中写真实姓名或联系方式。
3. 分别启动两个 loopback viewer。A 使用 `annotator_a.jsonl` 与
   `private/annotator_a.working.jsonl`；B 使用对应的 B 文件。
4. 只把各自随机 URL 交给对应 annotator。不得交付 repo、adapter 根目录、另一人的
   URL、source manifest、OCR 或模型输出。

示例（A）：

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
ARIS_PYTHON="$PROJECT_ROOT/.venv/bin/python3"
"$ARIS_PYTHON" \
  popup-solution/dataset-v1/annotation-pilot/scripts/serve_blind_viewer.py \
  --annotations-template popup-solution/dataset-v1/annotation-pilot/templates/annotator_a.jsonl \
  --adapter-root popup-solution/dataset-v1/work/annotation-media/pilot-batch-30 \
  --working-output popup-solution/dataset-v1/annotation-pilot/private/annotator_a.working.jsonl \
  --annotator-pseudonym human-a
```

## Annotator 操作

- 每项先完整查看截图，再判断 `popup/no_popup/uncertain/unusable/out_of_scope`。
- 只有 `popup + complete/partial` 才填写逐字消息和语义槽；不翻译、不补写。
- 语义槽填写 JSON 数组，例如：

```json
[{"slot_type":"duration_deadline","value":"today","polarity":"affirmed"}]
```

- `out_of_scope` 必须选择冻结原因；安全控制、认证、支付、CAPTCHA 等不得当作普通
  弹窗纳入。
- 每项必须独立确认未见 peer labels、source class 与 model output。
- 提交后页面显示完成计数。服务器只在本机私有工作文件中保存，不复制截图。
- 每项第一次成功提交后不可覆盖；刷新或重复提交会被拒绝。发现误标时停止会话，
  联系 coordinator 走版本化纠错，不得直接改写已完成行。

## 收尾门

1. A/B 都显示 `30/30` 后停止两个 viewer。
2. Coordinator 检查两个工作文件仍为 `0600`，且 pseudonym 不同。
3. 运行 `calculate_agreement.py` 生成协议一致性报告和第三人输入；它不产生 gold。
4. 第三位真人对全部 30 项重新查看 adapter evidence；包括 A/B 一致项。
5. 只有通过 finalizer 的 `resolved` 行才能成为技术 benchmark gold；
   `cannot_resolve` 不进入指标。

任何模型、OCR、source label 或现有 pre-gold prediction 都不得代填 A/B 或裁决字段。
