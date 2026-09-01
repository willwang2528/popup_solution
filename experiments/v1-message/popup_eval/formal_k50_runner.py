#!/usr/bin/env python3
"""Build a fail-closed formal K50 paired report from frozen evidence."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Mapping, Sequence


V1_ROOT = Path(__file__).resolve().parents[1]
if str(V1_ROOT) not in sys.path:
    sys.path.insert(0, str(V1_ROOT))

from popup_eval.comparison import compare_frozen_methods  # noqa: E402
from popup_eval.formal_k50 import (  # noqa: E402
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    FormalK50Error,
    MG_PU_METHOD_ID,
    SEEDED_RANDOM_METHOD_ID,
    finalize_formal_k50_confirmation,
)
from popup_eval.runner import ContractError  # noqa: E402
from popup_eval.semantic_adjudication import SEMANTIC_KEYS  # noqa: E402


RUNNER_CONTRACT_VERSION = "popup-message-formal-k50-runner-v1.0"
FORMAL_METHODS = (MG_PU_METHOD_ID, SEEDED_RANDOM_METHOD_ID)
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
CAPTURE_ID_PATTERN = re.compile(r"PMAB-A-CAP-\d{3}")
ACTION_BEARING_KEYS = {
    "action_semantics",
    "click",
    "coordinate",
    "dismiss",
    "execution_channel",
    "selector",
    "target",
    "target_candidate_id",
}


class FormalK50RunnerError(ValueError):
    """Raised when upstream evidence cannot produce a formal K50 report."""


class DuplicateKeyError(FormalK50RunnerError):
    """Raised when a JSON input contains an ambiguous duplicate key."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _canonical_jsonl(rows: Sequence[Mapping[str, Any]]) -> bytes:
    return b"".join(_canonical_json(row) + b"\n" for row in rows)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise FormalK50RunnerError(f"{label} must be a lowercase sha256")
    return value


def _reject_action_or_recovery(value: Any, context: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            lowered = key.casefold()
            if "recovery" in lowered or lowered in ACTION_BEARING_KEYS:
                raise FormalK50RunnerError(
                    f"{context}.{key}: action or Recovery field is forbidden"
                )
            if key == "action_attempts" and child != []:
                raise FormalK50RunnerError(
                    f"{context}.{key}: action or Recovery field is forbidden"
                )
            if key == "action_policy" and child != "no_action":
                raise FormalK50RunnerError(
                    f"{context}.{key}: action or Recovery field is forbidden"
                )
            _reject_action_or_recovery(child, f"{context}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, child in enumerate(value):
            _reject_action_or_recovery(child, f"{context}[{index}]")


def _validate_adjudicated_items(
    items: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Mapping[str, Any]], str, str]:
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)) or not items:
        raise FormalK50RunnerError("adjudicated gold must be a non-empty sequence")
    by_pilot: dict[str, Mapping[str, Any]] = {}
    item_ids: set[str] = set()
    gold_hashes: set[str] = set()
    batch_ids: set[str] = set()
    for item in items:
        if not isinstance(item, Mapping):
            raise FormalK50RunnerError("every adjudicated gold item must be an object")
        _reject_action_or_recovery(item)
        identity = item.get("identity")
        if not isinstance(identity, Mapping):
            raise FormalK50RunnerError("adjudicated gold item identity is missing")
        item_id = identity.get("item_id")
        pilot_id = identity.get("pilot_item_id")
        if not isinstance(item_id, str) or not item_id:
            raise FormalK50RunnerError("adjudicated gold item_id is missing")
        if not isinstance(pilot_id, str) or not pilot_id:
            raise FormalK50RunnerError("adjudicated gold pilot_item_id is missing")
        if item_id in item_ids or pilot_id in by_pilot:
            raise FormalK50RunnerError("adjudicated gold contains duplicate identities")
        item_ids.add(item_id)
        by_pilot[pilot_id] = item
        if identity.get("record_kind") in {
            "synthetic_schema_fixture",
            "annotation_pilot_candidate",
        }:
            raise FormalK50RunnerError("formal K50 rejects synthetic or pilot-only gold")
        if item.get("action_attempts") != []:
            raise FormalK50RunnerError("formal K50 gold must be action-free")
        if item.get("decision", {}).get("policy", {}).get("decision") != "no_action":
            raise FormalK50RunnerError("formal K50 gold decision must be no_action")
        if item.get("evaluation_exclusion_reasons", []) != []:
            raise FormalK50RunnerError("formal K50 gold contains metric exclusions")

        provenance = item.get("adjudication_provenance")
        if not isinstance(provenance, Mapping):
            raise FormalK50RunnerError("gold is not fully adjudicated")
        capture = provenance.get("capture_binding")
        if not isinstance(capture, Mapping):
            raise FormalK50RunnerError("gold lacks finalized CAP-001 capture binding")
        capture_id = capture.get("capture_id")
        delta_ms = capture.get("capture_delta_ms")
        maximum_delta_ms = capture.get("maximum_delta_ms")
        if (
            not isinstance(capture_id, str)
            or CAPTURE_ID_PATTERN.fullmatch(capture_id) is None
            or capture.get("capture_schema_version") != "1.1.0"
            or capture.get("capture_status") != "eligible_for_capture_feasibility"
            or capture.get("collector_mode")
            != "accessibilityservice_node_snapshot"
            or capture.get("source_origin") not in {"real_device", "emulator"}
            or capture.get("privacy_review_status") != "passed"
            or not isinstance(delta_ms, int)
            or isinstance(delta_ms, bool)
            or not isinstance(maximum_delta_ms, int)
            or isinstance(maximum_delta_ms, bool)
            or maximum_delta_ms != 3000
            or not 0 <= delta_ms <= maximum_delta_ms
            or capture.get("stable_state_verified") is not True
        ):
            raise FormalK50RunnerError("gold CAP-001 capture binding is invalid")
        for field in (
            "finalized_capture_record_sha256",
            "screenshot_sha256",
            "accessibility_snapshot_sha256",
        ):
            _require_sha256(capture.get(field), f"gold capture binding {field}")
        if (
            provenance.get("adjudication_status") != "resolved"
            or provenance.get("evidence_rechecked_via_adapter") is not True
            or provenance.get("pilot_item_id") != pilot_id
        ):
            raise FormalK50RunnerError("gold is not fully adjudicated")
        gold_hashes.add(
            _require_sha256(
                provenance.get("adjudication_batch_sha256"),
                "gold adjudication batch hash",
            )
        )
        batch_id = provenance.get("batch_id")
        if not isinstance(batch_id, str) or not batch_id:
            raise FormalK50RunnerError("gold adjudication batch_id is missing")
        batch_ids.add(batch_id)

        judgment = item.get("message_judgment")
        if not isinstance(judgment, Mapping) or judgment.get("profile") != (
            "popup_message_judgment_v1"
        ):
            raise FormalK50RunnerError("gold message-judgment profile is invalid")
        labels = judgment.get("labels")
        if not isinstance(labels, Mapping):
            raise FormalK50RunnerError("gold labels are missing")
        present = labels.get("popup_present_gt")
        if type(present) is not bool:
            raise FormalK50RunnerError("gold is not fully adjudicated")
        facts = labels.get("critical_facts_gt")
        if not isinstance(facts, list) or not all(
            isinstance(fact, str) for fact in facts
        ):
            raise FormalK50RunnerError("gold critical facts are invalid")
        observability = labels.get("message_text_observability")
        message = labels.get("message_text_gt")
        if present:
            if observability not in {"complete", "partial", "not_observable"}:
                raise FormalK50RunnerError("gold message observability is unresolved")
            if observability == "complete" and (
                not isinstance(message, str) or not message.strip()
            ):
                raise FormalK50RunnerError("gold complete message is missing")
        elif message is not None or observability != "not_applicable" or facts:
            raise FormalK50RunnerError("negative gold carries message semantics")
    if len(gold_hashes) != 1 or len(batch_ids) != 1:
        raise FormalK50RunnerError("adjudicated gold batch hash or batch_id is inconsistent")
    return by_pilot, next(iter(gold_hashes)), next(iter(batch_ids))


def _validate_prediction_coverage(
    prediction_rows: Sequence[Mapping[str, Any]],
    item_ids: set[str],
) -> dict[str, list[Mapping[str, Any]]]:
    if not isinstance(prediction_rows, Sequence) or isinstance(
        prediction_rows, (str, bytes)
    ):
        raise FormalK50RunnerError("predictions must be a sequence")
    rows_by_method: dict[str, list[Mapping[str, Any]]] = {
        method_id: [] for method_id in FORMAL_METHODS
    }
    for row in prediction_rows:
        if not isinstance(row, Mapping):
            raise FormalK50RunnerError("every prediction must be an object")
        _reject_action_or_recovery(row)
        method_id = row.get("method_id")
        if method_id not in rows_by_method:
            raise FormalK50RunnerError("formal K50 prediction method is unexpected")
        rows_by_method[method_id].append(row)
    for method_id, rows in rows_by_method.items():
        ids = [row.get("pilot_item_id") for row in rows]
        if (
            len(ids) != len(item_ids)
            or len(set(ids)) != len(ids)
            or set(ids) != item_ids
        ):
            raise FormalK50RunnerError(
                f"prediction coverage mismatch for {method_id}"
            )
    return rows_by_method


def _prediction_hash(rows: Sequence[Mapping[str, Any]]) -> str:
    ordered = sorted(rows, key=lambda row: row["pilot_item_id"])
    return _sha256(_canonical_jsonl(ordered))


def _validate_prediction_receipt_hashes(
    rows_by_method: Mapping[str, Sequence[Mapping[str, Any]]],
    budget_receipts: Mapping[str, Mapping[str, Any]],
) -> None:
    if not isinstance(budget_receipts, Mapping) or set(budget_receipts) != set(
        FORMAL_METHODS
    ):
        raise FormalK50RunnerError("budget receipts must cover exactly the K50 pair")
    _reject_action_or_recovery(budget_receipts)
    for method_id in FORMAL_METHODS:
        receipt = budget_receipts[method_id]
        if not isinstance(receipt, Mapping):
            raise FormalK50RunnerError(f"{method_id} budget receipt must be an object")
        declared = _require_sha256(
            receipt.get("frozen_prediction_sha256"),
            f"{method_id} frozen prediction hash",
        )
        if declared != _prediction_hash(rows_by_method[method_id]):
            raise FormalK50RunnerError(
                f"{method_id} frozen prediction hash mismatch"
            )


def _semantic_annotations(
    items_by_pilot: Mapping[str, Mapping[str, Any]],
    rows_by_method: Mapping[str, Sequence[Mapping[str, Any]]],
    semantic_rows: Sequence[Mapping[str, Any]],
    *,
    gold_batch_id: str,
) -> dict[tuple[str, str], dict[str, Any]]:
    predictions = {
        (row["pilot_item_id"], method_id): row
        for method_id, rows in rows_by_method.items()
        for row in rows
    }
    expected: set[tuple[str, str]] = set()
    for key, prediction in predictions.items():
        pilot_id, _ = key
        labels = items_by_pilot[pilot_id]["message_judgment"]["labels"]
        if (
            labels["popup_present_gt"] is True
            and labels.get("message_text_observability") == "complete"
            and prediction.get("status") == "judged"
            and prediction.get("popup_present_pred") is True
        ):
            expected.add(key)
    validated: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in semantic_rows:
        if not isinstance(row, Mapping):
            raise FormalK50RunnerError("semantic adjudication row must be an object")
        _reject_action_or_recovery(row)
        if set(row) != SEMANTIC_KEYS:
            raise FormalK50RunnerError("semantic adjudication keys are invalid")
        key = (row.get("pilot_item_id"), row.get("method_id"))
        if key not in expected or key in validated:
            raise FormalK50RunnerError("semantic adjudication coverage mismatch")
        if (
            row.get("contract_version")
            != "popup-message-output-adjudication-v1.0"
            or row.get("batch_id") != gold_batch_id
            or row.get("record_status") != "completed"
            or row.get("evidence_rechecked_via_adapter") is not True
            or type(row.get("message_semantically_correct")) is not bool
            or type(row.get("critical_hallucination")) is not bool
        ):
            raise FormalK50RunnerError("semantic adjudication is not resolved")
        adjudicator = row.get("adjudicator_id_pseudonymous")
        rationale = row.get("decision_rationale")
        if not isinstance(adjudicator, str) or not adjudicator.strip():
            raise FormalK50RunnerError("semantic adjudicator is missing")
        if not isinstance(rationale, str) or not rationale.strip():
            raise FormalK50RunnerError("semantic adjudication rationale is missing")
        timestamp = row.get("resolved_at")
        if not isinstance(timestamp, str):
            raise FormalK50RunnerError("semantic adjudication timestamp is invalid")
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as error:
            raise FormalK50RunnerError(
                "semantic adjudication timestamp is invalid"
            ) from error
        if parsed.tzinfo is None:
            raise FormalK50RunnerError("semantic adjudication timestamp is invalid")
        prediction = predictions[key]
        if row.get("prediction_row_sha256") != _sha256(_canonical_json(prediction)):
            raise FormalK50RunnerError("semantic prediction hash mismatch")
        validated[key] = row
    if set(validated) != expected:
        raise FormalK50RunnerError(
            "semantic adjudication coverage mismatch: "
            f"missing={sorted(expected - set(validated))}"
        )
    annotations: dict[tuple[str, str], dict[str, Any]] = {}
    for (pilot_id, method_id), row in validated.items():
        item_id = items_by_pilot[pilot_id]["identity"]["item_id"]
        annotations[(item_id, method_id)] = {
            "message_semantically_correct": row["message_semantically_correct"],
            "critical_hallucination": row["critical_hallucination"],
            "prediction_row_sha256": row["prediction_row_sha256"],
            "evidence_rechecked_via_adapter": True,
        }
    return annotations


def _require_defined_effect(report: Mapping[str, Any], metric_name: str) -> None:
    effect = report.get("paired_effects", {}).get("metrics", {}).get(metric_name)
    if (
        not isinstance(effect, Mapping)
        or effect.get("ci_status") != "available"
        or type(effect.get("point_estimate_difference")) not in (int, float)
        or not isinstance(effect.get("confidence_interval_95"), Mapping)
        or type(effect["confidence_interval_95"].get("lower")) not in (int, float)
        or type(effect["confidence_interval_95"].get("upper")) not in (int, float)
    ):
        raise FormalK50RunnerError(f"{metric_name} effect is undefined")


def build_formal_k50_paired_report(
    adjudicated_items: Sequence[Mapping[str, Any]],
    prediction_rows: Sequence[Mapping[str, Any]],
    semantic_rows: Sequence[Mapping[str, Any]],
    group_rows: Sequence[Mapping[str, Any]],
    budget_receipts: Mapping[str, Mapping[str, Any]],
    group_map_attestation: Mapping[str, Any],
) -> dict[str, Any]:
    """Build and verify the paired report consumed by the formal K50 finalizer."""
    _reject_action_or_recovery(group_rows)
    _reject_action_or_recovery(group_map_attestation)
    items_by_pilot, gold_hash, gold_batch_id = _validate_adjudicated_items(
        adjudicated_items
    )
    rows_by_method = _validate_prediction_coverage(
        prediction_rows, set(items_by_pilot)
    )
    _validate_prediction_receipt_hashes(rows_by_method, budget_receipts)
    annotations = _semantic_annotations(
        items_by_pilot,
        rows_by_method,
        semantic_rows,
        gold_batch_id=gold_batch_id,
    )
    try:
        report = compare_frozen_methods(
            list(adjudicated_items),
            list(prediction_rows),
            list(group_rows),
            method_ids=list(FORMAL_METHODS),
            proposed_method_id=MG_PU_METHOD_ID,
            strongest_baseline_method_id=SEEDED_RANDOM_METHOD_ID,
            bootstrap_replicates=BOOTSTRAP_REPLICATES,
            seed=BOOTSTRAP_SEED,
            semantic_annotations=annotations,
        )
    except (ContractError, KeyError, TypeError, ValueError) as error:
        raise FormalK50RunnerError(f"formal paired comparison rejected: {error}") from error

    if report.get("paired_item_count") != len(adjudicated_items):
        raise FormalK50RunnerError("gold is not fully metric-eligible")
    if report.get("adjudication_batch_sha256") != gold_hash:
        raise FormalK50RunnerError("paired report gold hash mismatch")
    for method_id in FORMAL_METHODS:
        mode = report.get("methods", {}).get(method_id, {}).get("metrics", {}).get(
            "vpma", {}
        ).get("mode")
        if mode != "adjudicated":
            raise FormalK50RunnerError("VPMA is not fully adjudicated")
    _require_defined_effect(report, "coverage")
    _require_defined_effect(report, "critical_hallucination_rate")

    report["status"] = "formal_k50_paired_report_ready"
    report["analysis_tier"] = "formal_confirmation_input"
    report["strongest_baseline_selection"] = "preregistered_seeded_random_k50"
    report["primary_pair"] = {
        "proposed": MG_PU_METHOD_ID,
        "reference": SEEDED_RANDOM_METHOD_ID,
    }
    report.pop("exploratory_reference_pair", None)
    report["formal_runner_contract_version"] = RUNNER_CONTRACT_VERSION
    report["input_sha256"] = {
        "adjudicated_items": _sha256(
            _canonical_jsonl(
                sorted(
                    adjudicated_items,
                    key=lambda item: item["identity"]["pilot_item_id"],
                )
            )
        ),
        "predictions": _sha256(
            _canonical_jsonl(
                sorted(
                    prediction_rows,
                    key=lambda row: (row["method_id"], row["pilot_item_id"]),
                )
            )
        ),
        "semantic_adjudications": _sha256(
            _canonical_jsonl(
                sorted(
                    semantic_rows,
                    key=lambda row: (row["method_id"], row["pilot_item_id"]),
                )
            )
        ),
        "group_map": report["group_map_sha256"],
        "budget_receipts": _sha256(_canonical_json(budget_receipts)),
        "group_map_attestation": _sha256(_canonical_json(group_map_attestation)),
        "implementation": _sha256(Path(__file__).read_bytes()),
    }
    report["action_policy"] = "no_action"
    report["recovery_evaluated"] = False
    report["paper_result_eligible"] = False
    report["claims"] = {
        "empirical_performance": False,
        "method_superiority": False,
        "user_experience_improvement": False,
        "recovery_or_dismissal": False,
    }
    try:
        finalize_formal_k50_confirmation(
            report,
            prediction_rows,
            budget_receipts,
            group_map_attestation,
        )
    except FormalK50Error as error:
        raise FormalK50RunnerError(
            f"formal K50 acceptance failed: {error}"
        ) from error
    return report


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise FormalK50RunnerError(f"cannot read {path.name}: {error}") from error
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line, object_pairs_hook=_strict_object)
        except Exception as error:
            raise FormalK50RunnerError(
                f"{path.name}:{line_number}: invalid JSON: {error}"
            ) from error
        if not isinstance(row, dict):
            raise FormalK50RunnerError(f"{path.name}:{line_number}: row must be an object")
        rows.append(row)
    if not rows:
        raise FormalK50RunnerError(f"{path.name}: input is empty")
    return rows


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    except Exception as error:
        raise FormalK50RunnerError(f"{path.name}: invalid JSON: {error}") from error
    if not isinstance(value, dict):
        raise FormalK50RunnerError(f"{path.name}: input must be an object")
    return value


def _write_private_new(path: Path, payload: bytes) -> None:
    if path.parent.name != "private" or not path.name.endswith(".private.json"):
        raise FormalK50RunnerError(
            "output must be a *.private.json file under a private directory"
        )
    if path.exists():
        raise FormalK50RunnerError("output already exists; report replacement is forbidden")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o600)
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise FormalK50RunnerError(
                "output already exists; report replacement is forbidden"
            ) from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adjudicated-items", required=True, type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--semantic-adjudications", required=True, type=Path)
    parser.add_argument("--group-map", required=True, type=Path)
    parser.add_argument("--budget-receipts", required=True, type=Path)
    parser.add_argument("--group-map-attestation", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.output.exists():
            raise FormalK50RunnerError(
                "output already exists; report replacement is forbidden"
            )
        report = build_formal_k50_paired_report(
            _read_jsonl(args.adjudicated_items),
            _read_jsonl(args.predictions),
            _read_jsonl(args.semantic_adjudications),
            _read_jsonl(args.group_map),
            _read_json_object(args.budget_receipts),
            _read_json_object(args.group_map_attestation),
        )
        _write_private_new(args.output, _canonical_json(report) + b"\n")
    except FormalK50RunnerError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "status": report["status"],
                "paired_item_count": report["paired_item_count"],
                "paper_result_eligible": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
