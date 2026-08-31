# Local macOS Vision OCR adapter

本目录把 annotation-media pilot 的本地截图送入 macOS Vision `VNRecognizeTextRequest`，冻结为按 `pilot_item_id` 对齐的、**只读且无动作**的 OCR prediction JSONL。它不调用在线或付费 API，不点击、关闭、滑动或控制任何移动设备。

## 结论边界

- `message_text_pred` 是整张截图的 OCR 转写，可能同时包含状态栏、宿主页面、按钮和弹窗文字；它**不是 popup message 金标**，也没有经过人工语义裁决。
- OCR 本身不能证明画面中存在 popup。因此当前 adapter 始终写 `status="abstain"`、`popup_present_pred=null`；即使识别到文字也不会把“有字”改写为“有弹窗”。
- `confidence` 只是 Vision top-candidate 的平均识别置信度，不是 popup presence、消息完整性或语义正确性的置信度。
- 每条 prediction 与 run manifest 都固定 `paper_result_eligible=false`。这批输出尚未对人工 gold 打分，不能支持 OCR 性能、论文方法效果、弹窗消除、任务恢复或视障用户体验改善主张。
- `critical_facts_pred=[]`：未经人工规则或模型提取，不从 OCR 文本伪造关键事实。

## 输入隔离

公开 CLI 只使用 manifest 的四类字段：

```text
pilot_item_id
artifacts[].role
artifacts[].relative_path
artifacts[].sha256
```

其余字段全部忽略，尤其不使用 `source_sampling_label`、`popup_present_gt` 或任何 gold 字段。运行前会验证：ID 唯一、恰有一个 `popsweeper_screenshot`、路径不能是绝对路径或包含 `..`、真实路径仍位于 media root 内、图像 SHA-256 与 manifest 相等。任一检查、Swift 编译或 Vision 运行失败时，只写 `status=blocked` 的 `run_manifest.json`，不留下部分或伪造 prediction。

正式本地输入目录是：

```text
popup-solution/dataset-v1/work/annotation-media/pilot-batch-30
```

该目录由项目 `.gitignore` 排除；原始 PMJ 图片不会被复制进本目录或提交。OCR 派生文本可能包含邮箱、昵称、社交文本或其他第三方信息，因此 `ocr/results/` 也整体 gitignored，在完成隐私审查与必要脱敏前**不得发布**。公开目录只保留不含 OCR 文本、bounding boxes、PII 或绝对源路径的 [`PUBLIC_RUN_SUMMARY.json`](./PUBLIC_RUN_SUMMARY.json)，其中仅有聚合计数、latency 与内容哈希，且 `privacy_status=withheld_pending_privacy_review`。

## 输出契约

私有、gitignored 的 `predictions.jsonl` 每行包含：

- `pilot_item_id`；
- `status="abstain"` 与保守的 `popup_present_pred=null`；
- `message_text_pred`、`confidence`、`ocr_status`；
- `evidence`：相对 artifact 路径、图像/manifest SHA-256、逐段 OCR text/confidence/bounding box；
- `ocr`：Vision request revision、Swift CLI 版本、macOS 版本、语言、recognition level 与 language-correction 设置；
- `latency_ms`、`paper_result_eligible=false`；
- 不含 action、coordinate、selector 或 execution 字段。

私有 `run_manifest.json` 冻结输入、engine/source/output SHA-256、配置、计数、总 latency 与禁止的论文主张。公开副本只有聚合 summary，不复制这些逐图文本证据。

## 可复现环境

本机 Command Line Tools 默认指向 macOS 26.5 SDK，但该 SDK 与已安装 Swift compiler build 不匹配。正式环境明确 pin `macosx15.4` SDK，并把 module cache 放在 gitignored `.build/`：

```bash
xcrun --sdk macosx15.4 swiftc \
  -target arm64-apple-macosx15.4 \
  -module-cache-path popup-solution/experiments/v1-message/ocr/.build/module-cache \
  -O popup-solution/experiments/v1-message/ocr/vision_ocr.swift \
  -o popup-solution/experiments/v1-message/ocr/.build/vision-ocr-b77d6b9d7694
```

Seeded Vision dispatch witness：

```bash
popup-solution/experiments/v1-message/ocr/.build/vision-ocr-b77d6b9d7694 \
  --witness --seed 17 --language en-US
```

预期 sentinel：

```text
WITNESS vision_ocr seed=17 observations=0 revision=3
```

Vision system service 在受限文件沙箱内可能返回 `nilError` 或 CVPixelBuffer `NSOSStatus -6662`；这是 fail-closed 环境阻塞，不得改用假 OCR。应在获授权的本地 macOS 环境执行同一命令，仍禁止网络和 GUI/device action。

## 测试与正式运行

默认契约测试不需要真实 Vision system service：

```bash
.venv/bin/python3 -m unittest discover \
  -s popup-solution/experiments/v1-message/ocr/tests -v
```

启用 seeded witness 与一张真实、gitignored PMJ 图片 smoke：

```bash
PMJ_RUN_REAL_VISION=1 .venv/bin/python3 \
  -m unittest discover -s popup-solution/experiments/v1-message/ocr/tests -v
```

正式 30 图冻结命令：

```bash
.venv/bin/python3 \
  popup-solution/experiments/v1-message/ocr/run_ocr.py \
  --manifest popup-solution/dataset-v1/work/annotation-media/pilot-batch-30/pilot-manifest.jsonl \
  --media-root popup-solution/dataset-v1/work/annotation-media/pilot-batch-30 \
  --output-dir popup-solution/experiments/v1-message/ocr/results/pilot-batch-30 \
  --language zh-Hans --language en-US \
  --recognition-level accurate --seed 17
```

CLI 默认拒绝覆盖冻结 predictions。只有在明确要建立新冻结版本并先保存旧证据时才可使用 `--overwrite`。

## 本次 TDD 与实际状态

- RED：实现前 6 个功能测试均因 `run_ocr.py` / `vision_ocr.swift` 不存在而失败，覆盖 label/gold 泄漏、路径逃逸、SHA 错配、engine 失败、seeded witness 与真实 PMJ decoding；发现派生文本隐私风险后，又先加入并观察了 public-artifact privacy gate 的失败。
- GREEN：当前共 7 项；默认测试 5 pass、2 个真实 gate 按环境变量 skip。fresh agent 原样执行完整命令后，在授权本机 Vision 环境中 7/7 通过（含 1 张正式 PMJ smoke 与 seeded witness）；隐私 gate 也确认 `.build/`、`results/` 被忽略，公开 summary/compute 副本不含本机绝对路径。
- 正式 30 图：30/30 产生 action-free OCR evidence；30/30 `status=abstain`、30/30 `popup_present_pred=null`、30/30 `paper_result_eligible=false`。这只说明 OCR 管线运行成功，不说明文本正确或方法有效。

可公开环境 spec/ledger：[`compute/local-macos-pmj-ocr.env-spec.json`](./compute/local-macos-pmj-ocr.env-spec.json) 与 [`compute/local-macos-pmj-ocr.md`](./compute/local-macos-pmj-ocr.md)。根目录 `.aris/compute/` 另保留本机 ledger，但它不是 `popup-solution` 发布子树的一部分。
