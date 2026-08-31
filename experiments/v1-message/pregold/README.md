# Pre-gold prediction freeze

This directory freezes deterministic, **gold-blind and unscored** v1 popup-message
predictions before human adjudication. It never computes a metric and never emits
or executes a popup action.

## Safety contract

- The formal item set comes from the sanitized structured-feature JSONL, not the
  raw pilot manifest. The optional `--manifest` input is an ID-only cross-check:
  only `pilot_item_id` is projected, and neither its raw-file hash nor any source
  label, split, stratum, artifact path, provenance, or status is consumed.
- Structured and visual inputs are recursively rejected if they contain ground
  truth, human labels, adjudication, metric-eligibility, source-label, split,
  archive-member, batch, or source-provenance keys. Safe attestations are accepted
  only as `gold_blind=true`, `gold_used=false`, `human_gold_used=false`,
  `scored=false`, and `paper_result_eligible=false`.
- The main freezer does not accept label-shaped model preannotations. The isolated
  adapter accepts only records with `annotator_type="AI model"`,
  `not_human_gold=true`, `metric_eligible=false`, and `record_status="completed"`,
  then projects them into private visual-candidate predictions. Human,
  adjudicated, or metric-eligible inputs fail closed.
- Text-bearing outputs must be named `*.private.jsonl` under a `private/`
  directory. They are written with mode `0600` and ignored by Git. The public
  summary contains only contracts, aggregate counts, routes, hashes, and negative
  claim attestations; it contains no message text, item IDs, or paths.

## Frozen methods

`structured-only-v1` is a deliberately weak baseline. It concatenates visible
structured candidate text across the tree and therefore exposes possible host-page
contamination. With no usable structured text it abstains.

`the-ok-text-rule` ports the consent-dialog decision from the official
`the-ok-is-not-enough/scala-appanalyzer` revision
`b618948c0d24b917b3a46a88f5c1cf6ff84571cd`. It consumes only raw Appium-like
`features.text` from Appium-like structured channels, not DOM/protocol or
normalized icon/class fallbacks. The original rule's
dialog/link/regular/half-keyword corpus and `keywordThreshold=1` are frozen under
`resources/the-ok/`. A rule match predicts popup presence and deterministically
joins only contributing element text as the v1 message; this message projection is
our action-free benchmark adaptation. A non-match with raw text is a judged
negative, while missing raw text abstains.

`mg-pu-gated-union-v1` uses a separately preregistered popup-scope gate:

1. A structured candidate is popup-scoped only when
   `component_label` is `Modal` or `Advertisement`, or when its class/ancestor
   strings contain `Dialog`, `Popup`, or `Overlay` (case-insensitive).
2. Only marker nodes and descendants carrying one of those ancestor markers are
   used to build the structured popup message.
3. No explicit popup scope produces the `ambiguous` gap. Explicit scope with no
   message produces `missing`. Declared gaps such as `merged`, `contradictory`, or
   `stale` also open the visual gate.
4. The visual branch reads only an already frozen visual prediction. A missing or
   unstable mapping abstains; it never fabricates a message.

These rules were frozen before human gold and must not be tuned against later
adjudication.

## Reproduce the 30-item freeze

Use the project interpreter:

```bash
../.venv/bin/python3 \
  experiments/v1-message/pregold/adapt_model_preannotation.py \
  --input dataset-v1/work/model-preannotation-b.jsonl \
  --private-output experiments/v1-message/pregold/private/model-b.visual-candidate.private.jsonl

../.venv/bin/python3 \
  experiments/v1-message/pregold/freeze_predictions.py \
  --structured-features experiments/v1-message/features/private/pilot-30.features.private.jsonl \
  --visual-predictions experiments/v1-message/pregold/private/model-b.visual-candidate.private.jsonl \
  --private-output experiments/v1-message/pregold/private/pilot-30.predictions.private.jsonl \
  --public-summary experiments/v1-message/pregold/PUBLIC_PREGOLD_SUMMARY.json \
  --expected-count 30
```

The 30-item public summary also includes A2 aggregate status only: 10 raw-text
items were judged as rule no-match and 20 items abstained because raw element text
was unavailable. These are unscored pre-gold outputs, not performance results.

The adapted Model-B evidence is a **model-workflow visual candidate**, not a formal
paper baseline: its exact model identity and execution reproducibility are not
complete. Therefore the public summary fixes
`visual_evidence_is_formal_baseline=false`,
`visual_model_identity_reproducible=false`, `human_gold_used=false`,
`scored=false`, and `paper_result_eligible=false`.

## Tests

```bash
../.venv/bin/python3 -m unittest discover \
  -s experiments/v1-message/pregold/tests -v
```

The tests cover manifest-label invariance, explicit popup-scope gating, strict
human/gold/adjudication rejection, safe Model-B projection, zero actions, zero
scoring, private-output placement and permissions, and public-summary privacy.
