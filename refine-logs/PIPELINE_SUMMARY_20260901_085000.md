# Pipeline Summary：PMAB-Android V1

**Problem**：Android popup 的可见消息与 TalkBack 可获得结构之间可能存在 exposure gap。
**Method thesis**：只在结构消息不足时分配视觉预算；收益必须在同预算下实证，允许 null/negative。
**Verdict**：`PROCEED_WITH_CAUTION`
**Review**：3-round Claude cross-family review completed；fatal flaws=0；readiness=3.5/5。
**Evidence**：pre-empirical；0 human gold，0 formal item，0 paper result。

## Completed pipeline artifacts

- source-bounded literature + residual novelty search；
- 90 literature fields + 165 method fields = 255-field item union；
- observable popup scope、explicit out-of-scope、G1/G2 protocols；
- 30-item annotation/infrastructure pilot 与 fail-closed readiness；
- action-free baseline/evaluator/pregold scaffolding；
- five-block experiment plan and stop conditions；
- independent review trace and public review summary。

## Dominant / supporting contribution

- Dominant：PMAB-Android factual popup-message measurement benchmark。
- Supporting：MG-PU message-sufficiency allocation policy。
- Excluded：自动关闭、权限／安全绕过、UX、Recovery、跨平台外推、新 backbone。

## Next executable gate

真实同步 Android capture feasibility：至少 5 groups、3 template families。通过后运行真人 G1/G2 pilot，并用真实 prevalence/cluster variance 冻结正式 N。未通过则停止 benchmark 主实验，不用 PopSweeper/RICO 或 synthetic 代替。

## Release state

研究文档、协议和代码可以在 clean-clone 内容审计后公开；当前经验数据因 0 human gold、privacy/license/EXIF gate 未完成，继续 NO-GO。
