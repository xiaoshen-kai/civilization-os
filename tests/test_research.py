"""Research-card traceability, transfer boundaries and CLI regressions."""
import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "civilization-os"
SCRIPT = SKILL / "scripts" / "catalog.py"
spec = importlib.util.spec_from_file_location("research_catalog_test", SCRIPT)
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


class ResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = catalog.load_database(SKILL)
        cls.rows = cls.db["research"]
        cls.models = {x["id"] for x in cls.db["models"]}

    def checked(self, rows):
        return catalog.check_research(rows, self.models, {"P001", "C001", "S001"})

    def test_actual_cards_are_distinct_and_traceable(self):
        self.assertEqual({x["id"] for x in self.rows}, {f"A{i:03d}" for i in range(1, 17)})
        self.assertEqual(self.checked(self.rows), [])
        self.assertEqual(len(self.db["models"]), 100)
        self.assertEqual(len(self.db["cases"]), 1000)
        counts = catalog.database_counts(self.db)
        self.assertEqual(counts["research_cards"], 16)
        self.assertGreaterEqual(counts["research_sources"], 32)

    def test_mathematical_learning_does_not_become_direct_advice(self):
        fields = [x for x in self.rows if x["id"] in {"A013", "A014", "A015", "A016"}]
        self.assertEqual(len(fields), 4)
        self.assertTrue(all(x["decision_application"]["status"] == "learning_only" for x in fields))

    def test_unknown_and_outside_claim_sources_rejected(self):
        row = copy.deepcopy(self.rows[0])
        row["claims"][0]["source_ids"] = [self.rows[1]["sources"][0]["id"]]
        self.assertTrue(any("not card-local" in x for x in self.checked([row])))

    def test_invalid_model_and_duplicate_card_rejected(self):
        row = copy.deepcopy(self.rows[0])
        row["model_ids"] = ["P999"]
        self.assertTrue(any("unknown model" in x for x in self.checked([row])))
        self.assertTrue(any("duplicate research ID" in x for x in self.checked([row, row])))

    def test_unchecked_and_invalid_dates_rejected(self):
        row = copy.deepcopy(self.rows[0])
        row["verification"]["status"] = "candidate"
        row["sources"][0]["checked_on"] = "2026-02-30"
        self.assertTrue(any("unchecked research" in x for x in self.checked([row])))
        self.assertTrue(any("invalid checked_on" in x for x in self.checked([row])))

    def test_missing_primary_reading_rejected(self):
        row = copy.deepcopy(self.rows[0])
        for source in row["sources"]:
            source["source_type"] = "official_summary"
        self.assertTrue(any("primary research reading required" in x for x in self.checked([row])))

    def test_missing_reading_scope_and_unused_source_rejected(self):
        row = copy.deepcopy(self.rows[0])
        row["sources"][0]["reading_scope"] = ""
        self.assertTrue(any("reading_scope" in x for x in self.checked([row])))
        sid = row["sources"][0]["id"]
        for claim in row["claims"]:
            claim["source_ids"] = [x for x in claim["source_ids"] if x != sid]
        self.assertTrue(any("unused research source" in x for x in self.checked([row])))

    def test_malformed_objects_and_enums_rejected(self):
        row = copy.deepcopy(self.rows[0])
        row["decision_application"] = []
        row["award"]["year"] = True
        row["research"]["evidence_type"] = []
        self.assertTrue(self.checked([row]))
        self.assertTrue(self.checked([None]))

    def test_missing_source_and_claim_arrays_are_reported_without_crash(self):
        for field in ("sources", "claims"):
            db = copy.deepcopy(self.db)
            db["research"][0].pop(field)
            self.assertTrue(catalog.check_database(db, SKILL))
            catalog.database_counts(db)

    def test_legacy_manifest_without_research_counters(self):
        db = copy.deepcopy(self.db)
        db.pop("research")
        counts = catalog.database_counts(db)
        self.assertNotIn("research_cards", counts)
        manifest = {"schema_version": "2.0", "library_version": "2.1.1",
                    "checked_on": "2026-10-12", "counts": counts}
        self.assertEqual(catalog.check_manifest(manifest, db), [])
        db["research"] = []
        self.assertEqual(catalog.check_manifest(manifest, db), [])

    def test_malformed_host_and_userinfo_urls_rejected(self):
        for url in ("https://user@", "https://:443", "https://host name/path",
                    "https://user:secret@example.org", "https://example.org:bad"):
            row = copy.deepcopy(self.rows[0])
            row["sources"][0]["url"] = url
            self.assertTrue(any("invalid absolute URL" in x for x in self.checked([row])))

    def test_invalid_urls_and_claim_identity_rejected(self):
        row = copy.deepcopy(self.rows[0])
        row["sources"][0]["url"] = "https://[invalid"
        row["claims"][1]["id"] = row["claims"][0]["id"]
        errors = self.checked([row])
        self.assertTrue(any("invalid absolute URL" in x for x in errors))
        self.assertTrue(any("collision claim ID" in x for x in errors))

    def test_negative_transfer_does_not_create_search_match(self):
        row = copy.deepcopy(self.rows[0])
        row["misuse"].append("sentinel_bad_application_881")
        row["research"]["limitations"].append("sentinel_bad_application_881")
        row["decision_application"]["stop_conditions"].append("sentinel_bad_application_881")
        self.assertEqual(catalog.search_research([row], "sentinel_bad_application_881", 8), [])
        row["research"]["principle"] += " sentinel_positive_881"
        self.assertEqual(catalog.search_research([row], "sentinel_positive_881", 8)[0]["id"], row["id"])

    def test_search_status_and_model_filters(self):
        found = catalog.search_research(self.rows, "菲尔兹", 100, "learning_only")
        self.assertEqual({x["id"] for x in found}, {"A013", "A014", "A015", "A016"})
        self.assertTrue(all(x["application_status"] == "learning_only" for x in found))
        self.assertTrue(catalog.search_research(self.rows, "前景", 8, model="P039"))
        self.assertEqual(catalog.search_research(self.rows, "missing_sentinel_999", 8), [])

    def test_chinese_laureate_names_find_research(self):
        for name, expected in (("陶哲轩", "A014"), ("米尔扎哈尼", "A015"),
                               ("卡尼曼", "A001"), ("奥斯特罗姆", "A004")):
            found = catalog.search_research(self.rows, name, 8)
            self.assertTrue(any(x["id"] == expected for x in found), name)

    def test_empty_query_and_limit_bounds(self):
        for query, limit in [(" ", 8), ("选择", 0), ("选择", 101), ("选择", True)]:
            with self.assertRaises(ValueError):
                catalog.search_research(self.rows, query, limit)

    def test_cli_research_show_and_sources_from_other_cwd(self):
        for args in [["search", "心理账户", "--research"], ["show", "A002"],
                     ["show", self.rows[0]["sources"][0]["id"]], ["stats"], ["validate"]]:
            done = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SCRIPT), *args],
                                  cwd=ROOT.parent, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(done.returncode, 0, done.stderr + done.stdout)
            json.loads(done.stdout)

    def test_model_discovery_exposes_related_research(self):
        done = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SCRIPT),
                               "search", "前景"], cwd=ROOT.parent, capture_output=True,
                              text=True, encoding="utf-8")
        self.assertEqual(done.returncode, 0, done.stderr)
        found = json.loads(done.stdout)["results"]
        prospect = next(row for row in found if row["id"] == "P039")
        self.assertIn("A001", prospect["research_card_ids"])

    def test_cli_conflicting_filters_fail(self):
        for args in [["--cases", "--research"], ["--application", "direct"],
                     ["--research", "--kind", "theorem"], ["--research", "--model", "P999"]]:
            done = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SCRIPT),
                                   "search", "选择", *args], cwd=ROOT.parent,
                                  capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(done.returncode, 2, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
