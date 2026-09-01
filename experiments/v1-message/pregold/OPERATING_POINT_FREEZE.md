# Pre-gold operating-point freeze

`freeze_operating_points.py` freezes selected-item ledgers for `K25`, `K50`,
and `K100` before human gold is released. It produces no prediction, score,
comparison, or action.

## Status and interpretation

The MG-PU ranking in this tool is a **proposed operating-point policy**. It is
not the already-frozen binary MG-PU gate, a validated allocation rule, or a
formal paper result. The tool verifies that its derived gap/no-gap decision
agrees with the existing `mg-pu-gated-union-v1` method result, then adds an
explicit ordering needed to cap visual access at a fixed K.

For N frozen items:

- `K25 = ceil(0.25 * N)`;
- `K50 = ceil(0.50 * N)`;
- `K100 = N`.

MG-PU candidates are ranked by descending gap-severity score, with ascending
`item_id` as the complete tie-break. Multiple reasons use the maximum score:

| Score | Pre-gold gap reasons |
|---:|---|
| 4 | `contradictory`, `owner_mismatch`, `stale` |
| 3 | `missing`, `visual_only_text` |
| 2 | `ambiguous`, `merged`, `unknown` |
| 1 | `non_actionable` |
| 0 | no derived gap |

The random control ranks by ascending
`SHA256("seeded-random-k-v1|<seed>|<item_id>")`, then ascending `item_id`.
The seed is mandatory and written into the ledger.

For every operating point the ledger also records whether the two selected-ID
sets are identical, their intersection count, and `overlap_count / K`. When the
sets differ, the machine-readable interpretation is
`budget_matched_not_item_matched`: equal K does not control which items receive
visual evidence and must not be described as an item-matched comparison.

These severity values are a pre-gold design choice for falsifiable
operating-point experiments. They must not be tuned after gold release, and the
ledger must continue to be described as proposed until evaluated.

## Fail-closed contract

All three JSONL inputs must have identical item coverage:

1. a sanitized, action-free, unscored item/structured-feature snapshot;
2. a frozen visual-bank projection with one uniform `model_config_sha256`;
3. frozen method results containing complete `mg-pu-gated-union-v1` rows.

The tool rejects label-, ground-truth-, adjudication-, stratum-, or
metric-eligibility-shaped fields. Safe attestations must retain their negative
values, including `human_gold_used=false`, `scored=false`, and
`paper_result_eligible=false`. It does not use visual messages, OCR text, image
content, or any human annotation to rank items.

The output is a new `*.private.json` file inside a directory named `private`.
Existing output is never replaced. The file is mode `0600` and includes:

- the selected IDs, severity scores, reasons, ranks, and selected-ledger hashes;
- the seeded-random selected IDs and hashes;
- selected-set identity, overlap count/fraction, and the budget-vs-item matching caveat;
- item-identity, input-bundle, policy-config, implementation, and budget-ledger
  hashes;
- the exact UTC freeze timestamp;
- `gold_release_id=null`, `human_gold_used=false`, `scored=false`, and
  `paper_result_eligible=false`.

The timestamp is a caller-supplied commitment, not an independently trusted
clock attestation. A later release process must bind the ledger hash and freeze
timestamp to its separately controlled gold-release record.

## Command

Run only before gold access, using the canonical project interpreter:

```bash
/Users/will/Documents/ARIS-paper/.venv/bin/python3 \
  /Users/will/Documents/ARIS-paper/popup-solution/experiments/v1-message/pregold/freeze_operating_points.py \
  --items /Users/will/Documents/ARIS-paper/popup-solution/experiments/v1-message/features/private/formal.features.private.jsonl \
  --visual-bank /Users/will/Documents/ARIS-paper/popup-solution/experiments/v1-message/pregold/private/formal.visual.private.jsonl \
  --method-results /Users/will/Documents/ARIS-paper/popup-solution/experiments/v1-message/pregold/private/formal.predictions.private.jsonl \
  --seed 17 \
  --freeze-timestamp 2026-09-01T09:30:00Z \
  --output /Users/will/Documents/ARIS-paper/popup-solution/experiments/v1-message/pregold/private/formal.operating-points.private.json
```

The example filenames are interface placeholders, not claims that a formal
snapshot or formal visual baseline already exists.
