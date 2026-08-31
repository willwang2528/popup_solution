"""Command-line entry point for frozen, action-free evaluation."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path

from .io import (
    prepare_finalized_pilot_items,
    prepare_items,
    read_jsonl,
    sha256_file,
    write_json,
    write_jsonl,
)
from .runner import METHODS, run_experiment, run_frozen_prediction_experiment


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", required=True, type=Path, help="Frozen union-item or pilot-manifest JSONL")
    parser.add_argument(
        "--annotations",
        type=Path,
        help="Optional frozen adjudication_output.schema.json JSONL joined by pilot_item_id",
    )
    parser.add_argument("--fit-items", type=Path, help="Disjoint labeled fit JSONL for majority/no-input")
    parser.add_argument("--predictions", type=Path, help="Frozen OCR/VLM prediction JSONL adapter input")
    parser.add_argument(
        "--method", required=True, choices=sorted(METHODS | {"frozen-prediction"})
    )
    parser.add_argument(
        "--frozen-prediction-method-id",
        help="Exact pre-gold method_id to score when --method=frozen-prediction",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def _input_manifest(paths: dict[str, Path | None]) -> dict[str, dict[str, str]]:
    return {
        role: {"sha256": sha256_file(path)}
        for role, path in sorted(paths.items())
        if path is not None
    }


def _implementation_manifest() -> dict[str, str]:
    package_root = Path(__file__).resolve().parent
    paths = {
        "baselines.py": package_root / "baselines.py",
        "cli.py": package_root / "cli.py",
        "io.py": package_root / "io.py",
        "metrics.py": package_root / "metrics.py",
        "resources/the-ok/indicators.json": (
            package_root.parent / "resources" / "the-ok" / "indicators.json"
        ),
        "runner.py": package_root / "runner.py",
        "the_ok_baseline.py": package_root / "the_ok_baseline.py",
    }
    return {name: sha256_file(path) for name, path in paths.items()}


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.method == "frozen-prediction":
        if args.predictions is None or not args.frozen_prediction_method_id:
            parser.error(
                "--method=frozen-prediction requires --predictions and "
                "--frozen-prediction-method-id"
            )
    elif args.frozen_prediction_method_id:
        parser.error("--frozen-prediction-method-id requires --method=frozen-prediction")
    annotation_rows = read_jsonl(args.annotations) if args.annotations else []
    source_items = read_jsonl(args.items)
    adjudication_summary = None
    if args.annotations:
        items, semantic_annotations, adjudication_summary = prepare_finalized_pilot_items(
            source_items, annotation_rows
        )
    else:
        items, semantic_annotations = prepare_items(source_items)
    fit_items = None
    if args.fit_items:
        fit_items, _ = prepare_items(read_jsonl(args.fit_items))
    prediction_rows = read_jsonl(args.predictions) if args.predictions else []

    if args.method == "frozen-prediction":
        result = run_frozen_prediction_experiment(
            items,
            prediction_rows,
            args.frozen_prediction_method_id,
            semantic_annotations=semantic_annotations,
        )
    else:
        result = run_experiment(
            items,
            method=args.method,
            seed=args.seed,
            fit_items=fit_items,
            prediction_rows=prediction_rows,
            semantic_annotations=semantic_annotations,
        )
    manifest = deepcopy(result["run"])
    if adjudication_summary is not None:
        manifest["adjudication_batch"] = adjudication_summary
    manifest["implementation_sha256"] = _implementation_manifest()
    manifest["inputs"] = _input_manifest(
        {
            "annotations": args.annotations,
            "fit_items": args.fit_items,
            "items": args.items,
            "predictions": args.predictions,
        }
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(
        args.output_dir / "predictions.jsonl",
        sorted(result["predictions"], key=lambda row: row["item_id"]),
    )
    write_json(args.output_dir / "metrics.json", result["metrics"])
    write_json(args.output_dir / "run_manifest.json", manifest)
    print(
        json.dumps(
            {
                "status": "pass",
                "method": manifest["method"],
                "evaluated_item_count": manifest["evaluated_item_count"],
                "evidence_level": manifest["evidence_level"],
                "paper_result_eligible": manifest["paper_result_eligible"],
                "output_dir": str(args.output_dir),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0
