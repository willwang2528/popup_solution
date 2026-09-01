# Android 正式采集可行性门（CAP-001）

这里定义 PMAB v1 正式 Android 数据锚的采集、人工复核和离线终结入口。每条候选必须来自同一稳定状态下的 `tree-before → screenshot → tree-after` 回证；三者使用 `SystemClock.uptimeMillis()` 同一时基，截图与两侧树的距离均不超过 3000 ms，并且全程只读、`pre_action`、无点击/手势/返回键/弹窗消除动作。

本目录当前已有可编译的 Android 30+ `AccessibilityService` 采集器、主机触发/回读工具和经过测试的 V1.1 终结器（合同修订 1.1.2），但没有连接过真实设备，也没有真实 Android capture。公开状态因此仍是 `blocked_no_real_android_captures`；它不构成人工金标、论文结果、公开 benchmark 或视障用户体验证据。

当前主机安装前提与两条可执行路径见
[`ANDROID_RUNTIME_READINESS.md`](./ANDROID_RUNTIME_READINESS.md)：优先使用授权真机；
模拟器路径仍缺 command-line tools、emulator 与 system image。该记录不改变真实
capture 数为 0 的状态。

[`fixture-target/`](./fixture-target/) 提供受控采集目标的源码、场景目录和构建合同：5 个唯一 package、3 个弹窗模板族、每组 positive/no-popup/boundary，共 15 个 `definition_only` 场景。其状态是 `installation_prerequisites_ready=true`、`device_capture_validated=false`；它只用于后续真实采集 dry run，不能替代 AccessibilityService 设备证据或人工复核。

## 采集器边界

`collector-android/` 只暴露由系统以签名级 `BIND_ACCESSIBILITY_SERVICE` 权限绑定的服务。服务读取 interactive windows、view IDs、AccessibilityNodeInfo 字段和默认显示器截图；请求只能通过 debug APK 的 app-private `files/capture_requests/` 目录注入。它没有 Activity、网络权限、悬浮窗权限，也不请求触摸探索、按键过滤或手势能力；编译产物测试还拒绝 `performAction`、`performGlobalAction` 和 `dispatchGesture` 符号。

采集器先读树，再调用 API 30+ `takeScreenshot`，最后再次读树。只有 canonical tree hash、accessibility event sequence 和焦点 token 前后一致，目标包存在、树未截断、没有 password/API 34 sensitive node，且同步距离通过时，才写出 `complete` bundle。机器输出不能写入隐私审核、金标、预测或论文结果字段。

Android 官方依据：AccessibilityService 必须由系统绑定并以 `BIND_ACCESSIBILITY_SERVICE` 保护；`takeScreenshot` 需要 XML 中声明截图 capability；`ScreenshotResult.getTimestamp()` 与 `SystemClock.uptimeMillis()` 同时基。

- <https://developer.android.com/guide/topics/ui/accessibility/service>
- <https://developer.android.com/reference/android/accessibilityservice/AccessibilityService.ScreenshotResult>
- <https://developer.android.com/reference/android/accessibilityservice/AccessibilityServiceInfo>

## 构建

只接受已经公开、且确实包含当前采集器源码的 40 位 Git commit SHA。`uncommitted` build 会被 V1.1 终结器拒绝。

```bash
ANDROID_HOME=/path/to/android-sdk \
GRADLE_USER_HOME=/path/to/project-local-gradle-home \
/path/to/gradle-8/bin/gradle --no-daemon \
  -PpmabSourceRevision=<40-char-public-commit-sha> \
  :app:testDebugUnitTest :app:assembleDebug
```

编译产物合约测试需要显式绑定同一个 SHA：

```bash
PMAB_COLLECTOR_APK=/path/to/app-debug.apk \
PMAB_AAPT2=/path/to/android-sdk/build-tools/35.0.0/aapt2 \
PMAB_EXPECTED_SOURCE_REVISION=<40-char-public-commit-sha> \
.venv/bin/python3 -m unittest \
  collector-android/tests/test_built_apk_contract.py -v
```

## 真机步骤（尚未执行）

1. 连接一台授权的 Android 30+ 设备，记录 serial；安装与公开 commit 绑定的 debug APK。
2. 由操作者在系统“无障碍”设置中手动启用 PMAB Collector；工具不会改写 secure settings。保留研究条件要求的屏幕阅读器，并在后续 `review.json` 中人工确认其名称和版本。
3. 把普通、已授权目标 App 停在待采集的稳定弹窗/非弹窗/边界状态。不要采集验证码、认证、支付、风险控制、人工审核或其他安全控制。
4. 从 `collector-android/request.example.json` 复制一个请求，保证 capture/group/template ID 唯一，目标包准确。
5. 运行 doctor；只有 `device_state="device"`，且
   `package_installed`、`debug_run_as_ready`、`collector_service_enabled` 三个布尔门
   全部为 true 才继续：

```bash
.venv/bin/python3 \
  collector-android/host_capture.py \
  --adb /path/to/adb --serial <serial> doctor
```

6. 注入请求、等待 app-private bundle、逐文件回读并重算哈希：

```bash
.venv/bin/python3 \
  collector-android/host_capture.py \
  --adb /path/to/adb --serial <serial> capture \
  --request-json collector-android/request.example.json \
  --output incoming/PMAB-A-CAP-001
```

主机输出包含 `request.json`、`machine-capture.json`、`tree-before.json`、`tree-after.json` 和 `screenshot.png`。它仍是私有候选，不是公开数据。

如果设备端 collector 返回 `machine_status="rejected"`，主机命令必须以退出码 2
失败，并且不会把该记录发布到成功的 `incoming/<capture-id>` 路径。stderr 只报告经
allowlist 约束的 `machine_reason`。常见原因及处理如下：

| `machine_reason` | 含义／下一步 |
|---|---|
| `expected_target_package_absent` | 目标 App 不在当前 accessibility window；回到目标 App 的待采集状态并使用新的 capture ID |
| `sensitive_accessibility_node_present` | 发现 password 或 API 34 sensitive node；停止采集该状态，不绕过隐私门 |
| `accessibility_tree_incomplete` | 树超过采集上限或不完整；该状态不可进入 CAP-001 |
| `synchronization_delta_exceeded` | tree／screenshot 时间间距超过 3000 ms；稳定页面后以新 capture ID 重试 |
| `tree_hash_drift` / `accessibility_event_drift` / `focus_drift` | 前后状态或 TalkBack 焦点发生变化；不得把该 bundle 当作同步证据 |
| `screenshot_error_<code>` 或图像转换错误 | 平台截图能力／buffer／PNG 失败；先检查 runtime capability，不降级为异步截图 |
| `capture_already_in_flight` 或 collector exception | 并发或 collector 运行异常；保留日志诊断，不生成正式候选 |

设备端会保留该 capture ID 的拒绝记录以供诊断，因此重试必须生成新的 capture ID 和
nonce；不得编辑拒绝记录后重新提交。

7. 用同一个 request、公开 commit 对应的本地 APK 和 `apksigner`，逐字节比较设备已安装 APK，并生成独立 host attestation：

```bash
.venv/bin/python3 \
  collector-android/host_capture.py \
  --adb /path/to/adb --serial <serial> attest \
  --request-json collector-android/request.example.json \
  --collector-apk /path/to/app-debug.apk \
  --apksigner /path/to/android-sdk/build-tools/35.0.0/apksigner \
  --source-revision <40-char-public-commit-sha> \
  --output incoming/PMAB-A-CAP-001/collector-attestation.json
```

该命令要求本地 APK 与 `pm path org.pmab.collector` 指向的已安装 APK 字节级 SHA-256 相同、DEX 含预期 source revision 且不含 `uncommitted`，并从 `apksigner --print-certs` 读取 signer certificate SHA-256。人工 `review.json` 中的两个哈希必须与该 attestation 一致。

## 输入 bundle

V1.1 每个私有 bundle 必须包含三类彼此分离的证据：

- `request.json`：采集 ID、item/group/template、冻结抽样层、目标包与 nonce；
- `machine-capture.json`：运行时 capability/flags、设备/App/locale、Git source revision、单调时序、前后树状态和 artifact hashes；
- `review.json`：独立于采集器填写的授权、隐私、再分发、屏幕阅读器和 APK/签名证书哈希复核；
- `collector-attestation.json`：主机对本地/已安装 APK、source revision 和签名证书的独立绑定；
- `screenshot.png`、`tree-before.json`、`tree-after.json`。

从 `collector-android/review.example.json` 复制人工复核模板。原始 bundle 应放在 Git 忽略的 `incoming/` 或 `private/`。不接受 UIAutomator dump、RICO semantic JSON、OCR 或模型输出冒充正式 accessibility snapshot，也不接受采集器自报 `privacy_review_status=passed`。

## 单条终结

在项目根目录运行：

```bash
.venv/bin/python3 \
  popup-solution/dataset-v1/android-capture/finalize_android_capture.py \
  finalize-collector \
  --bundle popup-solution/dataset-v1/android-capture/incoming/PMAB-A-CAP-001 \
  --output popup-solution/dataset-v1/android-capture/results/CAP-001.finalized.json
```

输出只保留标识符、同步结果、授权状态、文件哈希／大小和 window/node 计数，不复制原始 screenshot 或 node text。单条成功状态仅为 `eligible_for_capture_feasibility`。
终结输出以 `0600` 权限、同目录临时文件加原子 no-overwrite 链接写入；目标 receipt
已存在时退出码为 2，并保持原文件逐字节不变。重跑必须使用新的输出路径，不能覆盖
已经审计的 receipt。

## 聚合门

创建一个 JSON array，元素为相对于该清单文件的私有 bundle 目录。聚合命令会逐 bundle 重新读取请求、机器记录、人工复核、截图和前后 accessibility tree，重新运行全部单条门并重算哈希；它不接受只含 record 的 JSON：

```bash
.venv/bin/python3 \
  popup-solution/dataset-v1/android-capture/finalize_android_capture.py \
  audit-collector \
  --bundle-list popup-solution/dataset-v1/android-capture/incoming/bundle-list.json \
  --output popup-solution/dataset-v1/android-capture/results/feasibility-audit.json
```

聚合门以私有 bundle 为输入并现场生成完整终结记录，手工拼写一个 `eligible` 状态或随机哈希不能通过正式 CLI。离线终结器会从实际 window/node 字段和有序 child IDs 重新计算与 Android `CanonicalStateHasher` 相同的 typed canonical tree hash（`null` 与字面字符串分离），再分别核对树内自报值与机器时序记录；它还验证 collector 值域和父子路径，并从节点重算 package 集与焦点 token。只同步改写文件 SHA-256 或多个自报字段不能绕过该门。它要求至少 5 个 source groups、3 个 popup template families，并覆盖 `popup_candidate`、`no_popup_candidate`、`boundary_candidate` 三层；capture ID、截图哈希和 canonical tree hash 均不得重复。通过后也只是 `ready_for_real_g1_pilot`，下一步仍须进行独立、盲式真人 G1 标注。

## 回归

```bash
.venv/bin/python3 -m unittest \
  popup-solution/dataset-v1/android-capture/tests/test_capture_finalizer.py -v
```

权威合同见 [`CAPTURE_CONTRACT_V1.json`](./CAPTURE_CONTRACT_V1.json)，当前零样本状态见 [`PUBLIC_FEASIBILITY_STATUS.json`](./PUBLIC_FEASIBILITY_STATUS.json)。

## 仍未关闭的边界

- 当前 ADB 设备列表为空；collector 从未在真机或 emulator 上安装、启用或采集。
- Android lint 在首次运行中于回传终态前被人工中止，但已生成 `0 errors, 3 warnings` 报告；三条 warning 修复后重新运行正常 exit 0，最终报告为 `No issues found`。
- FileObserver 事件丢失现由同一 worker 每 2 秒扫描 app-private pending requests 兜底；真实设备上的可靠性仍需 dry run 回证。
- 完整 finalizer 能校验文件、时序、字段约束，独立重算 window/node canonical commitment、package 集和焦点 token；host attestation 能逐字节绑定本地与已安装 APK。但 API 34 `isAccessibilityDataSensitive()` 没有逐节点序列化字段，离线端不能独立重算该位；恶意 collector 的整体诚实性也不能由 bundle 自证。因此仍要求公开 commit、人工操作记录和可复现构建，不能把 `tree_hash_verified` 表述成完整隐私／provenance 证明。
- CAP-001 通过仍不等于 popup 标签正确、不等于方法指标、更不等于视障用户体验改善。
