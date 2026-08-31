# PMJ Pilot 30 — Model Preannotation A Summary

## Status

- `annotator_type`: `AI model`
- `annotator_id_pseudonymous`: `AI-MODEL-A`
- `not_human_gold`: `true`
- `metric_eligible`: `false`
- This artifact is an independent, screenshot-only model preannotation. It is **not human gold**, is **not adjudicated**, and must **not** be used in protocol-agreement or empirical metric computation.

## Blinding and input boundary

The annotation used only the frozen annotation guide, the pilot README, the blank Annotator A template, and the 30 per-item `popsweeper-screenshot.jpg` images. It did not inspect coordinator/candidate manifests, source labels or paths, peer annotations, model predictions, agreement outputs, or any `popup_present_gt` field.

All 30 screenshots were inspected individually with the image viewer. No screenshot was copied into the annotation file or report.

## Record schema used

Each JSONL record preserves the template's `pilot_item_id`, `adapter_item_handle`, `annotation_order`, `batch_id`, blinding attestation, and evidence discipline, while explicitly marking the result as model-only. The requested added fields are:

- `blocking_label`: `blocking | non_blocking | null`; it is `null` unless `presence_label=popup`.
- `ambiguity`: `{level: none|low|medium|high, note: string|null}`.
- `not_human_gold=true` and `metric_eligible=false` on every record.

Message and semantic-slot fields follow the pilot protocol. `message_text` contains only visible popup text in a reasonable reading order; host-page text is excluded unless a second visible popup layer also independently satisfies the popup definition.

## Preannotation distribution

- Total: 30
- `popup`: 19
  - `blocking`: 17
  - `non_blocking`: 2
- `no_popup`: 10
- `uncertain`: 1
- `unusable`: 0
- Message observability among popup items: `complete=15`, `partial=4`, `not_observable=0`

The one `uncertain` item is `PMJ-PILOT-020`: a single screenshot cannot reliably distinguish a transient host splash/loading layer from an interrupting popup message. Authentication/permission full pages were treated as outside target popup scope; embedded banner advertisements were not treated as interrupting popups.

## Eligibility warning

This preannotation is a workflow aid only. It must remain separate from human A/B annotations and adjudication. It cannot unlock, replace, seed, or otherwise influence human gold, and it is not eligible for κ, message-agreement, VPMA, or downstream performance metrics.
