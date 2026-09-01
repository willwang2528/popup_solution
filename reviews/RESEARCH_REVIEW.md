# Independent Research Review：PMAB-Android V1

> 日期：2026-09-01
> 执行者：Codex / OpenAI family
> 独立 reviewer：Claude Sonnet 5 / Anthropic family
> 状态：cross-family review completed and accepted as a review trace
> 研究结论：`PROCEED_WITH_CAUTION / pre-empirical`
> 注意：评审接受的是研究设计可以进入 pilot，不是接受效果主张；human gold=0、formal benchmark item=0、paper result=0。

## 审阅范围

只提交了 V1 问题边界、可证伪主张、标注协议、G1/G2 gold 分离、方法族和实验计划。没有提交密钥、个人信息、飞书原文、原始媒体、未过隐私闸的派生文本或无关仓库文件。

V1 被严格限定为：在冻结动作前移动状态中判断目标 popup 是否存在，并重建屏幕可见的事实消息。关闭弹窗、焦点／页面／任务 Recovery、用户体验、权限安全控制和多步工作流不在 V1。

## 三轮结论

| Round | Reviewer verdict | Score | 主要问题 | 处理结果 |
|---|---|---:|---|---|
| 1 | `STRONG_REJECT_PRE_EMPIRICAL` | 1.5/5 | 数据锚不匹配、边界／gold／预算不充分、把工程 pilot 写得过强 | proposal 收缩到 PMAB-Android，PopSweeper/RICO 降为协议 pilot |
| 2 | `PROCEED_WITH_CAUTION` | 2.0/5 | 科学锚点被认可；剩余唯一 fatal flaw 是 G2 冲突处理未定义 | 加入 versioned G1 correction + G2 restart + cannot_resolve fail-closed |
| 3 | `PROCEED_WITH_CAUTION` | 3.5/5 | fatal flaws=0；三项非阻断实验修订 | 明确 K 比例、主确认比较与多重比较控制 |

## Round 3 关键判断

### G2 fatal flaw 已关闭

Reviewer 确认以下层级可审计且 fail closed：

1. screenshot 是可见事实来源；
2. G1 是冻结的截图事实 gold；
3. G2 只比较 structure 与 G1，不另造竞争真值；
4. 普通 G2 分歧无法解决则 `cannot_resolve`；
5. G2 发现 G1 实质错误时不能改写，必须退回版本化 G1 修正，生成新 hash 后从头重启 G2；
6. 方法 prediction 与 gate reason 始终不可见。

### 显式 out-of-scope 是正确修复

Reviewer 同意 `out_of_scope + predefined reason` 防止 CAPTCHA、风控、认证、支付、权限安全控制与人工审核被塞入 `uncertain`，从而污染 ambiguity rate 或主指标。它是已裁决 disposition，但永不 metric eligible。

Reviewer 建议进一步说明系统权限对话框边界。根据用户已冻结的 V1 范围，本研究明确：OS 级权限对话框与 App 内权限／安全控制均 `out_of_scope`。这是范围选择，不代表它们不重要。

### 实验计划无剩余 fatal flaw

Reviewer 认为当前计划在 pre-empirical 阶段可执行，理由包括：

- 真实同步 Android capture 硬门；
- 5+ App/source groups、3+ template families；
- pilot 后按 gap prevalence 与 cluster structure 冻结 N；
- G1/G2 双人独立 + 第三人裁决；
- K25/K50/K100 operating points；
- null、vision-win、structure-ceiling 的预注册出口；
- privacy/license release gate。

三项非阻断修订已经落地：

1. K25/K50/K100 明确为冻结 item 集上最多 25%/50%/100% 的视觉调用比例；
2. 主确认比较固定为 MG-PU vs seeded random-K at K50，用于 power/precision 规划；
3. 次级比较采用 Holm，探索性分层采用 BH-FDR `q=0.10`。

## 允许与禁止的主张

允许：

- popup presence 与 visible-message factual correctness；
- structure vs vision 的 matched-budget 比较；
- 真实 gap prevalence 与类别分布；
- 只有实验通过预注册门时，才能报告 gate 的 allocation benefit。

禁止：

- 真实用户体验改善；
- 消息对视障用户决策充分；
- accessibility remediation；
- popup dismissal 或 focus/page/task Recovery；
- 权限／安全控制建议；
- iOS 或跨平台泛化；
- 未运行前宣称方法优于基线、数据集已经发布或研究是 broad first。

建议在论文中固定声明：本 benchmark 测技术事实消息提取准确率，不等于用户体验、可访问性改善或消息可用性；V1 排除关闭、恢复与多步交互。

## 最终执行门

当前可以进入 feasibility pilot，但不得直接扩到正式 N。以下状态保持真实：

- 正式同步 Android item：0；
- 真人 G1/G2 gold：0；
- 正式 baseline/method score：0；
- 公开经验数据集：NO-GO；
- 研究文档、协议与代码：完成发布审计后可公开。

停止／转向条件继续绑定：真实同步 capture 不可行则停止主实验；G1/G2 agreement 不过门则停止相应 gold；真实 gap <10% 或少于 20 个 non-synthetic positives 则转 structure-sufficiency measurement；方法比较不过门则撤销 superiority。

## Android capture gate 增量审阅

公开实现完成后，又在同一 Claude thread 中进行了三次最小化增量审阅。最终结论为 `TOOLING_GATE_CONVERGED`，但只针对 CAP-001 离线软件门，经验主张变化为 `NONE`。

审阅过程保留了一次重要纠错：Claude 首轮认可工具门后，Codex 反向检查发现 nested node 中的 label/prediction key 可绕过顶层检查，且聚合器仅凭手写 `eligible` record 可放行。新增失败测试后，代码改为递归拒绝标签／预测键，并完整校验每条终结记录。Claude 随后给出 `VERIFIED_FIX`，但又过度声称“随机 SHA-256 无法伪造”；Codex 指出任意 64 位十六进制串都能通过形状检查。正式 CLI 因此再次收紧为只接受私有 metadata 路径清单、逐 bundle 重新读取 artifact bytes、重新终结并重算哈希，彻底移除 `--records` 入口。

最终审阅确认：路径穿越、直接 symlink、目录 symlink escape、重复 resolved path、重复 capture ID、重复截图哈希和重复结构哈希均 fail closed；12 条 capture gate 测试通过。它同时明确软件门的能力边界：它能证明当前磁盘 artifact 存在、格式与声明一致，不能密码学证明 collector、授权、时间戳、稳定状态 token 或 AccessibilityService 来源声明真实。后者需要开源 collector、可复现构建、运行日志和人工／流程审计。

因此当前状态仍是：真实 capture=0、human gold=0、paper result=0。增量审阅不允许提前宣称 capture feasibility 已实证通过。

## 真实 Android collector 增量审阅

在离线门之后实现了 Android 30+ `AccessibilityService` 采集器、app-private request/readback、`tree-before → screenshot → tree-after` 单调时钟回证，以及机器记录与人工 `review.json` 分离的 V1.1 终结协议。

第 7 次 reviewer 调用尝试让 Claude 限定读取采集器源码和测试，但 600 秒后明确超时，没有返回任何审阅文本；该次调用保持 `provisional/failed_timeout`，不能算 cross-family 接受。随后第 8 次调用改成不使用 repository tools 的自包含 bounded design/contract review，Claude 明确声明这不是 fresh source-level verification，并给出 `PROCEED_TO_ONE_DRY_RUN`。

该结论只允许在一台已授权 Android 设备上做一个 dry run，不能直接进入 5-group gate。Claude 认为 dry run 前没有已识别的 fatal blocker，同时要求 5-group gate 前关闭以下问题：完成或重跑 Android lint；独立计算并核对实际安装 APK 与签名证书哈希；把 Git SHA/可复现构建继续视为信任边界；记录 TalkBack 导致的 `focus_drift` 拒绝率；为 FileObserver 事件遗漏增加可靠性策略；在真实 OEM/Android 设备上核对 runtime capability/flag bits。

审阅后已进一步加入三项不依赖设备的修复：服务用同一 worker 每 2 秒扫描 app-private pending request，兜底 FileObserver 事件遗漏；主机新增 `attest` 命令，逐字节比较本地与已安装 APK、核对 DEX source revision、从 `apksigner` 读取证书哈希，V1.1 finalizer 再与人工 review 交叉绑定；Android lint 的 3 条 warning 修复后重新运行正常 exit 0，最终为 `No issues found`。真实 OEM capability、TalkBack focus drift 和设备端安装 APK 读取仍需 dry run 实证。

经验主张变化仍为 `NONE`。真实 capture=0、human gold=0、method metrics=0；`PROCEED_TO_ONE_DRY_RUN` 只说明设计合同足以尝试一次安全、授权的真实采集。

## 视觉 bank 与等预算基线增量审阅

第 9 次调用只披露 V1 边界、固定阈值协议、聚合计数、哈希、重放结果和五方法路由／调用计数；没有发送截图、OCR 原文、逐项 ID、私有 prediction 或人工标签。Claude 给出 `PROCEED_WITH_MANDATORY_FIXES`：没有发现已证实的泄漏或正确性致命缺陷，但要求公开推送前去掉两个过强命名。

修正后，Apple Vision 证据只声明 `repeat_execution_byte_identical_on_fixed_host=true`，跨 OS／设备模型身份保持 `not_verified`；方法只称为冻结的固定阈值、positive-or-abstain 启发式 adaptation，不再称为 formal/canonical/validated baseline。C1-BM 明确只匹配调用成本，不匹配 item 集或难度；MG-PU 的“28 次视觉调用”也拆成 4 次形成视觉正判断、24 次视觉 adapter 弃答。

同时新增两类 fail-closed 回归：物理删除 `popup_present_gt`、stratum、source ID 后输出必须不变；新增未登记 manifest／artifact 字段则整批拒绝。修正后的 30 项本机重放仍为 4 judged、26 abstain，逐项决定／ROI／消息在排除运行时字段后相同。经验主张变化仍为 `NONE`。

## PMAB 合同与受控 fixture 增量审阅

第 14 次调用只披露聚合的 V1 边界、255 字段计数、正式 K50 输入门、受控 Android fixture 构建事实和全部为零的经验计数；工具关闭，没有发送截图、消息文本、逐项数据、人工标签、凭据或私有文件。Claude 判断 V1 不可观测上限、broad-first 撤回、synthetic union item 和 formal K50 fail-closed runner 均没有新增强制问题，也明确指出这些事实不支持 empirical、superiority、usability、dismissal 或 Recovery 主张。

唯一强制问题是 `device_capture_ready=true` 的字段名会脱离 README 被机器读取，从而把“安装前条件已具备”误写成“设备采集已验证”。该字段已测试先行拆成：

- `installation_prerequisites_ready=true`；
- `device_capture_validated=false`。

Validator 要求前者为 true，并在后者被改为 true 时 fail closed；catalog、机器摘要和 README 均使用同一命名。第 15 次同线程复核确认强制修改已满足，最终 verdict 为 `PROCEED`，mandatory blocker 为 0。经验主张变化仍为 `NONE`；真实 Android capture、human gold、formal result 和 paper result 继续全部为 0。

## CAP-001 正式 item 与 K50 冻结链增量审阅

第 16 次调用只发送了非私有的合同与测试摘要，工具关闭。审阅前 Codex 发现
formal item materializer 仅凭 `record_kind=real_app` 可能把归档
`partial_device_evidence` 误送进正式评测，因此先增加逐项 CAP-001 绑定和负向测试：
正式 item 必须是 `full_device_evidence`，来自真实设备或 emulator、隐私复核通过、
使用同步 `AccessibilityService` snapshot，并绑定 finalized capture record、截图和
accessibility snapshot 三类 SHA-256；formal runner 会再次独立校验。

Claude 认为该修复关闭了已识别的 partial-evidence 绕过，G1/G2 gold 独立性、K50
预测冻结哈希链和 V1 无动作／无 Recovery 边界没有新增强制问题，最终 verdict 为
`PROCEED`，mandatory blocker 为 0。非阻断 hardening 是：真实采集出现后，必须保留
由私有原始 bundle 实际终结出的 capture record，并确认 formal item 校验的是该原始
终结产物的 hash，而不是后续编辑副本。

该审阅不改变经验状态：真实 capture=0、human G1/G2=0、formal K50 result=0，不能
宣称数据集完成、方法优越、可用性改善、弹窗消除或 Recovery。

## 正式多重比较与 Pareto 合同增量审阅

第 17 次调用只发送了 V1 边界、预注册统计口径、冻结注册表摘要、fail-closed
约束、聚合测试结果和全部为零的经验计数；工具关闭，没有发送逐项内容、截图、
消息文本、人工标签、凭据或无关仓库材料。Claude 给出 `PROCEED`，mandatory
blocker 为 0。

Reviewer 确认 Holm step-down 与 BH step-up 公式正确；少于 5 个 group 的分层行必须
保持 descriptive-only，同时以 `p=1` 留在完整冻结 family 中，避免通过删减低样本行
缩小校正族。质量—覆盖—成本 Pareto 采用“所有维度不差且至少一维严格更好”的
dominance 定义。当前尚未实现的 method/operating-point 也必须保留在 gold 前冻结的
注册表内，后续若要改变只能走显式修订，不能静默删除。

审阅同时确认，主计划在数据产生前把含糊的“corrected CI”澄清为“Holm-adjusted
`p<.05` 且原始逐比较 paired cluster-bootstrap 95% CI 排除 0”是可辩护的。其非阻断
建议已落实为机器可读字段
`ci_adjustment_status=unadjusted_per_comparison_cluster_bootstrap_95ci`，防止未来报告
把该 CI 错称为同时校正区间。

该审阅不产生经验结果：真实 capture=0、human G1/G2=0、formal supplementary
analysis receipt=0、paper result=0；不得据此宣称 superiority、usability、dismissal
或 Recovery。

## 299 字段、shuffled-gap 与 collector 语义增量审阅

第 18 次调用在用户明确授权后，只发送了 299 行字段归因、ABL-003 shuffled-gap
合同、collector rejected/no-overwrite 行为、聚合测试结果和全部为零的经验计数；工具
关闭，没有发送逐项 ID、截图、OCR/UI 文本、私有 prediction、人工标签、凭据或无关
文件。Claude 给出 `PROCEED`，mandatory fix 为 0。

Reviewer 确认 `90 literature + 165 our-method = 255 source-attributed` 与另计的
`44 non-source-attributed V1 protocol extensions` 合成 299 行的说法准确，不把新增
协议字段误归因给已有论文。它也确认 rejected bundle 退出码 2、partial 清理、不得
发布到成功路径，以及 0600 atomic no-overwrite receipt 足以作为 tooling evidence；
但真实设备／模拟器运行仍为 0，CAP-001 与 empirical readiness 均未解锁。

ABL-003 被接受为 gold 前冻结的 equal-visual-budget ablation，同时形成必须保留的
论文 caveat：它把同一批由内容产生的 gap reasons 一一置换到其他 item，隔离的是
“gap reason 与 item 的正确绑定”是否提供超越 gap 分布本身的信号；它不是完全内容
盲的随机策略，必须与 seeded-random 对照区分。当前 6 judged 对 4 judged 只是未评分
的路由／输出计数，不是准确率、显著性或优越性结果。

## Trace metadata

- Review thread：`3d76b654-220f-41c8-965d-424b0be7c2c8`
- Round 1 job：`579cc0159bd8439486de5670c8fb2631`
- Round 2 job：`d1015d7c106d4593a85be63da5d359e8`
- Round 3 job：`1c4fe530e2c841fe9ce7a6505397ac9b`
- Android gate review job：`8939bb2d516544ba9cebdd2126da555c`
- Fail-closed recheck job：`5cc4019879de44d2a9b9b10b06c39fda`
- Artifact-binding final job：`9c58eb567dd9407b9e7aa10c4949d726`
- Real collector source-reading job（timeout/provisional）：`48b3db97d19b433796ec20462c8a5ead`
- Bounded collector review job：`5a97eb92f2c04a1fb9c682440950bca0`
- Visual bank / C1 fatal-gate job：`762b47f9867245b18f082a33d2b16164`
- PMAB contract / union / K50 / fixture gate job：`43d3cd07957a4cc9acd55261ff325eea`
- Fixture readiness-field recheck job：`4161a87c339f48e3b696f6d317f8e5d3`
- Formal CAP-001 / K50 freezer review job：`15b95afc3e984fd2b49840eb43367901`
- Formal multiplicity / Pareto review job：`f5cdc8e10e704d459d917eb361dd50da`
- Item union / shuffled-gap / collector review job：`0f09af5714984c178d5fb044b3c152f8`
- Local complete trace：`.aris/traces/research-review/2026-09-01_run01/`

完整请求／回复／模型／时间／任务标识保存在本地 trace；本公开文档只保留最小化、可审计的研究结论与标识。
