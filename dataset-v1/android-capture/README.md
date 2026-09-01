# Android 正式采集可行性门（CAP-001）

这里定义 PMAB v1 正式 Android 数据锚的离线入口。每条候选必须来自同一稳定状态下、时间差不超过 3000 ms 的截图与 Android `AccessibilityService` node snapshot，并且全程 `pre_action`、`action_attempts=[]`。

本目录当前只有经过测试的校验工具，没有真实 Android capture。公开状态因此仍是 `blocked_no_real_android_captures`；它不构成人工金标、论文结果、公开 benchmark 或视障用户体验证据。

## 输入 bundle

每个私有 bundle 至少包含：

- `capture.json`：采集 ID、group、弹窗模板族、预期抽样层、双时间戳、稳定状态 token、设备／App／locale、collector 和授权信息；
- PNG/JPEG 截图；
- UTF-8 JSON 的 AccessibilityService window/node snapshot。

原始 bundle 应放在 Git 忽略的 `incoming/` 或 `private/`。不接受 UIAutomator dump、RICO semantic JSON、OCR 或模型输出冒充正式 accessibility snapshot。

## 单条终结

在项目根目录运行：

```bash
.venv/bin/python3 \
  popup-solution/dataset-v1/android-capture/finalize_android_capture.py \
  finalize \
  --metadata popup-solution/dataset-v1/android-capture/incoming/CAP-001/capture.json \
  --output popup-solution/dataset-v1/android-capture/results/CAP-001.finalized.json
```

输出只保留标识符、同步结果、授权状态、文件哈希／大小和 window/node 计数，不复制原始 screenshot 或 node text。单条成功状态仅为 `eligible_for_capture_feasibility`。

## 聚合门

将终结记录组成 JSON array 后运行：

```bash
.venv/bin/python3 \
  popup-solution/dataset-v1/android-capture/finalize_android_capture.py \
  audit \
  --records popup-solution/dataset-v1/android-capture/results/finalized-records.json \
  --output popup-solution/dataset-v1/android-capture/results/feasibility-audit.json
```

聚合门要求：至少 5 个 source groups、3 个 popup template families，并覆盖 `popup_candidate`、`no_popup_candidate`、`boundary_candidate` 三层；capture ID、截图哈希和结构哈希均不得重复。通过后也只是 `ready_for_real_g1_pilot`，下一步仍须进行独立、盲式真人 G1 标注。

## 回归

```bash
.venv/bin/python3 -m unittest \
  popup-solution/dataset-v1/android-capture/tests/test_capture_finalizer.py -v
```

权威合同见 [`CAPTURE_CONTRACT_V1.json`](./CAPTURE_CONTRACT_V1.json)，当前零样本状态见 [`PUBLIC_FEASIBILITY_STATUS.json`](./PUBLIC_FEASIBILITY_STATUS.json)。
