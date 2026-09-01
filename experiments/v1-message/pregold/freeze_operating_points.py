#!/usr/bin/env python3
"""Freeze pre-gold K25/K50/K100 MG-PU and seeded-random selected-ID ledgers."""

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
from typing import Any


CONTRACT_VERSION = "popup-operating-point-freeze-v1.0"
SOURCE_METHOD_ID = "mg-pu-gated-union-v1"
ITEM_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
UTC_TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")

SAFE_ATTESTATIONS = {
    "adjudication_used": False,
    "folder_label_used": False,
    "gold_blind": True,
    "gold_used": False,
    "human_gold_used": False,
    "paper_result_eligible": False,
    "post_action_evidence_used": False,
    "scored": False,
    "source_sampling_label_used": False,
}
FORBIDDEN_EXACT_KEYS = {
    "annotations",
    "batch_id",
    "eligibility",
    "labels",
    "metric_eligible",
    "official_split",
    "presence_label",
    "provenance",
    "sampling_stratum",
    "source_label",
    "source_provenance",
    "source_record_id",
}
GAP_SEVERITY = {
    "contradictory": 4,
    "owner_mismatch": 4,
    "stale": 4,
    "missing": 3,
    "visual_only_text": 3,
    "ambiguous": 2,
    "merged": 2,
    "unknown": 2,
    "non_actionable": 1,
}
OPERATING_POINTS = (
    ("K25", "0.25", 1, 4),
    ("K50", "0.50", 1, 2),
    ("K100", "1.00", 1, 1),
)


class ContractError(ValueError):
    """Raised when a pre-gold operating-point input is unsafe or inconsistent."""


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


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_jsonl(path: Path) -> tuple[list[dict[str, Any]], bytes]:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise ContractError(f"cannot read {path.name}: {error}") from error
    if not payload:
        raise ContractError(f"{path.name}: input is empty")
    rows: list[dict[str, Any]] = []
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ContractError(f"{path.name}: input must be UTF-8 JSONL") from error
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line, object_pairs_hook=_strict_object)
        except Exception as error:
            raise ContractError(
                f"{path.name}:{line_number}: invalid JSON: {error}"
            ) from error
        if not isinstance(row, dict):
            raise ContractError(f"{path.name}:{line_number}: row must be an object")
        rows.append(row)
    if not rows:
        raise ContractError(f"{path.name}: input has no JSON rows")
    return rows, payload


def _is_forbidden_key(key: str) -> bool:
    lowered = key.casefold()
    if key in FORBIDDEN_EXACT_KEYS:
        return True
    if key == "component_label":
        return False
    if lowered.endswith("_gt") or "ground_truth" in lowered:
        return True
    if "adjudicat" in lowered:
        return True
    if lowered == "label" or lowered.endswith("_label") or "_label_" in lowered:
        return True
    if "stratum" in lowered or lowered.startswith("eligible_for_"):
        return True
    if "metric" in lowered and "eligible" in lowered:
        return True
    if "gold" in lowered:
        return key not in SAFE_ATTESTATIONS
    return False


def _reject_forbidden_keys(value: Any, context: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_context = f"{context}.{key}"
            if key in SAFE_ATTESTATIONS:
                expected = SAFE_ATTESTATIONS[key]
                if child is not expected:
                    raise ContractError(
                        f"{child_context}: safe attestation must be {expected!r}"
                    )
            elif _is_forbidden_key(key):
                raise ContractError(f"{child_context}: forbidden label/gold/metric key")
            _reject_forbidden_keys(child, child_context)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_keys(child, f"{context}[{index}]")


def _item_id(row: dict[str, Any], context: str) -> str:
    identity = row.get("identity")
    if isinstance(identity, dict):
        pilot_id = identity.get("pilot_item_id")
        item_id = identity.get("item_id")
        value = pilot_id or item_id
        if pilot_id is not None and item_id is not None and pilot_id != item_id:
            raise ContractError(f"{context}: item_id and pilot_item_id disagree")
    else:
        value = row.get("pilot_item_id") or row.get("item_id")
    if not isinstance(value, str) or ITEM_ID_PATTERN.fullmatch(value) is None:
        raise ContractError(f"{context}: invalid item identity")
    return value


def _candidate_has_popup_scope(candidate: dict[str, Any]) -> bool:
    features = candidate.get("features")
    if not isinstance(features, dict):
        return False
    component_label = features.get("component_label")
    if isinstance(component_label, str) and component_label.casefold() in {
        "modal",
        "advertisement",
    }:
        return True
    marker_values: list[str] = []
    for value in (features.get("component_label"), features.get("class")):
        if isinstance(value, str):
            marker_values.append(value)
    ancestors = features.get("ancestors", [])
    if isinstance(ancestors, list):
        for ancestor in ancestors:
            if isinstance(ancestor, str):
                marker_values.append(ancestor)
            elif isinstance(ancestor, dict):
                marker_values.extend(
                    value for value in ancestor.values() if isinstance(value, str)
                )
    return any(
        any(marker in value.casefold() for marker in ("dialog", "popup", "overlay"))
        for value in marker_values
    )


def _derive_gap(item: dict[str, Any], item_id: str) -> tuple[list[str], int]:
    candidates = item.get("candidates")
    if not isinstance(candidates, list) or not all(
        isinstance(candidate, dict) for candidate in candidates
    ):
        raise ContractError(f"{item_id}: candidates must be an object list")
    scoped = [candidate for candidate in candidates if _candidate_has_popup_scope(candidate)]
    if not scoped:
        reasons = ["ambiguous"]
    else:
        reason_set: set[str] = set()
        has_message = False
        for candidate in scoped:
            features = candidate.get("features", {})
            normalized = candidate.get("normalized")
            if not isinstance(normalized, dict):
                raise ContractError(f"{item_id}: candidate normalized fields are required")
            if normalized.get("visible") is False:
                continue
            declared = features.get("gap_reasons", [])
            if not isinstance(declared, list) or not all(
                isinstance(reason, str) and reason in GAP_SEVERITY for reason in declared
            ):
                raise ContractError(f"{item_id}: gap_reasons are invalid")
            reason_set.update(declared)
            has_message = has_message or any(
                isinstance(normalized.get(field), str)
                and bool(normalized[field].strip())
                for field in ("name_or_text", "value_or_hint")
            )
        if not has_message:
            reason_set.add("missing")
        observations = item.get("observations")
        if not isinstance(observations, list):
            raise ContractError(f"{item_id}: observations must be a list")
        for observation in observations:
            if not isinstance(observation, dict):
                raise ContractError(f"{item_id}: observation must be an object")
            representation = observation.get("structured_representation", {})
            if not isinstance(representation, dict):
                raise ContractError(
                    f"{item_id}: structured_representation must be an object"
                )
            if (
                representation.get("availability") == "missing"
                or representation.get("node_count") == 0
            ):
                reason_set.add("missing")
        reasons = sorted(reason_set)
    score = max((GAP_SEVERITY[reason] for reason in reasons), default=0)
    return reasons, score


def _validate_items(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        _reject_forbidden_keys(row)
        item_id = _item_id(row, "item snapshot")
        if item_id in by_id:
            raise ContractError(f"duplicate item snapshot identity: {item_id}")
        metadata = row.get("metadata")
        if not isinstance(metadata, dict):
            raise ContractError(f"{item_id}: metadata is required")
        required = {
            "gold_blind": True,
            "gold_used": False,
            "scored": False,
            "paper_result_eligible": False,
            "action_mode": "no_action",
        }
        for key, expected in required.items():
            if metadata.get(key) != expected:
                raise ContractError(f"{item_id}: metadata.{key} must be {expected!r}")
        if row.get("action_attempts") != []:
            raise ContractError(f"{item_id}: action_attempts must be empty")
        if row.get("decision", {}).get("policy", {}).get("decision") != "no_action":
            raise ContractError(f"{item_id}: decision must be no_action")
        reasons, score = _derive_gap(row, item_id)
        by_id[item_id] = {"gap_reasons": reasons, "gap_severity_score": score}
    return by_id


def _validate_method_results(
    rows: list[dict[str, Any]], items: dict[str, dict[str, Any]]
) -> None:
    selected: dict[str, dict[str, Any]] = {}
    for row in rows:
        _reject_forbidden_keys(row)
        if row.get("method_id") != SOURCE_METHOD_ID:
            continue
        item_id = _item_id(row, "method-results row")
        if item_id in selected:
            raise ContractError(f"duplicate method-results identity: {item_id}")
        if row.get("action_policy") != "no_action":
            raise ContractError(f"{item_id}: method result must be action-free")
        for key in ("human_gold_used", "scored", "paper_result_eligible"):
            if row.get(key) is not False:
                raise ContractError(f"{item_id}: method result {key} must be false")
        expected_visual_call = bool(items.get(item_id, {}).get("gap_reasons"))
        if row.get("visual_called") is not expected_visual_call:
            raise ContractError(f"{item_id}: method route disagrees with derived gap route")
        route = row.get("route_reason")
        valid_routes = (
            {"visual_evidence_missing_or_unstable", "visual_frozen_prediction"}
            if expected_visual_call
            else {"popup_scoped_structure_sufficient"}
        )
        if route not in valid_routes:
            raise ContractError(f"{item_id}: method route_reason is inconsistent")
        selected[item_id] = row
    expected = set(items)
    actual = set(selected)
    if actual != expected:
        raise ContractError(
            "method-results item coverage mismatch: "
            f"missing={sorted(expected - actual)} unexpected={sorted(actual - expected)}"
        )


def _validate_visual_rows(
    rows: list[dict[str, Any]], item_ids: set[str]
) -> dict[str, str]:
    seen: set[str] = set()
    config_hashes: set[str] = set()
    protocol_hashes: set[str] = set()
    declared_bank_hashes: set[str] = set()
    for row in rows:
        _reject_forbidden_keys(row)
        item_id = _item_id(row, "visual-bank row")
        if item_id in seen:
            raise ContractError(f"duplicate visual-bank identity: {item_id}")
        seen.add(item_id)
        for key in ("human_gold_used", "scored", "paper_result_eligible"):
            if row.get(key) is not False:
                raise ContractError(f"{item_id}: visual bank {key} must be false")
        config_hash = row.get("model_config_sha256")
        if not isinstance(config_hash, str) or SHA256_PATTERN.fullmatch(config_hash) is None:
            raise ContractError(f"{item_id}: visual model config hash is invalid")
        config_hashes.add(config_hash)
        for key, target in (
            ("protocol_sha256", protocol_hashes),
            ("visual_bank_sha256", declared_bank_hashes),
        ):
            value = row.get(key)
            if value is not None:
                if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
                    raise ContractError(f"{item_id}: visual {key} is invalid")
                target.add(value)
    if seen != item_ids:
        raise ContractError(
            "visual-bank item coverage mismatch: "
            f"missing={sorted(item_ids - seen)} unexpected={sorted(seen - item_ids)}"
        )
    if len(config_hashes) != 1:
        raise ContractError("visual-bank model_config_sha256 is not uniform")
    if len(protocol_hashes) > 1 or len(declared_bank_hashes) > 1:
        raise ContractError("visual-bank protocol or declared bank hash is not uniform")
    return {
        "visual_model_config_sha256": next(iter(config_hashes)),
        "visual_protocol_sha256": next(iter(protocol_hashes), ""),
        "visual_declared_bank_sha256": next(iter(declared_bank_hashes), ""),
    }


def _validate_timestamp(value: str) -> str:
    if UTC_TIMESTAMP_PATTERN.fullmatch(value) is None:
        raise ContractError("freeze timestamp must be canonical UTC YYYY-MM-DDTHH:MM:SSZ")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise ContractError(
            "freeze timestamp must be canonical UTC YYYY-MM-DDTHH:MM:SSZ"
        ) from error
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ContractError("freeze timestamp must be canonical UTC YYYY-MM-DDTHH:MM:SSZ")
    return value


def _selection_hash(item_ids: list[str]) -> str:
    return _sha256(_canonical_json(item_ids))


def _build_ledger(
    *,
    items: dict[str, dict[str, Any]],
    seed: int,
    freeze_timestamp: str,
    item_payload: bytes,
    visual_payload: bytes,
    method_payload: bytes,
    visual_hashes: dict[str, str],
) -> dict[str, Any]:
    severity_policy = {
        "status": "proposed_operating_point_policy",
        "score_aggregation": "maximum_declared_or_derived_gap_severity",
        "severity_scores": dict(sorted(GAP_SEVERITY.items())),
        "mg_pu_ranking": "gap_severity_score_desc_then_item_id_asc",
        "seeded_random_algorithm": "sha256('seeded-random-k-v1|seed|item_id')",
        "seeded_random_ranking": "sha256_seed_item_id_asc_then_item_id_asc",
        "budget_unit": "items_with_visual_access",
        "operating_points": [name for name, _, _, _ in OPERATING_POINTS],
    }
    config = {
        "source_method_id": SOURCE_METHOD_ID,
        "seed": seed,
        "policy": severity_policy,
    }
    severity_ranked = sorted(
        (
            {
                "item_id": item_id,
                "gap_reasons": item["gap_reasons"],
                "gap_severity_score": item["gap_severity_score"],
            }
            for item_id, item in items.items()
        ),
        key=lambda row: (-row["gap_severity_score"], row["item_id"]),
    )
    random_ranked = sorted(
        items,
        key=lambda item_id: (
            _sha256(f"seeded-random-k-v1|{seed}|{item_id}".encode("utf-8")),
            item_id,
        ),
    )
    operating_points: dict[str, Any] = {}
    budget_commitments: list[dict[str, Any]] = []
    item_count = len(items)
    for name, fraction, numerator, denominator in OPERATING_POINTS:
        k = (numerator * item_count + denominator - 1) // denominator
        mgpu_selected = [
            {**row, "rank": rank}
            for rank, row in enumerate(severity_ranked[:k], 1)
        ]
        mgpu_ids = [row["item_id"] for row in mgpu_selected]
        random_ids = random_ranked[:k]
        overlap_count = len(set(mgpu_ids).intersection(random_ids))
        same_selected_item_set = set(mgpu_ids) == set(random_ids)
        selection_relationship = {
            "same_selected_item_set": same_selected_item_set,
            "overlap_count": overlap_count,
            "overlap_fraction_of_k": f"{overlap_count / k:.6f}",
            "comparison_interpretation": (
                "budget_and_item_matched"
                if same_selected_item_set
                else "budget_matched_not_item_matched"
            ),
        }
        budget = {
            "operating_point": name,
            "fraction": fraction,
            "item_count": item_count,
            "k": k,
            "unit": "items_with_visual_access",
        }
        budget_sha256 = _sha256(_canonical_json(budget))
        operating_points[name] = {
            "fraction": fraction,
            "k": k,
            "budget_sha256": budget_sha256,
            "selection_relationship": selection_relationship,
            "mg_pu": {
                "selected": mgpu_selected,
                "selected_item_ids": mgpu_ids,
                "selected_item_set_sha256": _selection_hash(sorted(mgpu_ids)),
                "selected_ledger_sha256": _sha256(_canonical_json(mgpu_selected)),
            },
            "seeded_random": {
                "seed": seed,
                "selected_item_ids": random_ids,
                "selected_item_set_sha256": _selection_hash(sorted(random_ids)),
                "selected_ledger_sha256": _sha256(_canonical_json(random_ids)),
            },
        }
        budget_commitments.append(
            {
                **budget,
                "budget_sha256": budget_sha256,
                "mg_pu_selected_ledger_sha256": operating_points[name]["mg_pu"][
                    "selected_ledger_sha256"
                ],
                "seeded_random_selected_ledger_sha256": operating_points[name][
                    "seeded_random"
                ]["selected_ledger_sha256"],
                "selection_relationship": selection_relationship,
            }
        )

    input_hashes = {
        "item_snapshot_sha256": _sha256(item_payload),
        "visual_bank_input_sha256": _sha256(visual_payload),
        "method_results_sha256": _sha256(method_payload),
    }
    hashes = {
        **input_hashes,
        **visual_hashes,
        "item_identity_sha256": _selection_hash(sorted(items)),
        "input_bundle_sha256": _sha256(_canonical_json(input_hashes)),
        "config_sha256": _sha256(_canonical_json(config)),
        "implementation_sha256": _sha256(Path(__file__).read_bytes()),
        "budget_ledger_sha256": _sha256(_canonical_json(budget_commitments)),
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "status": "frozen_pregold_operating_point_ledgers",
        "policy_status": "proposed_operating_point_policy",
        "scope": "popup_message_judgment_v1",
        "action_policy": "no_action",
        "freeze_timestamp": freeze_timestamp,
        "gold_release_id": None,
        "human_gold_used": False,
        "scored": False,
        "paper_result_eligible": False,
        "seed": seed,
        "item_count": item_count,
        "source_method_id": SOURCE_METHOD_ID,
        "policy": severity_policy,
        "hashes": hashes,
        "operating_points": operating_points,
    }


def _write_private_new(path: Path, payload: bytes) -> None:
    if path.parent.name != "private" or not path.name.endswith(".private.json"):
        raise ContractError("output must be a *.private.json file under a private directory")
    if path.exists():
        raise ContractError("output already exists; frozen ledger replacement is forbidden")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
        temporary.chmod(0o600)
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise ContractError(
                "output already exists; frozen ledger replacement is forbidden"
            ) from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", required=True, type=Path)
    parser.add_argument("--visual-bank", required=True, type=Path)
    parser.add_argument("--method-results", required=True, type=Path)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--freeze-timestamp", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.seed < 0 or args.seed > 2**63 - 1:
            raise ContractError("seed must be an integer in [0, 2^63-1]")
        freeze_timestamp = _validate_timestamp(args.freeze_timestamp)
        if args.output.exists():
            raise ContractError("output already exists; frozen ledger replacement is forbidden")
        item_rows, item_payload = _read_jsonl(args.items)
        visual_rows, visual_payload = _read_jsonl(args.visual_bank)
        method_rows, method_payload = _read_jsonl(args.method_results)
        items = _validate_items(item_rows)
        _validate_method_results(method_rows, items)
        visual_hashes = _validate_visual_rows(visual_rows, set(items))
        ledger = _build_ledger(
            items=items,
            seed=args.seed,
            freeze_timestamp=freeze_timestamp,
            item_payload=item_payload,
            visual_payload=visual_payload,
            method_payload=method_payload,
            visual_hashes=visual_hashes,
        )
        _write_private_new(args.output, _canonical_json(ledger) + b"\n")
    except ContractError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "status": ledger["status"],
                "item_count": ledger["item_count"],
                "operating_points": {
                    name: value["k"] for name, value in ledger["operating_points"].items()
                },
                "budget_ledger_sha256": ledger["hashes"]["budget_ledger_sha256"],
                "human_gold_used": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
