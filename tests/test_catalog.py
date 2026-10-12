"""Offline regressions for real library invariants and corrupted input copies."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "civilization-os"
SCRIPT = SKILL / "scripts" / "catalog.py"
spec = importlib.util.spec_from_file_location("civilization_catalog", SCRIPT)
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = catalog.load_database(SKILL)

    def fixture_database(self):
        # Preserve real card/source structures but isolate synthetic test events.
        db = copy.deepcopy(self.db)
        db["cases"] = [copy.deepcopy(next(row for row in db["cases"] if row["id"] == "C001"))]
        for source in db["sources"]:
            if source["id"] in {"C-10", "C-11"}:
                source["origin_group"] = "neil-ashby-gps"
        self.relink(db)
        return db

    @staticmethod
    def relink(db):
        for model in db["models"]:
            model["case_ids"] = [row["id"] for row in db["cases"]
                                 if model["id"] in row["model_ids"]]

    def event_database(self):
        db = self.fixture_database()
        event = copy.deepcopy(db["cases"][0])
        event["id"] = "C9000"
        event["record_type"] = "evidence_event"
        event["result_type"] = "documented_event"
        event["event_key"] = "test:nasa:C9000"
        event["title"] = "测试事件 sentinel_positive_event"
        event["domain"] = "testing_event"
        event["provenance"] = {"source_id": event["source_ids"][0], "row_key": "test:C9000",
                               "locator": "Fixture record C9000"}
        event["verification"]["causal_confidence"] = "low"
        event["claims"][0]["claim_id"] = "C9000.001"
        event["claims"][1]["claim_id"] = "C9000.002"
        for field in ("decision_context", "observed_actions", "outcomes",
                      "transfer_conditions", "non_transfer_conditions", "model_mapping_note"):
            event.pop(field, None)
        db["cases"].append(event)
        self.relink(db)
        return db

    def assert_error(self, db, phrase):
        self.assertTrue(any(phrase in error for error in catalog.check_database(db)), phrase)

    def test_complete_library(self):
        self.assertEqual(catalog.check_database(self.db, SKILL), [])
        self.assertEqual(len(self.db["models"]), 100)
        self.assertGreaterEqual(len(self.db["cases"]), 10)

    def test_lookup_selects_relevant_card(self):
        found = catalog.search_rows(self.db["models"], "机会成本", 8)
        self.assertEqual(found[0]["id"], "P058")
        self.assertTrue(catalog.search_rows(self.db["cases"], "部署", 8))
        self.assertEqual(catalog.search_rows(self.db["models"], "a_word_not_present_7421", 8), [])

    def test_filter_applies_before_ranking(self):
        rows = catalog.search_rows(self.db["models"], "风险 选择", 8, domain="business")
        self.assertTrue(rows)
        self.assertTrue(all(row["domain"] == "business" for row in rows))

    def test_damaged_references_are_rejected(self):
        db = self.fixture_database()
        db["models"][0]["source_ids"] = ["MISSING"]
        db["cases"][0]["model_ids"] = ["P999"]
        self.assert_error(db, "MISSING")
        self.assert_error(db, "P999")

    def test_duplicate_and_missing_ids_are_rejected(self):
        db = self.fixture_database()
        db["models"][1]["id"] = db["models"][0]["id"]
        self.assert_error(db, "duplicate IDs")
        self.assert_error(db, "P001-P100")
        db["models"][1]["id"] = None
        self.assert_error(db, "missing IDs")

    def test_cross_table_ids_cannot_collide(self):
        for replacement in ("C001", "P001"):
            with self.subTest(replacement=replacement):
                db = self.fixture_database()
                db["sources"][0]["id"] = replacement
                self.assert_error(db, "global ID collision")

    def test_verification_and_dates_are_checked(self):
        db = self.fixture_database()
        db["cases"][0]["verification"]["status"] = "pending"
        db["sources"][0]["checked_on"] = "2026-02-30"
        self.assert_error(db, "unchecked cases")
        self.assert_error(db, "calendar date")

    def test_claim_source_must_be_in_case(self):
        db = self.fixture_database()
        outside = next(row["id"] for row in db["sources"]
                       if row["id"] not in db["cases"][0]["source_ids"])
        db["cases"][0]["claims"][0]["source_ids"] = [outside]
        self.assert_error(db, "absent from case.source_ids")

    def test_result_type_enum_is_enforced(self):
        for value in ("invented_success", ["reported_success"], None):
            with self.subTest(value=value):
                db = self.fixture_database()
                db["cases"][0]["result_type"] = value
                self.assert_error(db, "result_type")
        db = self.fixture_database()
        for result_type in ("regulatory_action", "near_miss"):
            db["cases"][0]["result_type"] = result_type
            self.assertEqual(catalog.check_database(db), [])
        db["cases"][0]["result_type"] = "documented_event"
        self.assert_error(db, "deep_case cannot use")

    def test_list_in_enums_returns_errors_without_typeerror(self):
        mutations = (
            ("model", "domain"), ("model", "kind"), ("source", "source_type"),
            ("case", "record_type"), ("case", "result_type"),
            ("verification", "fact_confidence"), ("verification", "causal_confidence"),
            ("claim", "evidence_strength"),
        )
        for group, field in mutations:
            with self.subTest(group=group, field=field):
                db = self.fixture_database()
                row = {"model": db["models"][0], "source": db["sources"][0],
                       "case": db["cases"][0],
                       "verification": db["cases"][0]["verification"],
                       "claim": db["cases"][0]["claims"][0]}[group]
                row[field] = ["invalid"]
                self.assert_error(db, field)

    def test_group_count_must_match_actual_origins(self):
        db = self.fixture_database()
        db["cases"][0]["verification"]["independent_source_groups"] = 999
        self.assert_error(db, "actual origin groups")
        for invalid in (0, True, "1"):
            db["cases"][0]["verification"]["independent_source_groups"] = invalid
            self.assert_error(db, "positive integer")

    def test_explicit_group_overrides_publisher_fallback(self):
        db = self.fixture_database()
        first = db["cases"][0]["source_ids"][0]
        source = copy.deepcopy(next(row for row in db["sources"] if row["id"] == first))
        source["id"] = "TEST-SECOND"
        source["publisher"] = "Different archive, same author"
        source["origin_group"] = "shared-origin"
        next(row for row in db["sources"] if row["id"] == first)["origin_group"] = "shared-origin"
        db["sources"].append(source)
        db["cases"][0]["source_ids"].append(source["id"])
        self.assertEqual(catalog.check_database(db), [])
        source.pop("origin_group")
        self.assert_error(db, "actual origin groups")
        db["cases"][0]["verification"]["independent_source_groups"] = 2
        self.assertEqual(catalog.check_database(db), [])

    def test_origin_group_must_be_nonempty_text(self):
        for value in ("", [], None):
            db = self.fixture_database()
            db["sources"][0]["origin_group"] = value
            self.assert_error(db, "origin_group")

    def test_legacy_deep_case_default_is_preserved(self):
        db = self.fixture_database()
        db["cases"][0].pop("record_type", None)
        self.assertEqual(catalog.record_type(db["cases"][0]), "deep_case")
        self.assertEqual(catalog.check_database(db), [])

    def test_evidence_event_can_omit_decision_story(self):
        self.assertEqual(catalog.check_database(self.event_database()), [])

    def test_unknown_actions_require_explicit_status_and_limitations(self):
        db = self.fixture_database()
        row = db["cases"][0]
        row["observed_actions"] = []
        row["observed_actions_status"] = "not_reported"
        row["verification"]["limitations"] = "报告未记载处置动作；建议不代表实施。"
        self.assertEqual(catalog.check_database(db), [])
        row.pop("observed_actions_status")
        self.assert_error(db, "observed_actions cannot be empty")
        row["observed_actions_status"] = "reported"
        self.assert_error(db, "observed_actions cannot be empty")
        row["observed_actions_status"] = "not_reported"
        row["verification"]["limitations"] = ""
        self.assert_error(db, "limitations")
        row["verification"]["limitations"] = "报告未记载处置动作。"
        row["observed_actions"] = ["仅建议整改，不代表实际处置。"]
        self.assert_error(db, "not_reported observed_actions")
        row["observed_actions"] = []
        for field in ("facts", "outcomes"):
            broken = copy.deepcopy(db)
            broken["cases"][0][field] = []
            self.assert_error(broken, field + " cannot be empty")

    def test_event_needs_key_provenance_and_low_causal_confidence(self):
        for field in ("event_key", "provenance"):
            with self.subTest(field=field):
                db = self.event_database()
                db["cases"][-1].pop(field)
                self.assert_error(db, field)
        db = self.event_database()
        db["cases"][-1]["verification"]["causal_confidence"] = "high"
        self.assert_error(db, "causal_confidence must be low")
        db = self.event_database()
        db["cases"][-1]["result_type"] = "reported_success"
        self.assert_error(db, "must use documented_event")

    def test_provenance_source_must_belong_to_case(self):
        db = self.event_database()
        db["cases"][-1]["provenance"]["source_id"] = "UNKNOWN"
        self.assert_error(db, "unknown reference")
        self.assert_error(db, "provenance source is absent")

    def test_event_key_is_unique_across_tiers(self):
        db = self.event_database()
        db["cases"][0]["event_key"] = db["cases"][-1]["event_key"]
        self.assert_error(db, "duplicate event_key")

    def test_claim_ids_are_optional_unique_and_well_formed(self):
        db = self.event_database()
        db["cases"][-1]["claims"][1]["claim_id"] = "C9000.001"
        self.assert_error(db, "duplicate claim_id")
        for value in ("", "has spaces", [], 4):
            db["cases"][-1]["claims"][0]["claim_id"] = value
            self.assert_error(db, "stable non-empty identifier")

        db = self.event_database()
        db["cases"][0]["claims"][0]["claim_id"] = "SHARED.01"
        db["cases"][-1]["claims"][0]["claim_id"] = "SHARED.01"
        self.assert_error(db, "global claim_id collision")

    def test_shards_load_and_duplicates_are_not_silently_dropped(self):
        db = self.event_database()
        with tempfile.TemporaryDirectory(prefix="civilization-catalog-") as task_dir:
            root = Path(task_dir)
            refs = root / "references"
            refs.mkdir()
            rows_by_file = {"models-01.json": db["models"][:50],
                            "models-02.json": db["models"][50:],
                            "sources-test.json": db["sources"],
                            "cases.json": db["cases"][:1], "cases-test.json": db["cases"][1:]}
            for name, rows in rows_by_file.items():
                (refs / name).write_text(json.dumps(rows), encoding="utf-8")
            loaded = catalog.load_database(root)
            self.assertEqual(len(loaded["cases"]), 2)
            self.assertEqual(catalog.check_database(loaded), [])
            manifest = {"schema_version": "2.0", "library_version": "2.0.0",
                        "checked_on": "2026-10-12", "counts": catalog.database_counts(loaded)}
            (refs / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(catalog.check_database(loaded, root), [])
            manifest["counts"]["cases"] = 999
            (refs / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertTrue(any("manifest: counts.cases" in error
                                for error in catalog.check_database(loaded, root)))
            (refs / "cases-duplicate.json").write_text(json.dumps(db["cases"][1:]), encoding="utf-8")
            loaded = catalog.load_database(root)
            self.assertEqual(len(loaded["cases"]), 3)
            self.assert_error(loaded, "duplicate IDs")
            self.assert_error(loaded, "duplicate event_key")

    def test_negative_transfer_and_limits_do_not_create_positive_matches(self):
        db = self.fixture_database()
        row = db["cases"][0]
        row["non_transfer_conditions"] = ["sentinel_negative_only"]
        row["verification"]["limitations"] = "sentinel_negative_only"
        row["model_mapping_note"] = "sentinel_negative_only"
        row["claims"][0]["causal_limit"] = "sentinel_negative_only"
        self.assertEqual(catalog.search_rows(db["cases"], "sentinel_negative_only", 8), [])
        row["facts"] = ["sentinel_positive_fact"]
        self.assertEqual(catalog.search_rows(db["cases"], "sentinel_positive_fact", 8)[0]["id"], "C001")

    def test_case_filters_and_evidence_summary(self):
        db = self.event_database()
        event = db["cases"][-1]
        mid = event["model_ids"][0]
        found = catalog.search_rows(db["cases"], "sentinel_positive_event", 8,
                                    case_record_type="evidence_event", model=mid,
                                    case_domain="testing_event")
        self.assertEqual([row["id"] for row in found], ["C9000"])
        row = found[0]
        self.assertEqual(row["record_type"], "evidence_event")
        self.assertEqual(row["causal_confidence"], "low")
        self.assertIn(mid, row["model_ids"])
        self.assertEqual(row["claim_count"], 2)
        self.assertTrue(row["checked_on"])
        self.assertTrue(row["limitation"])
        self.assertEqual(catalog.search_rows(db["cases"], "sentinel_positive_event", 8,
                                            case_record_type="deep_case"), [])
        self.assertEqual(catalog.search_rows(db["cases"], "sentinel_positive_event", 8,
                                            model="P001"), [])
        self.assertEqual(catalog.search_rows(db["cases"], "sentinel_positive_event", 8,
                                            case_domain="not_this_domain"), [])

    def test_manifest_versions_dates_and_counts(self):
        db = self.event_database()
        manifest = {"schema_version": "2.0", "library_version": "2.0.0",
                    "checked_on": "2026-10-12", "counts": catalog.database_counts(db)}
        self.assertEqual(catalog.check_manifest(manifest, db), [])
        for key, value, phrase in (("schema_version", "unsupported", "schema_version"),
                                   ("library_version", [], "library_version"),
                                   ("checked_on", "2026-02-30", "checked_on")):
            broken = copy.deepcopy(manifest)
            broken[key] = value
            self.assertTrue(any(phrase in error for error in catalog.check_manifest(broken, db)))
        manifest["counts"]["cases"] = 999
        self.assertTrue(any("counts.cases" in error for error in catalog.check_manifest(manifest, db)))
        manifest["counts"]["models"] = True
        self.assertTrue(any("counts.models" in error for error in catalog.check_manifest(manifest, db)))

    def test_stats_separate_events_and_origin_groups(self):
        db = self.event_database()
        stats = catalog.database_stats(db)
        self.assertEqual(stats["deep_cases"], 1)
        self.assertEqual(stats["evidence_events"], 1)
        self.assertEqual(stats["claims"], 4)
        self.assertEqual(stats["case_source_origin_groups"], 1)
        self.assertEqual(stats["model_coverage"]["mapped_models"], 4)
        self.assertIn("独立实验", stats["note"])

    def test_bad_json_shape_fails_read(self):
        with tempfile.TemporaryDirectory(prefix="civilization-catalog-") as task_dir:
            path = Path(task_dir) / "bad.json"
            path.write_text('{"not": "an array"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                catalog.read_rows(path)

    def test_malformed_url_reports_validation_error(self):
        db = self.fixture_database()
        db["sources"][0]["url"] = "https://[malformed"
        self.assert_error(db, "URL must be absolute")

    def test_render_preserves_urls_and_math(self):
        text = "AI模型:复利100次 -- 查看 https://example.com/a?q=1 与 `P(A|B)`"
        rendered = catalog.render_text(text)
        self.assertIn("AI 模型：复利 100 次", rendered)
        self.assertIn("https://example.com/a?q=1", rendered)
        self.assertIn("`P(A|B)`", rendered)
        self.assertEqual(catalog.render_text("中文—英文"), "中文--英文")

    def test_cli_success_and_failure_paths(self):
        commands = [
            (["show", "P058"], 0),
            (["show", "C001", "--format", "md"], 0),
            (["show", "P999"], 2),
            (["search", "  "], 2),
            (["search", "风险", "--limit", "0"], 2),
            (["search", "部署", "--cases", "--domain", "business"], 2),
            (["search", "风险", "--model", "P094"], 2),
            (["search", "风险", "--cases", "--model", "P999"], 2),
            (["search", "部署", "--cases", "--record-type", "deep_case",
              "--model", "p094", "--case-domain", "technology"], 0),
            (["stats"], 0),
            (["validate"], 0),
        ]
        for args, expected in commands:
            with self.subTest(args=args):
                done = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), *args],
                                      text=True, encoding="utf-8", capture_output=True)
                self.assertEqual(done.returncode, expected, done.stderr + done.stdout)
                self.assertNotIn("Traceback", done.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)

