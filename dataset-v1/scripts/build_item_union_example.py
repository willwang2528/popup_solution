#!/usr/bin/env python3
"""Build a public, non-empirical view of one schema-fixture item union."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping


class UnionExampleError(ValueError):
    """Raised when the public union inputs disagree or are incomplete."""


ROOT = Path(__file__).resolve().parents[1]
FIELD_CATALOG = ROOT / "schema" / "field_catalog.json"
CROSSWALK = ROOT / "schema" / "source_to_item_crosswalk.json"
ITEM_TEMPLATE = ROOT / "data" / "item.template.json"
SCHEMA_FIXTURES = ROOT / "data" / "items.schema-fixture.jsonl"
DEFAULT_OUTPUT = ROOT / "ITEM_UNION_EXAMPLE.md"


ADVANCED_RECOVERY_FIELDS = (
    ("D", "/verification/dismissal/D", ("verification", "dismissal", "D")),
    (
        "C_tech",
        "/verification/technical_context_recovery/C_tech",
        ("verification", "technical_context_recovery", "C_tech"),
    ),
    (
        "C_a11y",
        "/verification/accessible_context_recovery/C_a11y",
        ("verification", "accessible_context_recovery", "C_a11y"),
    ),
    ("T", "/verification/task/T", ("verification", "task", "T")),
    (
        "VTR_tech",
        "/verification/metrics/VTR_tech",
        ("verification", "metrics", "VTR_tech"),
    ),
    (
        "A_VTR",
        "/verification/metrics/A_VTR",
        ("verification", "metrics", "A_VTR"),
    ),
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise UnionExampleError(message)


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _source_provenance_complete(namespace: str, field: Mapping[str, Any]) -> bool:
    if namespace == "literature_14":
        paper_ids = field.get("paper_ids")
        evidence_status = field.get("evidence_status")
        if not isinstance(paper_ids, Mapping) or not isinstance(evidence_status, Mapping):
            return False
        paper_references = list(paper_ids.get("core_experimental_seed", [])) + list(
            paper_ids.get("schema_method_reference", [])
        )
        return bool(paper_references) and _nonempty_string(evidence_status.get("overall"))
    if namespace == "our_method":
        return all(
            _nonempty_string(field.get(key))
            for key in ("label_source", "missing_value_policy", "why_needed")
        )
    return False


def _source_provenance_summary(namespace: str, field: Mapping[str, Any]) -> str:
    if namespace == "literature_14":
        paper_ids = field["paper_ids"]
        papers = sorted(
            set(paper_ids["core_experimental_seed"])
            | set(paper_ids["schema_method_reference"])
        )
        return f"papers={','.join(papers)}; evidence={field['evidence_status']['overall']}"
    return (
        f"label_source={field['label_source']}; "
        f"missing={field['missing_value_policy']}; stage={field.get('stage', 'not_specified')}"
    )


def _markdown_text(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _validate_source_union(
    catalog: Mapping[str, Any], crosswalk: Mapping[str, Any]
) -> dict[str, dict[str, int]]:
    namespace_specs = (
        ("literature_14", "literature_fields"),
        ("our_method", "our_method_fields"),
    )
    catalog_by_key: dict[tuple[str, str], Mapping[str, Any]] = {}
    catalog_counts: dict[str, int] = {}
    for namespace, catalog_key in namespace_specs:
        fields = catalog.get(catalog_key)
        _require(isinstance(fields, list), f"catalog {catalog_key} must be a list")
        catalog_counts[namespace] = len(fields)
        for field in fields:
            _require(isinstance(field, Mapping), f"{namespace} field must be an object")
            source_path = field.get("field_path")
            _require(_nonempty_string(source_path), f"{namespace} field_path is missing")
            key = (namespace, source_path)
            _require(key not in catalog_by_key, f"duplicate catalog source field: {key}")
            catalog_by_key[key] = field

    total = sum(catalog_counts.values())
    expected_catalog_counts = {
        "literature_atomic_fields": catalog_counts["literature_14"],
        "our_method_atomic_fields": catalog_counts["our_method"],
        "source_records_total": total,
    }
    _require(catalog.get("counts") == expected_catalog_counts, "catalog declared counts are stale")

    expected_crosswalk_counts = {**catalog_counts, "total": total}
    _require(
        crosswalk.get("source_counts") == expected_crosswalk_counts,
        "crosswalk declared counts disagree with the catalog",
    )
    _require(
        catalog.get("schema_version") == crosswalk.get("schema_version"),
        "catalog and crosswalk schema versions differ",
    )

    entries = crosswalk.get("entries")
    _require(isinstance(entries, list), "crosswalk entries must be a list")
    crosswalk_by_key: dict[tuple[str, str], Mapping[str, Any]] = {}
    mapped_counts = {namespace: 0 for namespace, _ in namespace_specs}
    provenance_counts = {namespace: 0 for namespace, _ in namespace_specs}
    for entry in entries:
        _require(isinstance(entry, Mapping), "crosswalk entry must be an object")
        namespace = entry.get("source_namespace")
        source_path = entry.get("source_field_path")
        key = (namespace, source_path)
        _require(key in catalog_by_key, f"crosswalk contains unknown source field: {key}")
        _require(key not in crosswalk_by_key, f"duplicate crosswalk source field: {key}")
        crosswalk_by_key[key] = entry
        pointers = entry.get("canonical_item_pointers")
        _require(
            isinstance(pointers, list)
            and bool(pointers)
            and all(_nonempty_string(pointer) and pointer.startswith("/") for pointer in pointers),
            f"{key} has no canonical item pointer",
        )
        mapped_counts[namespace] += 1
        _require(
            entry.get("source_metadata") == catalog_by_key[key],
            f"{key} crosswalk metadata differs from the catalog",
        )
        _require(
            _source_provenance_complete(namespace, catalog_by_key[key]),
            f"{key} source provenance is incomplete",
        )
        provenance_counts[namespace] += 1

    _require(set(crosswalk_by_key) == set(catalog_by_key), "catalog/crosswalk source-field presence differs")
    return {
        namespace: {
            "catalog": catalog_counts[namespace],
            "crosswalk": sum(1 for key in crosswalk_by_key if key[0] == namespace),
            "mapped": mapped_counts[namespace],
            "provenance": provenance_counts[namespace],
        }
        for namespace, _ in namespace_specs
    }


def _nested_value(item: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = item
    for key in path:
        _require(isinstance(value, Mapping) and key in value, f"item is missing {'/'.join(path)}")
        value = value[key]
    return value


def _validate_fixture(item_template: Mapping[str, Any], item: Mapping[str, Any]) -> int:
    _require(set(item_template) == set(item), "template and fixture top-level containers differ")
    _require(
        _nested_value(item_template, ("identity", "item_id"))
        == _nested_value(item, ("identity", "item_id")),
        "template and fixture item IDs differ",
    )
    _require(
        _nested_value(item, ("identity", "record_kind")) == "synthetic_schema_fixture",
        "union example must use only a synthetic schema fixture",
    )
    for key in ("source_origin", "evidence_level"):
        _require(
            _nested_value(item, ("provenance", key)) == "synthetic_schema_fixture",
            f"fixture {key} is not synthetic_schema_fixture",
        )
    _require(
        _nonempty_string(_nested_value(item, ("provenance", "license_or_permission"))),
        "fixture license/permission disclosure is missing",
    )
    _require(
        _nested_value(item, ("quality", "synthetic_or_fixture_disclosed")) is True,
        "fixture disclosure quality flag is false",
    )
    _require(
        _nested_value(item, ("decision", "policy", "decision")) in {"no_action", "abstain"},
        "v1 fixture has an actionful decision",
    )
    _require(item.get("action_attempts") == [], "v1 fixture contains action attempts")
    _require(
        _nested_value(
            item,
            ("message_judgment", "eligibility", "eligible_for_advanced_recovery_metric"),
        )
        is False,
        "fixture is incorrectly eligible for advanced Recovery metrics",
    )

    field_status = item.get("observability", {}).get("field_status", {})
    _require(isinstance(field_status, Mapping), "observability.field_status must be an object")
    for _, pointer, path in ADVANCED_RECOVERY_FIELDS:
        _require(_nested_value(item, path) is None, f"advanced Recovery field {pointer} must be null")
        _require(pointer in field_status, f"{pointer} status is missing")
        _require(field_status[pointer] == "not_applicable", f"{pointer} status must be not_applicable")
    return len(item)


def render_item_union_example(
    *,
    catalog: Mapping[str, Any],
    crosswalk: Mapping[str, Any],
    item_template: Mapping[str, Any],
    item: Mapping[str, Any],
) -> str:
    """Render counts derived from the supplied source-field catalog."""

    completeness = _validate_source_union(catalog, crosswalk)
    container_count = _validate_fixture(item_template, item)
    literature_count = completeness["literature_14"]["catalog"]
    our_method_count = completeness["our_method"]["catalog"]
    total = literature_count + our_method_count
    lines = [
        "# Item 字段并集示例",
        "",
        "> 这是仅由公开 schema 产物生成的视图：该 item 是 `synthetic_schema_fixture`，不是经验数据，也不是 gold 数据。",
        "",
        "## Fixture 披露",
        "",
        "| 属性 | 值 |",
        "|---|---|",
        f"| Item ID | `{item['identity']['item_id']}` |",
        "| 记录类型 | `synthetic_schema_fixture` |",
        "| 证据级别 | `synthetic_schema_fixture` |",
        "| 是否为经验数据 | **否** |",
        "| 是否为 gold 数据 | **否** |",
        f"| 动作策略 | `{item['decision']['policy']['decision']}` |",
        f"| 动作尝试次数 | {len(item['action_attempts'])} |",
        "",
        "## 来源字段并集",
        "",
        "| 来源类别 | 原子 source field 数 |",
        "|---|---:|",
        f"| `literature_14` | {literature_count} |",
        f"| `our_method` | {our_method_count} |",
        f"| **并集总计** | **{total}** |",
        "",
        "## 机器审计完整性",
        "",
        "这里的 presence 表示：每个 source-field 记录在公开 catalog 与 crosswalk 中恰好出现一次，并且至少具有一个 canonical pointer；它不表示该 v1 item 的每个 nullable 值都已被观测。",
        "",
        "Provenance 完整性表示：对应来源类别要求的 source metadata 已齐备；它不构成经验验证。",
        "",
        "| 来源类别 | Catalog presence | Crosswalk presence | 非空 canonical mapping | Provenance 完整 |",
        "|---|---:|---:|---:|---:|",
        (
            f"| `literature_14` | {completeness['literature_14']['catalog']} | "
            f"{completeness['literature_14']['crosswalk']} | {completeness['literature_14']['mapped']} | "
            f"{completeness['literature_14']['provenance']} |"
        ),
        (
            f"| `our_method` | {completeness['our_method']['catalog']} | "
            f"{completeness['our_method']['crosswalk']} | {completeness['our_method']['mapped']} | "
            f"{completeness['our_method']['provenance']} |"
        ),
        f"| **并集总计** | **{total}** | **{total}** | **{total}** | **{total}** |",
        "",
        "| Item 形状检查 | 完整 |",
        "|---|---:|",
        f"| Template/fixture 顶层 containers | {container_count}/{container_count} |",
        "",
        "## 此单个 item 的 canonical containers",
        "",
        ", ".join(f"`{key}`" for key in sorted(item)),
        "",
        "## 完整 source field 清单",
        "",
        "下表直接由通过校验的公开 crosswalk 生成；只列字段元数据，不列任何 item 值。",
        "",
        "| 序号 | Namespace | Source field path | Canonical pointer(s) | Provenance 摘要 |",
        "|---:|---|---|---|---|",
    ]
    for index, entry in enumerate(crosswalk["entries"], start=1):
        pointers = "<br>".join(f"`{pointer}`" for pointer in entry["canonical_item_pointers"])
        provenance_summary = _markdown_text(
            _source_provenance_summary(entry["source_namespace"], entry["source_metadata"])
        )
        lines.append(
            f"| {index} | `{entry['source_namespace']}` | `{entry['source_field_path']}` | "
            f"{pointers} | {provenance_summary} |"
        )
    lines.extend(
        [
            "",
        "## 进阶 Recovery 兼容字段",
        "",
        "这些字段仅为 schema 兼容性保留，不属于 v1 成功定义。",
        "",
        "| 字段 | Canonical pointer | 存储值 | v1 状态 |",
        "|---|---|---|---|",
        ]
    )
    for field_name, pointer, _ in ADVANCED_RECOVERY_FIELDS:
        lines.append(f"| `{field_name}` | `{pointer}` | `null` | `not_applicable` |")
    lines.extend(
        [
            "",
            "## 公开输入与机器校验",
            "",
            "输入：`schema/field_catalog.json`、`schema/source_to_item_crosswalk.json`、`data/item.template.json` 与 `data/items.schema-fixture.jsonl`。",
            "",
            "```bash",
            "../../.venv/bin/python3 scripts/build_item_union_example.py --check",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(payload, dict), f"{path} must contain a JSON object")
    return payload


def _load_matching_fixture(path: Path, item_id: str) -> dict[str, Any]:
    matches = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        _require(isinstance(row, dict), f"{path}:{line_number} must be a JSON object")
        if row.get("identity", {}).get("item_id") == item_id:
            matches.append(row)
    _require(len(matches) == 1, f"expected one schema fixture for template item_id {item_id}")
    return matches[0]


def render_public_repository_example() -> str:
    """Load only the four public union artifacts and render the selected fixture."""

    catalog = _load_json(FIELD_CATALOG)
    crosswalk = _load_json(CROSSWALK)
    item_template = _load_json(ITEM_TEMPLATE)
    item_id = _nested_value(item_template, ("identity", "item_id"))
    _require(_nonempty_string(item_id), "template item_id is missing")
    item = _load_matching_fixture(SCHEMA_FIXTURES, item_id)
    return render_item_union_example(
        catalog=catalog,
        crosswalk=crosswalk,
        item_template=item_template,
        item=item,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if --output is missing or differs from the deterministic rendering.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        rendered = render_public_repository_example()
        if args.check:
            if not args.output.is_file() or args.output.read_text(encoding="utf-8") != rendered:
                print(f"error: stale or missing item union example: {args.output}", file=sys.stderr)
                return 2
            print(f"verified {args.output}")
            return 0
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"wrote {args.output}")
        return 0
    except (UnionExampleError, OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
