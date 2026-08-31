# Exploratory paired comparison statistics

This directory contains the **post-gold scoring contract**, not an experiment
result. It preserves the v1 boundary: popup presence and message judgment only,
with `no_action`, no dismissal, no Recovery, and no user-experience claim.

## Frozen-input chain

The comparison CLI requires four private, pre-existing inputs:

1. the 30-item pending-union bundle with stable `pilot_item_id` values;
2. one complete final human-adjudication row per pilot item;
3. the pre-gold prediction bundle, scored without rerunning any method; and
4. a private group map built after prediction freeze and never used as model
   input.

Optional method-output semantic adjudication is prediction-row-hash bound. If it
is absent, VPMA remains `normalized_exact_proxy`; if it is present, every
eligible positive output for every compared method must be covered, otherwise
the run fails rather than mixing proxy and human judgments.

## Pilot group map

Build the private statistical group map from the frozen pilot manifest:

```bash
../../../.venv/bin/python3 -m popup_eval.group_map \
  --manifest ../../dataset-v1/annotation-pilot/manifests/pilot_batch_30.jsonl \
  --private-output statistics/private/pilot-30.group-map.private.jsonl \
  --public-summary statistics/PUBLIC_GROUP_MAP_SUMMARY.json \
  --expected-count 30
```

The builder uses connected components over `group_key` and `content_key`. The
current pilot produces 30 singleton clusters, so it does **not** establish a
formal near-duplicate/app/template leakage control. The public summary contains
only counts and hashes; the row-level map remains Git-ignored with mode `0600`.

## Paired scorer

After real human gold and, optionally, blind semantic output review exist:

```bash
../../../.venv/bin/python3 -m popup_eval.comparison_cli \
  --items ../../dataset-v1/empirical-pilot/private/pilot-30.pending-union.private.jsonl \
  --annotations /private/path/final-adjudication.jsonl \
  --predictions pregold/private/pilot-30.predictions.private.jsonl \
  --group-map statistics/private/pilot-30.group-map.private.jsonl \
  --semantic-annotations /private/path/semantic-output-adjudication.jsonl \
  --method-id structured-only-v1 \
  --method-id the-ok-text-rule \
  --method-id mg-pu-gated-union-v1 \
  --proposed-method-id mg-pu-gated-union-v1 \
  --strongest-baseline-method-id structured-only-v1 \
  --bootstrap-replicates 10000 \
  --seed 20260901 \
  --output statistics/comparison_summary.json
```

The reference baseline must be explicitly declared; the test set never selects
it automatically. Bootstrap draws are deterministic
`sha256-counter-mod-v1`, sample whole clusters with replacement, and report a
type-7 percentile 95% interval for the paired difference in VPMA overall
success, where abstention/null counts as failure.

Every pilot report remains `analysis_tier=exploratory_pilot` and
`paper_result_eligible=false`. B2 exact PopSweeper remains NO-GO, B1 is not yet a
formal popup-ROI baseline, and no comparison output exists until real human gold
is completed.
