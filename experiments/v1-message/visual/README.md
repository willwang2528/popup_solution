# Pre-gold visual evidence freeze

本目录冻结 B1、C1 与 MG-PU 后续可共同使用的视觉证据边界。它不包含正式视觉输出，也不把现有全屏 OCR 或模型预标注改名为可复现视觉 baseline。

当前硬状态见 [`VISUAL_EVIDENCE_PROTOCOL_V1.json`](./VISUAL_EVIDENCE_PROTOCOL_V1.json)：`blocked_missing_reproducible_presence_roi_visual_bank`。30-item pilot 尚无可复现的 popup-presence detector、合法 popup ROI、完整视觉模型身份或共享 visual bank，因此 B1、C1 与完整 MG-PU 都不能进入正式比较。

## Fail-closed 规则

- 一切冻结发生在人工 gold 之前；不得读取抽样目录标签、source sampling label、标注、仲裁或动作后证据。
- 每个 pilot item 必须恰有一行。重复、缺失、未知 ID、输入图 hash 错配、配置漂移或部分输出都会阻断整批。
- positive popup judgment 若声明使用 popup ROI，必须具有预声明 detector 生成的 `predicted_popup_bbox`。全屏截图和 close-button bbox 都不是 popup ROI。
- 缺 presence 依据、ROI、模型 revision/checkpoint、prompt/config/environment hash 时，该行只能 `abstain`，不得以 OCR 中“有文字”推断“有弹窗”。
- 所有行都只能是 `no_action`、`human_gold_used=false`、`scored=false`、`paper_result_eligible=false`。

私有 bank 的验证与公共摘要由 [`popup_eval/visual_freeze.py`](../popup_eval/visual_freeze.py) 完成。finalizer 只接受 `ready_for_visual_bank_freeze` 且 presence/ROI/model/budget 全部 `formal_ready=true` 的协议，并把整批 item→冻结截图 SHA-256 映射 commitment、逐项图片 hash、presence/ROI policy ID、模型配置及 judged request/response hash 全部绑定；`mode=none`、blocked 协议、图片错配、占位调用证据或配置漂移均整批拒绝。逐项图片、crop、ROI、message、fact、请求/响应与 item/source 映射放入 Git-ignored `private/` 或 `results/`，权限分别为目录 `0700`、文件 `0600`；公开内容只能是协议/模型 hash、整批 bank hash 与聚合计数。

## C1 与等预算的命名

`C1-AO` 是真正的 always-on fusion：每项调用共享 visual bank，与 MG-PU 使用同一单次模型配置，但总视觉调用和成本更高，只用于 accuracy-cost frontier。

`C1-BM` 是 budget-matched fusion：在 gold 前按冻结 seed/hash 选择与 MG-PU 相同数量 `K` 的视觉项。它不能称为 always-on。二者必须分开报告，避免把“不可能同时成立的 always-on 与同总调用预算”混为一个基线。

## B2 边界

PopSweeper exact 不使用本目录自建 ROI 解锁。其官方代码、权重、阈值、时序帧和 close-button 标注仍缺失，继续保持 exact NO-GO。任何自建 popup ROI 只能命名为独立 adaptation，不能称为 PopSweeper exact。
