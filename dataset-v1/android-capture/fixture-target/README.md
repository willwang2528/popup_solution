# Android controlled-fixture 场景目录

本目录包含可控 target app 的 Android module 和机器可读场景矩阵。`FixtureActivity` 按 `scenario_id` 渲染 centered dialog、bottom dialog、fullscreen dialog 三类模板，并为每个 app flavor 提供 popup、no-popup、boundary 三种只读观察状态。它不会自动点击、关闭或发出 gold label。

`SCENARIO_CATALOG_V1.json` 冻结了 5 个相互独立的受控 package/app group、3 个 UI 模板族，以及每组各自的 `popup_candidate`、`no_popup_candidate`、`boundary_candidate`，合计 15 个启动场景。所有条目仍为 `definition_only`，目录整体固定为：

- `implementation_status = android_target_implemented`
- `installation_prerequisites_ready = true`
- `device_capture_validated = false`
- `cap001_eligible = false`
- `paper_result_eligible = false`
- `human_gold_eligible = false`
- `real_device_accessibility_verified = false`
- `real_capture_bundle_count = 0`
- `human_privacy_reviews_completed = false`

验证目录：

```bash
.venv/bin/python3 \
  popup-solution/dataset-v1/android-capture/fixture-target/validate_fixture_catalog.py \
  --catalog popup-solution/dataset-v1/android-capture/fixture-target/SCENARIO_CATALOG_V1.json \
  --implementation-contract popup-solution/dataset-v1/android-capture/fixture-target/TARGET_BUILD_CONTRACT_V1.json \
  --summary-json
```

运行契约测试：

```bash
.venv/bin/python3 -m unittest discover \
  -s popup-solution/dataset-v1/android-capture/fixture-target/tests \
  -p 'test_*.py' -v
```

构建并运行五个 flavor 的 JVM 测试：

```bash
ANDROID_HOME="$PWD/.tmp/android-sdk" \
GRADLE_USER_HOME="$PWD/.tmp/gradle-user-home" \
gradle --no-daemon \
  :fixtureTarget:testCommerceDebugUnitTest \
  :fixtureTarget:testMediaDebugUnitTest \
  :fixtureTarget:testTravelDebugUnitTest \
  :fixtureTarget:testProductivityDebugUnitTest \
  :fixtureTarget:testEducationDebugUnitTest \
  :fixtureTarget:assembleDebug
```

检查实际 APK 的五个 package 和 launchable Activity：

```bash
PMAB_FIXTURE_APK_ROOT="$PWD/popup-solution/dataset-v1/android-capture/fixture-target/build/outputs/apk" \
PMAB_AAPT2="$PWD/.tmp/android-sdk/build-tools/35.0.0/aapt2" \
.venv/bin/python3 -m unittest \
  popup-solution/dataset-v1/android-capture/fixture-target/tests/test_built_fixture_apks.py -v
```

## 尚未完成的设备验证

1. 在模拟器或真机安装 target APK 与 PMAB Collector，同时保持 TalkBack 等目标屏幕阅读器启用。
2. 逐类确认 Activity 中的真实 Android View/Dialog 出现在系统 AccessibilityService tree，并核对文本、window、bounds、focus 与 resource ID。
3. 对每个场景执行实际 `tree-before → screenshot → tree-after` 采集，并逐条经过人工隐私复核和 `finalize-collector`。
4. 只有真实 bundle 可以进入 CAP-001 聚合；本目录、JVM 测试、APK 构建、UIAutomator dump 或手工 JSON 均不能替代它。

`installation_prerequisites_ready=true` 只表示源码、构建合同和 APK 路由已满足安装前条件；`device_capture_validated=false` 明确表示 accessibility 行为尚未经过真实设备验证。状态改变本身不能生成 CAP-001 资格或 human gold。
