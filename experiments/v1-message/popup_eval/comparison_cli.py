"""CLI for private-gold, frozen-prediction paired pilot comparisons."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .comparison import compare_frozen_methods
from .io import (
    prepare_finalized_pilot_items,
    read_jsonl,
    sha256_file,
    write_json,
)
from .semantic_adjudication import prepare_semantic_output_annotations


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", required=True, type=Path)
    parser.add_argument("--annotations", required=True, type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--semantic-annotations", type=Path)
    parser.add_argument("--group-map", required=True, type=Path)
    parser.add_argument("--method-id", required=True, action="append", dest="method_ids")
    parser.add_argument("--proposed-method-id", required=True)
    parser.add_argument("--strongest-baseline-method-id", required=True)
    parser.add_argument("--bootstrap-replicates", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    items, semantic_annotations, adjudication_summary = prepare_finalized_pilot_items(
        read_jsonl(args.items), read_jsonl(args.annotations)
    )
    prediction_rows = read_jsonl(args.predictions)
    if args.semantic_annotations is not None:
        semantic_annotations = prepare_semantic_output_annotations(
            items,
            prediction_rows,
            read_jsonl(args.semantic_annotations),
            method_ids=args.method_ids,
        )
    report = compare_frozen_methods(
        items,
        prediction_rows,
        read_jsonl(args.group_map),
        method_ids=args.method_ids,
        proposed_method_id=args.proposed_method_id,
        strongest_baseline_method_id=args.strongest_baseline_method_id,
        bootstrap_replicates=args.bootstrap_replicates,
        seed=args.seed,
        semantic_annotations=semantic_annotations,
    )
    report["adjudication_batch"] = adjudication_summary
    report["input_sha256"] = {
        "items": sha256_file(args.items),
        "annotations": sha256_file(args.annotations),
        "predictions": sha256_file(args.predictions),
        "group_map": sha256_file(args.group_map),
    }
    if args.semantic_annotations is not None:
        report["input_sha256"]["semantic_annotations"] = sha256_file(
            args.semantic_annotations
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "paired_item_count": report["paired_item_count"],
                "method_ids": report["method_ids"],
                "paper_result_eligible": report["paper_result_eligible"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
