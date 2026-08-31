# PPT 第 14 页证据锚：五级回证边界

> 来源：`deliverables/ppt-format-2026-08-28/mobile弹窗问题调研-v1-formatted-v2.pptx`
>
> 幻灯片：14／18
>
> 标题：`验证：从弹窗消失到任务真正恢复`
>
> 源文件 SHA-256：`c5080b9ba45377520dc9ecb44bddd91973a920915dc132f7b047d97e8f1b43bd`
>
> 核验日期：2026-09-01；核验方式：读取 slide XML 全部可见文本，并检查 2400×1350 最新渲染图。

## 1. 原页结论

副标题明确指出：**五级回证逐步增强；单一画面变化不足以证明原任务恢复。**

| 方法分类 | 回证层级 | 检查方法 | 原页列举 | 能证明什么／不能证明什么 |
|---|---|---|---|---|
| 弱验证 | 弹窗标识消失 | 等待 Alert／Modal／按钮节点不存在 | Android `Until.gone`；Maestro `assertNotVisible` | 只能证明已编码标识消失；文案变化、透明化或跳到新弹窗可能误判。 |
| 弱验证 | 仅截图／日志变化 | 比较点击前后截图、OCR 相似度或系统日志 | WhisperTest；PopSweeper | 页面变化可能来自误点、跳转或动画，不等价于真实关闭或任务恢复。 |
| 强回证 | 原目标与 Context 恢复 | 检查原目标 `visible`／`enabled`／`clickable`／`isHittable`；核对 package、bundle、active app 和当前 Context | UI Automator；XCUITest Driver `activeAppInfo` | 证明回到正确 App／页面／自动化后端，原控件可继续操作。 |
| 强回证 | 业务选择与持久化状态 | 读取弹窗对应业务状态；重启后确认选择仍保存且横幅不再出现 | TCF Android；Abandon All Hope | 证明允许、拒绝或同意等选择真实保存。 |
| 强回证 | 原任务后置条件 | 显式编码目标文本、业务属性或页面状态；弹窗处理后同时满足 | D-GARA | 证明原任务最终达到预期结果。 |

## 2. 对本课题的硬约束

1. **不存在可宣称的统一弹窗解决器。** 弹窗 owner、平台协议、可访问性暴露、视觉呈现和业务语义不同，任何方法都必须限定适用边界。
2. **没有被平台暴露到 UI／组件树的内容，tree-only 方法原则上读不到。** 系统合并、过滤、权限限制和开发者漏标均可造成不可观测性；算法不能从不存在的结构证据中恢复事实。
3. **视觉兜底只能扩展可观测范围，不能自动升级为强回证。** 像素可帮助识别屏幕可见消息，但不能单独证明 owner、用户意图、业务持久化或原任务完成。
4. **弱验证不能冒充 Recovery。** `node gone`、截图变化或日志变化只能作为局部证据，不能支持“任务已恢复”的论文结论。
5. **完整 Recovery 必须分层报告。** 后续动作实验至少分开记录弹窗消失、原 Context、可访问性焦点、业务状态和任务后置条件；不得压成单一 success bit。

## 3. 当前 V1 的合理降级

V1 不挑战完整 Recovery，也不执行点击。它只研究动作前的：

- 弹窗存在性判断；
- 屏幕可见消息的可访问重建；
- 结构化 UI 缺口检测；
- 必要时的视觉消息补全；
- 关键事实保护、置信度和弃答。

因此 V1 的“Recovery”只可解释为 **message-level accessibility recovery（消息层可访问恢复）**，不能解释为弹窗消失、焦点恢复或原任务恢复。

## 4. 论文定位

在完成查新和真实实验以前，三项贡献都必须写成待验证命题：

1. 是否首次把“移动弹窗消息不可观测性对屏幕阅读器用户的影响”形式化为独立研究问题；
2. 是否形成首个具有结构／视觉证据、暴露缺口和消息真值的公开评测数据集；
3. message-gap-gated 方法是否在同一数据、同一冻结 observation 和同一预算下优于 structure-only、vision-only 与 always-on fusion。

“第一个”和“效果更好”只能由系统查新、公开数据集发布和可复现实验结果支持，不能由本页或研究动机直接推出。

## 5. 进阶层

如果后续启动 `dismissal_recovery_advanced`，必须使用本页的五级回证表作为最低报告结构，并把以下指标分开：

```text
D: popup disappearance
C_tech: owner / page / context restored
C_a11y: screen-reader focus and reading flow restored
B: business choice persisted
T: original task postcondition satisfied
```

V1 的消息准确率 `VPMA` 不能推导上述任何一项成功。
