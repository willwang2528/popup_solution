# Pending empirical union pilot

This directory materializes the frozen 30-item pilot into the complete
`dataset-v1/schema/item.schema.json` union shape **before human annotation**.
It is a lifecycle artifact, not a scored dataset release.

## Input boundary

The materializer accepts only:

1. the private, gold-blind structured feature bundle; and
2. optionally, the private frozen pre-gold prediction bundle.

There is deliberately no raw-manifest argument. Feature and prediction records
are checked against strict allowlists and fail closed on source labels, sampling
strata, ground truth, human annotations, adjudication, metric eligibility, raw
artifact routing, or any positive claim that gold was used.

## Pending-item semantics

Every output row is a complete union item with:

- `record_kind=real_app`, meaning an **archived real-app source observation**;
  this does not claim a newly executed or verified real-device episode;
- source device kind, OS, model, app/package, screen-reader state, and other
  unavailable environment facts remain null/not observable rather than being
  inferred from the archive;
- `collection_status=collected` and `split=pilot`;
- all scenario, popup, candidate, and message ground truth empty/null;
- `message_text_observability=pending_annotation`, a lifecycle sentinel rather
  than a label value;
- empty annotation and action arrays;
- all v1, advanced-recovery, training, and user-experience eligibility disabled
  with `pending_human_annotation` as the exclusion;
- advanced dismissal, focus, context, task, VTR-tech, and A-VTR values null and
  not observable;
- an optional frozen prediction only when it remains schema-stable without
  inventing confidence. A connected prediction is still gold-blind, unscored,
  action-free, and ineligible for paper results.

The materializer calls the project validator as an imported module. It validates
the schema, item invariants, and dataset invariants in memory and does not invoke
the validator CLI or overwrite `dataset-v1/validation-result.json`.

## Privacy and publication boundary

Text-bearing union items are written only to `private/*.private.jsonl`. The
directory is Git-ignored and set to mode `0700`; the bundle is `0600`.
`PUBLIC_PENDING_UNION_SUMMARY.json` contains only aggregate counts, field
coverage, hashes, and negative-claim attestations. It contains no item IDs, UI
text, source paths, or per-item predictions.

## Rebuild

From `popup-solution/` with the canonical project interpreter:

```bash
../.venv/bin/python3 \
  dataset-v1/empirical-pilot/materialize_pending_union.py \
  --features experiments/v1-message/features/private/pilot-30.features.private.jsonl \
  --pregold-predictions experiments/v1-message/pregold/private/pilot-30.predictions.private.jsonl \
  --private-output dataset-v1/empirical-pilot/private/pilot-30.pending-union.private.jsonl \
  --public-summary dataset-v1/empirical-pilot/PUBLIC_PENDING_UNION_SUMMARY.json \
  --expected-count 30
```

Run the behavior tests with:

```bash
../.venv/bin/python3 -m unittest \
  dataset-v1/empirical-pilot/tests/test_materialize_pending_union.py -v
```
