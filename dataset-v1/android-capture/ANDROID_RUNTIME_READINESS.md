# Android 真实运行环境就绪审计

> 更新：2026-09-01 13:50 +08:00
> 状态：`blocked_no_runtime_device`。本文只记录运行条件，不构成 CAP-001、真实 capture、human gold 或论文结果。

## 当前权威状态

- 主机架构：Apple Silicon `arm64`；项目卷可用空间约 55 GiB。
- 项目 SDK 当前只有 `platform-tools`、Android 35 platform 和 build-tools；没有 command-line tools、`emulator`、`avdmanager` 或 system image。
- `adb devices -l` 在沙箱外正常运行，但设备列表为空。
- 受控 fixture 的 5 个 APK 已构建；collector APK 与离线 finalizer 也已通过源码／构建测试。这些事实只满足安装前条件。
- `installation_prerequisites_ready=true`；`device_capture_validated=false`；真实 capture、人工隐私复核和 human gold 均为 0。

## 两条可执行路线

### A. 授权 Android 真机（优先）

真机最接近 TalkBack 用户环境，也避免下载 emulator/system image。需要操作者：

1. 连接一台授权的 Android 30+ 设备并启用 USB debugging；
2. 安装与公开 commit 绑定的 collector APK 和 fixture APK；
3. 在系统 UI 中人工启用 TalkBack 和 PMAB Collector，不通过脚本改写 secure settings；
4. 逐个启动 fixture `scenario_id`，执行 `tree-before → screenshot → tree-after`；
5. 人工填写独立授权／隐私／屏幕阅读器复核，再运行 fail-closed finalizer。

Android 官方的真机调试步骤要求在设备端启用 USB debugging；TalkBack 官方说明其启用路径会随设备厂商和系统版本变化，因此必须记录设备、Android 与 TalkBack 版本，而不能从 fixture 设计推断运行状态。

### B. Apple Silicon Android Emulator

Apple Silicon 应使用 `arm64-v8a` system image。官方硬件加速文档明确支持 Apple Silicon 与 ARM64 Android system image；AVD 仍需 command-line tools 中的 `sdkmanager` 和 `avdmanager`。

从 2026-09-01 获取的 Android 官方仓库 XML 可得稳定包规模：

| 包 | 版本／路径 | 压缩下载字节数 | 作用 |
|---|---|---:|---|
| Command-line tools Mac ARM | `15859902_latest` | 约 156.1 MB | 提供 `sdkmanager`／`avdmanager` |
| Android Emulator ARM64 | stable `37.1.11` | 394,555,844 | 运行 AVD |
| API 35 default ARM64 image | `system-images;android-35;default;arm64-v8a` | 769,099,654 | AOSP 基础镜像；不保证 TalkBack |
| API 35 Google APIs ARM64 image | `system-images;android-35;google_apis;arm64-v8a` | 1,778,933,980 | Google APIs；不等同已验证 TalkBack |
| API 35 Google Play ARM64 image | `system-images;android-35;google_apis_playstore;arm64-v8a` | 1,789,211,399 | 最可能支持从 Play Store 获得／更新 TalkBack；仍需实机核验 |

采用 Google Play 镜像时，三个核心压缩下载合计约 2.34 GB；解压后的 system image、AVD data 和快照会进一步占用空间，执行前保守预留至少 10 GiB。该预留值是工程估计，不是官方包大小。

2026-09-01 的一次 command-line-tools 官方下载尝试平均约 42 KB/s，只完成约 6.9 MB 后停止；这表明当前网络不足以在合理时间内完成约 2.34 GB 环境准备。保留部分文件不改变任何 readiness 状态。

## Emulator 路线的不可替代回证

安装和成功启动 AVD 后仍必须逐项验证：

- system image 中是否真实存在可启用的 Android Accessibility Suite／TalkBack；
- TalkBack 版本、启用状态与焦点事件；
- collector 的 `AccessibilityService` capability、interactive windows、截图 capability 和 target package；
- fixture 的三类 Dialog 是否以真实 window/node/text/bounds/resource ID 出现在 service tree；
- 前后 tree hash、event sequence 和 focus token 是否满足稳定状态门；
- 原始 screenshot/tree 是否通过独立人工隐私复核。

没有这些运行证据时，不能把“AVD 能启动”写成 screen-reader condition、CAP-001 或 empirical dataset。

## 下一执行条件

- 若出现授权真机：优先执行路线 A 的单条 dry run；成功后再扩到 5 groups × 3 strata。
- 若网络恢复并允许约 2.34 GB 下载：完成路线 B，但先做 1 个场景和 TalkBack presence gate；任一 screen-reader／AccessibilityService 条件不成立即停止，不生成 CAP-001。
- 两条路线均不可用时，继续完善 gold-blind formal pipeline，但数据集与实验结果保持未完成。

## 官方来源

- [Android Emulator 硬件加速与 Apple Silicon／ARM64 要求](https://developer.android.com/studio/run/emulator-acceleration)
- [`sdkmanager` 安装、包路径和许可证说明](https://developer.android.com/tools/sdkmanager)
- [`avdmanager` 创建 AVD](https://developer.android.com/tools/avdmanager)
- [命令行启动 Android Emulator](https://developer.android.com/studio/run/emulator-commandline)
- [在真机运行与 USB debugging](https://developer.android.com/studio/run/device)
- [TalkBack 入门](https://support.google.com/accessibility/android/answer/6283677)
- [启用 TalkBack](https://support.google.com/accessibility/android/answer/6007100)
- [Android Studio／Command-line tools 官方下载页](https://developer.android.com/studio)
