# Model Preannotation B Summary

## Status

- `annotator_type`: `AI model`
- `not_human_gold`: `true`
- `metric_eligible`: `false`
- `not_metric_eligible`: `true`
- Role: independent blind model preannotation B
- Record count: 30

This artifact is a non-human model preannotation only. It is **not human gold**, is **not adjudicated gold**, and is **not eligible for metric computation or empirical claims**.

## Blinding boundary

The preannotation was produced only from:

- `popup-solution/dataset-v1/ANNOTATION_GUIDE.md`
- `popup-solution/dataset-v1/annotation-pilot/README.md`
- `popup-solution/dataset-v1/annotation-pilot/templates/annotator_b.jsonl`
- the 30 fixed local `popsweeper-screenshot.jpg` images addressed by `PMJ-PILOT-XXX`

No pilot manifest, candidate manifest, source-directory class label, preannotation A, peer annotation, or existing `popup_present_gt` was read.

## Model decisions

- `popup`: 19
- `no_popup`: 11
- `uncertain`: 0
- `unusable`: 0
- blocking popup (`blocking_label=true`): 17
- non-blocking popup (`blocking_label=false`): 2
- `message_observability=complete`: 15
- `message_observability=partial`: 4
- `message_observability=not_applicable`: 11

The two non-blocking popup decisions are a bottom status notification and an app-level location-enablement banner. Medium ambiguity is explicitly recorded where a surface could plausibly be interpreted as persistent host content, a splash layer, permission-adjacent UI, or visually truncated ad copy.

## Output

The 30 JSONL records are stored in `popup-solution/dataset-v1/work/model-preannotation-b.jsonl`. Every record independently carries:

- `annotator_type="AI model"`
- `not_human_gold=true`
- `metric_eligible=false`
- `not_metric_eligible=true`
- all three blindness-attestation values set to `true`
- `raw_image_copied=false`

No protocol template or other annotator/model output was modified.
