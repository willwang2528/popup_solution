# Pre-gold visual evidence freeze

本目录冻结 B1、C1 与 MG-PU 可共同使用的视觉证据边界。现在已有一个低覆盖、本机可重放的本研究启发式 adaptation：Apple Vision 固定参数强矩形提议器先从整张截图生成 popup ROI，只有矩形分数达到冻结阈值且 ROI 内 OCR 至少读到 4 个字符时才输出正判断；其余一律弃答，永不因“没检测到矩形”输出 `no_popup`。

30-item pre-gold 运行的公开聚合见 [`PUBLIC_VISUAL_BANK_SUMMARY.json`](./PUBLIC_VISUAL_BANK_SUMMARY.json)：4 项 judged、26 项 abstain。相同主机、二进制和 OS build 上的两次独立运行，在排除 `latency_ms` 与由其影响的 `response_sha256` 后，presence 决定、ROI 和消息逐项一致。该结果只记为 `repeat_execution_byte_identical_on_fixed_host=true`；Apple Vision 是 OS 绑定的封闭实现，`cross_os_or_device_model_identity_reproducible=not_verified`。私有逐项 bank、截图、ROI 和 OCR 文本仍在 Git-ignored `results/`，没有公开。

[`VISUAL_EVIDENCE_PROTOCOL_V1.json`](./VISUAL_EVIDENCE_PROTOCOL_V1.json) 现为 `ready_for_visual_bank_freeze`，只解锁冻结视觉输入/ROI 工程门。它是 `fixed_threshold_heuristic_adaptation`，不是 canonical、validated 或 formal baseline；没有人工 gold、没有评分，也不证明 4 个正判断正确。B2 PopSweeper exact 仍为 NO-GO；本 adaptation 不能改名为 PopSweeper、VLM 或论文正式结果。

## Fail-closed 规则

- 一切冻结发生在人工 gold 之前；不得读取抽样目录标签、source sampling label、标注、仲裁或动作后证据。
- 每个 pilot item 必须恰有一行。重复、缺失、未知 ID、输入图 hash 错配、配置漂移或部分输出都会阻断整批。
- positive popup judgment 若声明使用 popup ROI，必须具有预声明 detector 生成的 `predicted_popup_bbox`。全屏截图和 close-button bbox 都不是 popup ROI。
- 缺 presence 依据、ROI、模型 revision/checkpoint、prompt/config/environment hash 时，该行只能 `abstain`，不得以 OCR 中“有文字”推断“有弹窗”。
- 所有行都只能是 `no_action`、`human_gold_used=false`、`scored=false`、`paper_result_eligible=false`。

## 可复现运行

在 macOS 上编译冻结的本地引擎：

```bash
xcrun --sdk macosx swiftc \
  -module-cache-path /private/tmp/pmab-visual-module-cache \
  -O \
  experiments/v1-message/visual/vision_popup_roi_ocr.swift \
  -o experiments/v1-message/visual/.build/vision-popup-roi-ocr
```

然后运行私有 30-item bank：

```bash
../.venv/bin/python3 experiments/v1-message/visual/run_roi_ocr.py \
  --manifest dataset-v1/work/annotation-media/pilot-batch-30/pilot-manifest.jsonl \
  --media-root dataset-v1/work/annotation-media/pilot-batch-30 \
  --engine experiments/v1-message/visual/.build/vision-popup-roi-ocr \
  --output-dir experiments/v1-message/visual/results/pilot-batch-30-v1.0.1
```

适配器只读取 `pilot_item_id` 与截图 role/path/hash；manifest 内已有的 source label、sampling stratum 与 `popup_present_gt` 明确被忽略。行为测试既会反转这些禁止字段，也会把它们物理删除，并要求预测与 bank hash 不变。manifest 根对象或 artifact 出现未登记字段时整批 fail closed，防止新标签字段在 schema 漂移中静默进入数据路径。

私有 bank 的验证与公共摘要由 [`popup_eval/visual_freeze.py`](../popup_eval/visual_freeze.py) 完成。finalizer 只接受 `ready_for_visual_bank_freeze` 且 presence/ROI/model/budget 全部 `formal_ready=true` 的协议，并把整批 item→冻结截图 SHA-256 映射 commitment、逐项图片 hash、presence/ROI policy ID、模型配置及 judged request/response hash 全部绑定；`mode=none`、blocked 协议、图片错配、占位调用证据或配置漂移均整批拒绝。逐项图片、crop、ROI、message、fact、请求/响应与 item/source 映射放入 Git-ignored `private/` 或 `results/`，权限分别为目录 `0700`、文件 `0600`；公开内容只能是协议/模型 hash、整批 bank hash 与聚合计数。

## C1 与等预算的命名

`C1-AO` 是真正的 always-on fusion：每项调用共享 visual bank，与 MG-PU 使用同一单次模型配置，但总视觉调用和成本更高，只用于 accuracy-cost frontier。

`C1-BM` 是 budget-matched fusion：在 gold 前按冻结 seed/hash 选择与 MG-PU 相同数量 `K` 的视觉项。它不能称为 always-on。二者必须分开报告，避免把“不可能同时成立的 always-on 与同总调用预算”混为一个基线。该控制只匹配调用成本，不匹配 item 集或难度；任何未来 accuracy 比较必须披露它和 MG-PU 实际视觉检查 item 集的重叠。

## B2 边界

PopSweeper exact 不使用本目录自建 ROI 解锁。其官方代码、权重、阈值、时序帧和 close-button 标注仍缺失，继续保持 exact NO-GO。任何自建 popup ROI 只能命名为独立 adaptation，不能称为 PopSweeper exact。
