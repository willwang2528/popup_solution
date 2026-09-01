# Pre-gold prediction freeze

This directory freezes deterministic, **gold-blind and unscored** v1 popup-message
predictions before human adjudication. It never computes a metric and never emits
or executes a popup action.

## Safety contract

- The frozen item set comes from the sanitized structured-feature JSONL, not the
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

`c1-always-on-fusion-v1` (`C1-AO`) calls the same frozen visual bank for all 30
items. A judged visual row is used; if visual evidence abstains, an already
sufficient popup-scoped structured message may be retained. It is an
accuracy-cost-frontier control and is not equal-budget.

`c1-budget-matched-fusion-v1` (`C1-BM`) sets `K` to the frozen MG-PU visual-call
count, ranks item IDs by SHA-256 of a fixed seed and method ID, and calls the
same bank for exactly the first `K`. Selection uses no source label, human gold,
message or metric. Its public summary commits the selected item-set hash.
This is cost-matching only, not item-set or difficulty matching. Any future
accuracy comparison must report the overlap between its visually inspected item
set and MG-PU's.

`shuffled-gap-reasons-v1` (`ABL-003`) reuses the exact popup-scoped gap vectors
derived for MG-PU, ranks item IDs with the fixed seed `17`, and assigns those
vectors through a stable one-position rotation. For `N > 1` this is a one-to-one
permutation with no self-assignment; therefore the gap-vector multiset and total
visual-call count are exactly preserved while the item-to-gap association is
broken. The private predictions identify shuffled routing in `route_reason`.
The public summary exposes only the seed, a SHA-256 commitment to the private
permutation, and aggregate permutation/call counts; it never exposes the item
mapping.

它不是完全内容盲的随机路由：gap reason 仍来自同一批 item，只是被应用到不同
item。因此它隔离的是“gap reason 与 item 的正确绑定”是否提供超越 gap 分布本身的
信号。未来论文必须与 seeded-random 控制并列披露这一限制，不能把 ABL-003 描述成
内容独立策略。

All freezer outputs are immutable. If either requested private prediction or
public-summary path already exists, the run fails before reading inputs and does
not replace either file.

## Reproduce the 30-item freeze

The current frozen heuristic visual path uses the verified private bank projection rather
than the older model-workflow preannotation:

```bash
../.venv/bin/python3 \
  experiments/v1-message/visual/export_pregold_visual_bank.py \
  --protocol experiments/v1-message/visual/results/pilot-batch-30-v1.0.1/protocol.json \
  --visual-bank experiments/v1-message/visual/results/pilot-batch-30-v1.0.1/visual-bank.private.jsonl \
  --input-manifest dataset-v1/work/annotation-media/pilot-batch-30/pilot-manifest.jsonl \
  --public-summary experiments/v1-message/visual/PUBLIC_VISUAL_BANK_SUMMARY.json \
  --private-output experiments/v1-message/pregold/private/roi-ocr.heuristic-visual.private.jsonl \
  --projection-summary experiments/v1-message/pregold/PUBLIC_HEURISTIC_VISUAL_PROJECTION_SUMMARY.json

../.venv/bin/python3 \
  experiments/v1-message/pregold/freeze_predictions.py \
  --structured-features experiments/v1-message/features/private/pilot-30.features.private.jsonl \
  --visual-predictions experiments/v1-message/pregold/private/roi-ocr.heuristic-visual.private.jsonl \
  --private-output experiments/v1-message/pregold/private/pilot-30.heuristic-visual-c1.predictions.private.jsonl \
  --public-summary experiments/v1-message/pregold/PUBLIC_PREGOLD_HEURISTIC_VISUAL_C1_SUMMARY.json \
  --expected-count 30
```

The 30-item public summary also includes A2 aggregate status only: 10 raw-text
items were judged as rule no-match and 20 items abstained because raw element text
was unavailable. These are unscored pre-gold outputs, not performance results.

The older adapted Model-B evidence remains a **model-workflow visual candidate**
and is not promoted. The new ROI-OCR projection sets
`visual_evidence_is_fixed_threshold_heuristic_adaptation=true` and
`visual_repeat_execution_byte_identical_on_fixed_host=true` only after recomputing
the complete bank against the frozen protocol, screenshot hash map and public
summary. It also fixes
`visual_cross_os_or_device_model_identity_reproducible=not_verified`. This means
the input is frozen and the measured fixed-host replay matched; it does not mean
the predictions are correct or that Apple Vision has a reproducible model identity.
`human_gold_used=false`, `scored=false`, and
`paper_result_eligible=false` remain mandatory.

## Materialize the formal K50 prediction pair

[`freeze_operating_points.py`](./freeze_operating_points.py) freezes the K25,
K50, and K100 selected-ID ledgers, but it deliberately emits no predictions.
After that ledger exists, [`freeze_k50_predictions.py`](./freeze_k50_predictions.py)
materializes exactly two complete K50 snapshots: `mg-pu-k50-v1` and
`seeded-random-k50-v1`.

The materializer revalidates the original feature, visual-bank, and method
snapshots; reconstructs the complete operating-point ledger; and recomputes the
source `mg-pu-gated-union-v1` rows through the shared pregold freezer. Every
output row binds the source-method snapshot, selected-ID ledger, visual-bank
input/config/protocol commitments, K50 budget commitment, and operating-point
ledger hashes. Both methods cover the identical full item set and set
`visual_called=true` for exactly `ceil(0.5 * N)` ledger-selected items.

The ledger's canonical-JSON selected-set hash and the formal finalizer's
newline-delimited selected-set hash are deliberately stored under different
names. The sidecar's `formal_receipt_hash_binding` projects the latter together
with the exact prediction, item-set, visual-bank/config, and budget-spec hashes;
copying the ledger hash into a later formal receipt would be rejected.

Both the prediction JSONL and its commitment sidecar are private, mode `0600`,
and immutable: existing paths are never replaced. The sidecar exposes each
method's canonical `frozen_prediction_sha256`, which a later measured budget
receipt can bind. It is not itself an actual-budget receipt, does not read gold,
does not compute metrics, and does not create a formal result.

```bash
../.venv/bin/python3 \
  experiments/v1-message/pregold/freeze_k50_predictions.py \
  --items experiments/v1-message/features/private/formal.features.private.jsonl \
  --visual-bank experiments/v1-message/pregold/private/formal.visual.private.jsonl \
  --method-results experiments/v1-message/pregold/private/formal.predictions.private.jsonl \
  --operating-point-ledger experiments/v1-message/pregold/private/formal.operating-points.private.json \
  --private-output experiments/v1-message/pregold/private/formal-k50.predictions.private.jsonl \
  --private-commitment experiments/v1-message/pregold/private/formal-k50.commitment.private.json
```

Formal scoring remains blocked until real adjudicated items, method-specific
semantic adjudications, a leakage-safe group-map attestation, and measured
pixels/tokens/cost receipts all exist. This freezer cannot satisfy or simulate
those gates.

## Tests

```bash
../.venv/bin/python3 -m unittest discover \
  -s experiments/v1-message/pregold/tests -v
```

The tests cover manifest-label value and physical-absence invariance, unknown
manifest-field fail-closed behavior, explicit popup-scope gating, strict
human/gold/adjudication rejection, safe Model-B projection, zero actions, zero
scoring, private-output placement and permissions, public-summary privacy, and
the K50 pair's complete coverage plus input/selection/budget hash bindings.
