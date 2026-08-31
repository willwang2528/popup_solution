# Gold-blind structured feature freeze

This directory freezes the structured-UI inputs used by the popup-message v1
pilot before human gold is available. It is strictly perception-only and never
executes a popup action.

## Privacy and leakage boundary

- The manifest reader uses only `pilot_item_id`. It does not use source labels,
  sampling strata, source kinds, model preannotations, or human annotations.
- `rico-semantic.json` may contain UI text and identifiers. The resulting JSONL
  is private and ignored by Git under `private/`.
- The CLI fails closed unless both the private file and its dedicated directory
  are inside the manifest's Git worktree and matched by `.gitignore`. The
  private directory is set to mode `0700` and the JSONL to `0600`.
- `PUBLIC_FEATURE_SUMMARY.json` contains only the contract, counts, hashes, and
  non-eligibility flags. It contains no UI text, screenshot, absolute path, or
  per-item label.
- All rows are `gold_blind=true`, `gold_used=false`, `scored=false`,
  `paper_result_eligible=false`, and `no_action`.
- Source-export integrity is checked by the upstream dataset adapter. This
  freezer deliberately does not consume expected hashes or artifact paths from
  the label-bearing pilot manifest; it freezes the semantic files it actually
  reads through per-file hashes and the private-bundle hash.

## Rebuild

From the repository root:

```bash
../.venv/bin/python3 \
  experiments/v1-message/features/build_pilot_features.py \
  --manifest dataset-v1/work/annotation-media/pilot-batch-30/pilot-manifest.jsonl \
  --private-output experiments/v1-message/features/private/pilot-30.features.private.jsonl \
  --public-summary experiments/v1-message/features/PUBLIC_FEATURE_SUMMARY.json
```

Run the tests with the canonical project interpreter:

```bash
../.venv/bin/python3 -m unittest discover \
  -s experiments/v1-message/features/tests -v
```
