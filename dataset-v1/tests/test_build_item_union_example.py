from __future__ import annotations

import copy
import importlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


DATASET_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATASET_ROOT / "scripts"))


def literature_field(index: int) -> dict:
    return {
        "field_path": f"literature.field_{index}",
        "type": "string | null",
        "requiredness": "conditional",
        "paper_ids": {
            "core_experimental_seed": [f"paper_{index}"],
            "schema_method_reference": [],
        },
        "method_stage": "discovery",
        "evidence_status": {"overall": "reported"},
        "notes": "Synthetic test metadata.",
    }


def our_field(index: int) -> dict:
    return {
        "field_path": f"ours.field_{index}",
        "type": "string | null",
        "requiredness": "conditional",
        "stage": "message_judgment",
        "label_source": "collector",
        "missing_value_policy": "explicit_reason_code",
        "why_needed": "Synthetic test metadata.",
    }


def minimal_item() -> dict:
    return {
        "identity": {
            "item_id": "fixture.test.union.0001",
            "record_kind": "synthetic_schema_fixture",
        },
        "provenance": {
            "source_origin": "synthetic_schema_fixture",
            "evidence_level": "synthetic_schema_fixture",
            "license_or_permission": "schema fixture; no empirical content",
        },
        "decision": {"policy": {"decision": "no_action"}},
        "action_attempts": [],
        "message_judgment": {
            "eligibility": {"eligible_for_advanced_recovery_metric": False}
        },
        "observability": {
            "field_status": {
                "/verification/dismissal/D": "not_applicable",
                "/verification/technical_context_recovery/C_tech": "not_applicable",
                "/verification/accessible_context_recovery/C_a11y": "not_applicable",
                "/verification/task/T": "not_applicable",
                "/verification/metrics/VTR_tech": "not_applicable",
                "/verification/metrics/A_VTR": "not_applicable",
            }
        },
        "verification": {
            "dismissal": {"D": None},
            "technical_context_recovery": {"C_tech": None},
            "accessible_context_recovery": {"C_a11y": None},
            "task": {"T": None},
            "metrics": {"VTR_tech": None, "A_VTR": None},
        },
        "quality": {"synthetic_or_fixture_disclosed": True},
    }


def miniature_artifacts() -> tuple[dict, dict, dict, dict]:
    literature = [literature_field(1)]
    ours = [our_field(1), our_field(2)]
    catalog = {
        "schema_version": "test-v1",
        "counts": {
            "literature_atomic_fields": 1,
            "our_method_atomic_fields": 2,
            "source_records_total": 3,
        },
        "literature_fields": literature,
        "our_method_fields": ours,
    }
    entries = []
    for namespace, fields in (("literature_14", literature), ("our_method", ours)):
        for field in fields:
            entries.append(
                {
                    "source_namespace": namespace,
                    "source_field_path": field["field_path"],
                    "canonical_item_pointers": ["/identity/item_id"],
                    "mapping_kind": "semantic_union",
                    "source_metadata": field,
                }
            )
    crosswalk = {
        "schema_version": "test-v1",
        "source_counts": {"literature_14": 1, "our_method": 2, "total": 3},
        "entries": entries,
    }
    item = minimal_item()
    return catalog, crosswalk, item, copy.deepcopy(item)


class ItemUnionExampleTests(unittest.TestCase):
    def assert_rejected(
        self,
        catalog: dict,
        crosswalk: dict,
        template: dict,
        item: dict,
    ) -> None:
        generator = importlib.import_module("build_item_union_example")
        with self.assertRaises(generator.UnionExampleError):
            generator.render_item_union_example(
                catalog=catalog,
                crosswalk=crosswalk,
                item_template=template,
                item=item,
            )

    def test_source_counts_are_derived_instead_of_hardcoded(self):
        try:
            generator = importlib.import_module("build_item_union_example")
        except ModuleNotFoundError as exc:
            self.fail(f"item union example generator is missing: {exc}")

        catalog, crosswalk, template, item = miniature_artifacts()
        rendered = generator.render_item_union_example(
            catalog=catalog,
            crosswalk=crosswalk,
            item_template=template,
            item=item,
        )

        self.assertIn("| `literature_14` | 1 |", rendered)
        self.assertIn("| `our_method` | 2 |", rendered)
        self.assertIn("| **并集总计** | **3** |", rendered)
        self.assertNotIn("255", rendered)

    def test_fixture_disclosure_and_advanced_recovery_status_are_explicit(self):
        generator = importlib.import_module("build_item_union_example")
        catalog, crosswalk, template, item = miniature_artifacts()

        rendered = generator.render_item_union_example(
            catalog=catalog,
            crosswalk=crosswalk,
            item_template=template,
            item=item,
        )

        self.assertIn("`synthetic_schema_fixture`", rendered)
        self.assertIn("| 是否为经验数据 | **否** |", rendered)
        self.assertIn("| 是否为 gold 数据 | **否** |", rendered)
        self.assertIn("| 动作尝试次数 | 0 |", rendered)
        for field_name in ("D", "C_tech", "C_a11y", "T", "VTR_tech", "A_VTR"):
            with self.subTest(field_name=field_name):
                self.assertIn(f"| `{field_name}` |", rendered)
        self.assertEqual(rendered.count("| `null` | `not_applicable` |"), 6)

    def test_presence_and_provenance_completeness_are_machine_audited(self):
        generator = importlib.import_module("build_item_union_example")
        catalog, crosswalk, template, item = miniature_artifacts()

        rendered = generator.render_item_union_example(
            catalog=catalog,
            crosswalk=crosswalk,
            item_template=template,
            item=item,
        )

        self.assertIn("| `literature_14` | 1 | 1 | 1 | 1 |", rendered)
        self.assertIn("| `our_method` | 2 | 2 | 2 | 2 |", rendered)
        self.assertIn("| **并集总计** | **3** | **3** | **3** | **3** |", rendered)
        self.assertIn("| Template/fixture 顶层 containers | 8/8 |", rendered)
        self.assertIn("这里的 presence 表示", rendered)

    def test_readable_view_lists_the_item_containers_and_check_command(self):
        generator = importlib.import_module("build_item_union_example")
        catalog, crosswalk, template, item = miniature_artifacts()

        rendered = generator.render_item_union_example(
            catalog=catalog,
            crosswalk=crosswalk,
            item_template=template,
            item=item,
        )

        self.assertIn("## 此单个 item 的 canonical containers", rendered)
        for container in ("identity", "provenance", "message_judgment", "verification"):
            with self.subTest(container=container):
                self.assertIn(f"`{container}`", rendered)
        self.assertIn("scripts/build_item_union_example.py --check", rendered)

    def test_every_source_field_has_one_readable_union_row(self):
        generator = importlib.import_module("build_item_union_example")
        catalog, crosswalk, template, item = miniature_artifacts()

        rendered = generator.render_item_union_example(
            catalog=catalog,
            crosswalk=crosswalk,
            item_template=template,
            item=item,
        )
        field_rows = [
            line
            for line in rendered.splitlines()
            if re.match(r"\| \d+ \| `(literature_14|our_method)` \|", line)
        ]

        self.assertEqual(len(field_rows), 3)
        self.assertEqual(sum("`literature_14`" in line for line in field_rows), 1)
        self.assertEqual(sum("`our_method`" in line for line in field_rows), 2)
        self.assertIn("`literature.field_1`", field_rows[0])
        self.assertIn("`/identity/item_id`", field_rows[0])
        self.assertIn("papers=paper_1; evidence=reported", field_rows[0])

    def test_human_facing_titles_and_table_headers_are_chinese(self):
        generator = importlib.import_module("build_item_union_example")
        catalog, crosswalk, template, item = miniature_artifacts()

        rendered = generator.render_item_union_example(
            catalog=catalog,
            crosswalk=crosswalk,
            item_template=template,
            item=item,
        )

        for label in (
            "# Item 字段并集示例",
            "## Fixture 披露",
            "## 来源字段并集",
            "## 机器审计完整性",
            "## 完整 source field 清单",
            "## 进阶 Recovery 兼容字段",
            "来源类别",
            "Provenance 摘要",
        ):
            with self.subTest(label=label):
                self.assertIn(label, rendered)
        self.assertNotIn("# Item field-union example", rendered)

    def test_incomplete_or_misrepresented_inputs_are_rejected(self):
        catalog, crosswalk, template, item = miniature_artifacts()
        cases = []

        stale_counts = copy.deepcopy(catalog)
        stale_counts["counts"]["source_records_total"] = 255
        cases.append(("stale catalog count", stale_counts, crosswalk, template, item))

        missing_crosswalk = copy.deepcopy(crosswalk)
        missing_crosswalk["entries"].pop()
        cases.append(("missing crosswalk entry", catalog, missing_crosswalk, template, item))

        empty_mapping = copy.deepcopy(crosswalk)
        empty_mapping["entries"][0]["canonical_item_pointers"] = []
        cases.append(("empty canonical mapping", catalog, empty_mapping, template, item))

        incomplete_provenance = copy.deepcopy(catalog)
        incomplete_provenance["literature_fields"][0]["paper_ids"] = {
            "core_experimental_seed": [],
            "schema_method_reference": [],
        }
        cases.append(
            ("incomplete source provenance", incomplete_provenance, crosswalk, template, item)
        )

        empirical_item = copy.deepcopy(item)
        empirical_item["identity"]["record_kind"] = "real_app"
        cases.append(("empirical item", catalog, crosswalk, template, empirical_item))

        actionful_item = copy.deepcopy(item)
        actionful_item["action_attempts"] = [{"attempt_id": "forbidden"}]
        cases.append(("actionful item", catalog, crosswalk, template, actionful_item))

        recovery_value = copy.deepcopy(item)
        recovery_value["verification"]["dismissal"]["D"] = True
        cases.append(("advanced Recovery value", catalog, crosswalk, template, recovery_value))

        for name, case_catalog, case_crosswalk, case_template, case_item in cases:
            with self.subTest(name=name):
                self.assert_rejected(
                    case_catalog,
                    case_crosswalk,
                    case_template,
                    case_item,
                )

    def test_missing_advanced_recovery_field_status_is_rejected(self):
        catalog, crosswalk, template, item = miniature_artifacts()
        del item["observability"]["field_status"]["/verification/dismissal/D"]

        self.assert_rejected(catalog, crosswalk, template, item)

    def test_cli_writes_and_checks_the_public_repository_artifact(self):
        script = DATASET_ROOT / "scripts" / "build_item_union_example.py"
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "ITEM_UNION_EXAMPLE.md"
            write_result = subprocess.run(
                [sys.executable, str(script), "--output", str(output)],
                cwd=DATASET_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(write_result.returncode, 0, write_result.stderr)
            self.assertTrue(output.is_file())
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("| `literature_14` | 90 |", rendered)
            self.assertIn("| `our_method` | 165 |", rendered)
            self.assertIn("| **并集总计** | **255** |", rendered)
            field_rows = [
                line
                for line in rendered.splitlines()
                if re.match(r"\| \d+ \| `(literature_14|our_method)` \|", line)
            ]
            self.assertEqual(len(field_rows), 255)
            self.assertEqual(sum("`literature_14`" in line for line in field_rows), 90)
            self.assertEqual(sum("`our_method`" in line for line in field_rows), 165)

            check_result = subprocess.run(
                [sys.executable, str(script), "--check", "--output", str(output)],
                cwd=DATASET_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(check_result.returncode, 0, check_result.stderr)

            output.write_text(rendered + "STALE\n", encoding="utf-8")
            stale_result = subprocess.run(
                [sys.executable, str(script), "--check", "--output", str(output)],
                cwd=DATASET_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(stale_result.returncode, 2)
            self.assertIn("stale", stale_result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
