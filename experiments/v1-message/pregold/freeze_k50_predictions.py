#!/usr/bin/env python3
"""Materialize the gold-blind K50 prediction pair from a frozen ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Iterable


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import freeze_operating_points as operating  # noqa: E402
import freeze_predictions as pregold  # noqa: E402
from popup_eval.formal_k50 import (  # noqa: E402
    MG_PU_METHOD_ID,
    SEEDED_RANDOM_METHOD_ID,
)
from popup_eval.formal_k50_runner import (  # noqa: E402
    FormalK50RunnerError,
    _reject_action_or_recovery,
)


CONTRACT_VERSION = "popup-message-k50-prediction-freeze-v1.0"
SOURCE_METHOD_ID = operating.SOURCE_METHOD_ID
METHOD_TO_LEDGER_KEY = {
    MG_PU_METHOD_ID: "mg_pu",
    SEEDED_RANDOM_METHOD_ID: "seeded_random",
}
EXTRA_ACTION_KEYS = {
    "action",
    "action_candidate",
    "action_type",
    "gesture",
    "planned_action",
    "press",
    "swipe",
    "tap",
}


class ContractError(ValueError):
    """Raised when the K50 prediction freeze is unsafe or not reproducible."""


class DuplicateKeyError(ContractError):
    """Raised when JSON contains an ambiguous duplicate key."""


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


def _canonical_jsonl(rows: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(_canonical_json(row) + b"\n" for row in rows)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _formal_selected_item_set_hash(item_ids: Iterable[str]) -> str:
    return _sha256(("\n".join(sorted(item_ids)) + "\n").encode("utf-8"))


def _read_json_object(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        payload = path.read_bytes()
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=_strict_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, DuplicateKeyError) as error:
        raise ContractError(f"cannot read {path.name} as strict UTF-8 JSON: {error}") from error
    if not isinstance(value, dict):
        raise ContractError(f"{path.name}: input must be an object")
    return value, payload


def _require_private_output(path: Path, suffix: str) -> None:
    if path.parent.name != "private" or not path.name.endswith(suffix):
        raise ContractError(
            f"output must be a *{suffix} file under a private directory"
        )


def _reject_extra_action_keys(value: Any, context: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.casefold() in EXTRA_ACTION_KEYS:
                raise ContractError(
                    f"{context}.{key}: action or Recovery field is forbidden"
                )
            _reject_extra_action_keys(child, f"{context}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_extra_action_keys(child, f"{context}[{index}]")


def _reject_action_or_recovery_strict(value: Any, context: str = "$") -> None:
    try:
        _reject_action_or_recovery(value, context)
    except FormalK50RunnerError as error:
        raise ContractError(str(error)) from error
    _reject_extra_action_keys(value, context)


def _verify_source_method_snapshot(
    method_rows: list[dict[str, Any]],
    features_by_id: dict[str, dict[str, Any]],
    visual_by_id: dict[str, dict[str, Any]],
) -> str:
    observed = sorted(
        (row for row in method_rows if row.get("method_id") == SOURCE_METHOD_ID),
        key=lambda row: row["pilot_item_id"],
    )
    recomputed = sorted(
        (
            row
            for row in pregold.freeze_predictions(features_by_id, visual_by_id)
            if row["method_id"] == SOURCE_METHOD_ID
        ),
        key=lambda row: row["pilot_item_id"],
    )
    if _canonical_jsonl(observed) != _canonical_jsonl(recomputed):
        raise ContractError(
            "source method snapshot does not match the shared pregold freezer output"
        )
    return _sha256(_canonical_jsonl(observed))


def _validate_ledger_and_inputs(
    *,
    ledger: dict[str, Any],
    ledger_payload: bytes,
    item_rows: list[dict[str, Any]],
    item_payload: bytes,
    visual_rows: list[dict[str, Any]],
    visual_payload: bytes,
    method_rows: list[dict[str, Any]],
    method_payload: bytes,
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, str],
]:
    for value in (ledger, item_rows, visual_rows, method_rows):
        _reject_action_or_recovery_strict(value)

    try:
        items_for_ledger = operating._validate_items(item_rows)
        operating._validate_method_results(method_rows, items_for_ledger)
        visual_hashes = operating._validate_visual_rows(
            visual_rows, set(items_for_ledger)
        )
        freeze_timestamp = operating._validate_timestamp(ledger.get("freeze_timestamp"))
    except (operating.ContractError, TypeError) as error:
        raise ContractError(str(error)) from error

    hashes = ledger.get("hashes")
    if not isinstance(hashes, dict):
        raise ContractError("operating-point ledger hashes are missing")
    exact_inputs = {
        "item_snapshot_sha256": _sha256(item_payload),
        "visual_bank_input_sha256": _sha256(visual_payload),
        "method_results_sha256": _sha256(method_payload),
    }
    for key, actual in exact_inputs.items():
        if hashes.get(key) != actual:
            label = {
                "item_snapshot_sha256": "item snapshot",
                "visual_bank_input_sha256": "visual bank input",
                "method_results_sha256": "source method snapshot",
            }[key]
            raise ContractError(f"{label} hash mismatch against operating-point ledger")

    if (
        ledger.get("contract_version") != operating.CONTRACT_VERSION
        or ledger.get("status") != "frozen_pregold_operating_point_ledgers"
        or ledger.get("policy_status") != "proposed_operating_point_policy"
        or ledger.get("scope") != "popup_message_judgment_v1"
        or ledger.get("action_policy") != "no_action"
        or ledger.get("gold_release_id") is not None
        or ledger.get("human_gold_used") is not False
        or ledger.get("scored") is not False
        or ledger.get("paper_result_eligible") is not False
        or ledger.get("source_method_id") != SOURCE_METHOD_ID
    ):
        raise ContractError("operating-point ledger pre-gold contract is invalid")
    seed = ledger.get("seed")
    if type(seed) is not int or not 0 <= seed <= 2**63 - 1:
        raise ContractError("operating-point ledger seed is invalid")

    expected_ledger = operating._build_ledger(
        items=items_for_ledger,
        seed=seed,
        freeze_timestamp=freeze_timestamp,
        item_payload=item_payload,
        visual_payload=visual_payload,
        method_payload=method_payload,
        visual_hashes=visual_hashes,
    )
    if ledger != expected_ledger:
        raise ContractError(
            "selected ledger or budget commitments do not match recomputed inputs"
        )

    item_count = len(items_for_ledger)
    k50 = ledger["operating_points"]["K50"]
    if k50.get("k") != (item_count + 1) // 2:
        raise ContractError("K50 does not equal ceil(0.50 * item_count)")

    try:
        features_by_id = pregold._rows_by_feature_id(item_rows, item_count)
        visual_by_id = pregold._rows_by_visual_id(
            visual_rows, set(features_by_id)
        )
    except pregold.ContractError as error:
        raise ContractError(str(error)) from error
    if set(visual_by_id) != set(features_by_id):
        raise ContractError("visual bank item coverage is incomplete")

    return features_by_id, visual_by_id, {
        **exact_inputs,
        **visual_hashes,
        "operating_point_ledger_sha256": _sha256(ledger_payload),
    }


def _freeze_pair(
    *,
    ledger: dict[str, Any],
    features_by_id: dict[str, dict[str, Any]],
    visual_by_id: dict[str, dict[str, Any]],
    input_hashes: dict[str, str],
    source_method_rows_sha256: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    k50 = ledger["operating_points"]["K50"]
    rows: list[dict[str, Any]] = []
    method_commitments: dict[str, Any] = {}
    for method_id, ledger_key in METHOD_TO_LEDGER_KEY.items():
        selection = k50[ledger_key]
        selected_ids = selection["selected_item_ids"]
        selected = set(selected_ids)
        formal_selected_hash = _formal_selected_item_set_hash(selected)
        if len(selected) != k50["k"]:
            raise ContractError(f"{method_id}: selected item coverage is not exact K50")
        binding = {
            "contract_version": CONTRACT_VERSION,
            "operating_point": "K50",
            "selection_policy": ledger_key,
            "item_snapshot_sha256": input_hashes["item_snapshot_sha256"],
            "source_method_snapshot_sha256": input_hashes["method_results_sha256"],
            "source_method_rows_sha256": source_method_rows_sha256,
            "visual_bank_input_sha256": input_hashes["visual_bank_input_sha256"],
            "visual_model_config_sha256": input_hashes[
                "visual_model_config_sha256"
            ],
            "visual_protocol_sha256": input_hashes["visual_protocol_sha256"],
            "visual_declared_bank_sha256": input_hashes[
                "visual_declared_bank_sha256"
            ],
            "budget_sha256": k50["budget_sha256"],
            "operating_point_selected_item_set_sha256": selection[
                "selected_item_set_sha256"
            ],
            "formal_selected_item_set_sha256": formal_selected_hash,
            "selected_ledger_sha256": selection["selected_ledger_sha256"],
            "operating_point_ledger_sha256": input_hashes[
                "operating_point_ledger_sha256"
            ],
        }
        method_rows: list[dict[str, Any]] = []
        for item_id in sorted(features_by_id):
            scoped_message, gaps = pregold._popup_scoped_message(
                features_by_id[item_id]
            )
            prediction = pregold._fusion_prediction(
                item_id,
                method_id,
                scoped_message,
                gaps,
                visual_by_id[item_id],
                visual_called=item_id in selected,
            )
            prediction["freeze_binding"] = dict(binding)
            method_rows.append(prediction)
        if {row["pilot_item_id"] for row in method_rows} != set(features_by_id):
            raise ContractError(f"{method_id}: prediction item coverage is incomplete")
        if {row["pilot_item_id"] for row in method_rows if row["visual_called"]} != selected:
            raise ContractError(f"{method_id}: visual calls differ from selected ledger")
        rows.extend(method_rows)
        frozen_prediction_hash = _sha256(_canonical_jsonl(method_rows))
        method_commitments[method_id] = {
            "row_count": len(method_rows),
            "visual_call_count": sum(row["visual_called"] for row in method_rows),
            "selected_item_ids": selected_ids,
            "selected_item_set_sha256": formal_selected_hash,
            "operating_point_selected_item_set_sha256": selection[
                "selected_item_set_sha256"
            ],
            "selected_ledger_sha256": selection["selected_ledger_sha256"],
            "frozen_prediction_sha256": frozen_prediction_hash,
            "formal_receipt_hash_binding": {
                "operating_point": "K50",
                "metric_item_set_sha256": ledger["hashes"][
                    "item_identity_sha256"
                ],
                "visual_bank_sha256": input_hashes["visual_bank_input_sha256"],
                "visual_config_sha256": input_hashes[
                    "visual_model_config_sha256"
                ],
                "budget_spec_sha256": k50["budget_sha256"],
                "selected_item_set_sha256": formal_selected_hash,
                "frozen_prediction_sha256": frozen_prediction_hash,
            },
        }

    rows.sort(key=lambda row: (row["method_id"], row["pilot_item_id"]))
    _reject_action_or_recovery_strict(rows)
    commitment = {
        "contract_version": CONTRACT_VERSION,
        "status": "frozen_pregold_k50_prediction_pair",
        "scope": "popup_message_judgment_v1",
        "action_policy": "no_action",
        "freeze_timestamp": ledger["freeze_timestamp"],
        "item_count": len(features_by_id),
        "k": k50["k"],
        "human_gold_used": False,
        "scored": False,
        "paper_result_eligible": False,
        "formal_result_generated": False,
        "actual_budget_measured": False,
        "formal_budget_receipt_ready": False,
        "input_sha256": input_hashes,
        "source_method_rows_sha256": source_method_rows_sha256,
        "methods": method_commitments,
        "pair_prediction_sha256": _sha256(_canonical_jsonl(rows)),
        "implementation_sha256": _sha256(Path(__file__).read_bytes()),
    }
    return rows, commitment


def _write_private_pair_new(
    prediction_path: Path,
    prediction_payload: bytes,
    commitment_path: Path,
    commitment_payload: bytes,
) -> None:
    _require_private_output(prediction_path, ".private.jsonl")
    _require_private_output(commitment_path, ".private.json")
    if prediction_path == commitment_path:
        raise ContractError("private outputs must be distinct files")
    for path in (prediction_path, commitment_path):
        if path.exists():
            raise ContractError("output already exists; frozen output replacement is forbidden")
    temporary_paths: list[Path] = []
    created_paths: list[Path] = []
    try:
        for path, payload in (
            (prediction_path, prediction_payload),
            (commitment_path, commitment_payload),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.parent.chmod(0o700)
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                temporary_paths.append(temporary)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.chmod(0o600)
        for temporary, destination in zip(
            temporary_paths, (prediction_path, commitment_path), strict=True
        ):
            try:
                os.link(temporary, destination)
            except FileExistsError as error:
                raise ContractError(
                    "output already exists; frozen output replacement is forbidden"
                ) from error
            created_paths.append(destination)
    except Exception:
        for path in created_paths:
            path.unlink(missing_ok=True)
        raise
    finally:
        for path in temporary_paths:
            path.unlink(missing_ok=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", required=True, type=Path)
    parser.add_argument("--visual-bank", required=True, type=Path)
    parser.add_argument("--method-results", required=True, type=Path)
    parser.add_argument("--operating-point-ledger", required=True, type=Path)
    parser.add_argument("--private-output", required=True, type=Path)
    parser.add_argument("--private-commitment", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        _require_private_output(args.private_output, ".private.jsonl")
        _require_private_output(args.private_commitment, ".private.json")
        if args.private_output.exists() or args.private_commitment.exists():
            raise ContractError(
                "output already exists; frozen output replacement is forbidden"
            )
        ledger, ledger_payload = _read_json_object(args.operating_point_ledger)
        item_rows, item_payload = operating._read_jsonl(args.items)
        visual_rows, visual_payload = operating._read_jsonl(args.visual_bank)
        method_rows, method_payload = operating._read_jsonl(args.method_results)
        features_by_id, visual_by_id, input_hashes = _validate_ledger_and_inputs(
            ledger=ledger,
            ledger_payload=ledger_payload,
            item_rows=item_rows,
            item_payload=item_payload,
            visual_rows=visual_rows,
            visual_payload=visual_payload,
            method_rows=method_rows,
            method_payload=method_payload,
        )
        source_method_rows_sha256 = _verify_source_method_snapshot(
            method_rows, features_by_id, visual_by_id
        )
        rows, commitment = _freeze_pair(
            ledger=ledger,
            features_by_id=features_by_id,
            visual_by_id=visual_by_id,
            input_hashes=input_hashes,
            source_method_rows_sha256=source_method_rows_sha256,
        )
        _write_private_pair_new(
            args.private_output,
            _canonical_jsonl(rows),
            args.private_commitment,
            _canonical_json(commitment) + b"\n",
        )
    except (
        ContractError,
        operating.ContractError,
        pregold.ContractError,
        OSError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "status": commitment["status"],
                "item_count": commitment["item_count"],
                "k": commitment["k"],
                "method_count": len(commitment["methods"]),
                "formal_result_generated": False,
                "paper_result_eligible": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
