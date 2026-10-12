"""Offline regressions for the 900 cached evidence-event records."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "civilization-os"
SCRIPT = SKILL / "scripts" / "verify_events.py"
spec = importlib.util.spec_from_file_location("civilization_event_verifier", SCRIPT)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)
TEMP_PARENT = ROOT / ".tmp" / "event-tests"


class EventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        refs = SKILL / "references"
        paths = list(refs.glob("cases*.json")) + list((refs / "event-data").glob("*.json"))
        cls.payloads = {path.relative_to(SKILL): path.read_bytes() for path in paths}

    def setUp(self):
        TEMP_PARENT.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="events-", dir=TEMP_PARENT)
        self.workspace = Path(self.temporary.name).resolve()
        self.assertEqual(self.workspace.parent, TEMP_PARENT.resolve())
        self.addCleanup(self.cleanup_workspace)
        self.skill = self.workspace / "skill"
        for relative, payload in self.payloads.items():
            path = self.skill / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)

    def cleanup_workspace(self):
        resolved = self.workspace.resolve()
        if resolved.parent != TEMP_PARENT.resolve() or not resolved.name.startswith("events-"):
            raise AssertionError("Refusing cleanup outside this test's temporary child")
        self.temporary.cleanup()

    def path(self, dataset, snapshot=False):
        refs = self.skill / "references"
        return refs / "event-data" / (dataset + ".json") if snapshot else refs / f"cases-events-{dataset}.json"

    def change(self, dataset, mutation, snapshot=False):
        path = self.path(dataset, snapshot)
        value = json.loads(path.read_text(encoding="utf-8"))
        mutation(value)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def assert_failure(self, phrase):
        result = verifier.verify_events(self.skill)
        self.assertFalse(result["valid"])
        self.assertGreater(result["error_count"], 0)
        self.assertTrue(any(phrase in error for error in result["errors"]), result["errors"])
        return result

    def test_actual_full_event_library(self):
        result = verifier.verify_events(SKILL)
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["events"], 900)
        self.assertEqual({key: value["derived_cases"] for key, value in result["datasets"].items()},
                         {"fdic": 300, "cfpb": 200, "clinical": 250, "nobel": 150})
        self.assertIn("不证明快照来自官方", result["note"])
        self.assertIn("医疗结论", result["note"])

    def test_facts_numbers_dates_urls_models_and_metadata_cannot_drift(self):
        operations = (
            ("fdic", lambda rows: rows[0]["facts"].__setitem__(1, "错误金额为 0。"), "facts[1]"),
            ("fdic", lambda rows: rows[0].__setitem__("event_time", "2000-01-01"), "event_time"),
            ("cfpb", lambda rows: rows[0]["provenance"].__setitem__("record_url", "https://example.com/wrong"), "record_url"),
            ("clinical", lambda rows: rows[0]["claims"][0].__setitem__("claim", "已证明疗效。"), "claims[0].claim"),
            ("nobel", lambda rows: rows[0].__setitem__("model_ids", ["P001"]), "model_ids[0]"),
            ("clinical", lambda rows: rows[0]["verification"].__setitem__("fact_confidence", "high"), "fact_confidence"),
        )
        for dataset, operation, phrase in operations:
            with self.subTest(dataset=dataset, phrase=phrase):
                original = self.path(dataset).read_bytes()
                self.change(dataset, operation)
                self.assert_failure(phrase)
                self.path(dataset).write_bytes(original)

    def test_snapshot_hash_and_source_mapping_cannot_drift(self):
        self.change("fdic", lambda rows: rows[0]["provenance"].__setitem__("snapshot_sha256", "0" * 64))
        self.assert_failure("snapshot_sha256")
        self.path("fdic").write_bytes(self.payloads[Path("references/cases-events-fdic.json")])
        self.change("nobel", lambda snapshot: snapshot.__setitem__("source_id", "WRONG"), snapshot=True)
        self.assert_failure("dataset/source mapping")

    def test_snapshot_numeric_change_is_detected(self):
        self.change("fdic", lambda snapshot: snapshot["records"][0]["fields"].__setitem__("QBFASSET", 0), snapshot=True)
        self.assert_failure("derived content differs")

    def test_duplicate_record_key_and_fixed_id_order_are_rejected(self):
        original = self.path("fdic", True).read_bytes()
        self.change("fdic", lambda snapshot: snapshot["records"][1].__setitem__(
            "record_key", snapshot["records"][0]["record_key"]), snapshot=True)
        self.assert_failure("duplicate record_key")
        self.path("fdic", True).write_bytes(original)
        self.change("clinical", lambda rows: rows[1].__setitem__("id", rows[0]["id"]))
        self.assert_failure("fixed ID range/order")

    def test_fdic_semantics_cannot_be_upgraded_or_rekeyed(self):
        original = self.path("fdic", True).read_bytes()
        operations = (
            (lambda snapshot: snapshot["records"][0]["fields"].__setitem__("RESTYPE", "ASSISTANCE"), "RESTYPE"),
            (lambda snapshot: snapshot["records"][0]["fields"].__setitem__("FAILDATE", "2026-01-01"), "FAILDATE"),
            (lambda snapshot: snapshot["records"][0]["fields"].__setitem__("QBFDEP", "1000"), "finite number or null"),
        )
        for operation, phrase in operations:
            with self.subTest(phrase=phrase):
                self.change("fdic", operation, snapshot=True)
                self.assert_failure(phrase)
                self.path("fdic", True).write_bytes(original)
        def same_episode(snapshot):
            left, right = snapshot["records"][:2]
            for key in ("NAME", "FAILDATE", "FAILYR", "CERT"):
                right["fields"][key] = left["fields"][key]
        self.change("fdic", same_episode, snapshot=True)
        self.assert_failure("duplicate canonical NAME + FAILDATE")

    def test_clinical_keeps_selection_group_units_and_denominators(self):
        original = self.path("clinical", True).read_bytes()
        operations = (
            (lambda snapshot: snapshot["records"][0]["fields"].__setitem__("allocation", "NON_RANDOMIZED"), "RANDOMIZED"),
            (lambda snapshot: snapshot["records"][0]["fields"].__setitem__("overall_status", "RECRUITING"), "COMPLETED"),
            (lambda snapshot: snapshot["records"][0]["fields"]["results_first_post_date_struct"].__setitem__("date", "2026-01-01"), "cutoff"),
            (lambda snapshot: snapshot["records"][0]["fields"]["measurements"][0].__setitem__("groupId", "MISSING"), "groupId"),
            (lambda snapshot: snapshot["records"][0]["fields"].__setitem__("unit_of_measure", ""), "unit_of_measure"),
            (lambda snapshot: snapshot["records"][0]["fields"].__setitem__("denoms", []), "denoms"),
            (lambda snapshot: snapshot["records"][0]["fields"].__setitem__("dispersion_type", []), "dispersion_type"),
            (lambda snapshot: snapshot["records"][0]["fields"].__setitem__("type_units_analyzed", []), "type_units_analyzed"),
            (lambda snapshot: snapshot["records"][0]["fields"].__setitem__("denom_units_selected", []), "denom_units_selected"),
        )
        for operation, phrase in operations:
            with self.subTest(phrase=phrase):
                self.change("clinical", operation, snapshot=True)
                self.assert_failure(phrase)
                self.path("clinical", True).write_bytes(original)

    def test_estimated_date_cannot_be_presented_as_actual(self):
        snapshot = json.loads(self.path("clinical", True).read_text(encoding="utf-8"))
        index = next(index for index, row in enumerate(snapshot["records"])
                     if row["fields"]["results_first_post_date_struct"]["type"] == "ESTIMATED")
        self.change("clinical", lambda rows: rows[index]["facts"].__setitem__(
            0, rows[index]["facts"][0].replace("ESTIMATED", "ACTUAL")))
        self.assert_failure("facts[0]")

    def test_cfpb_duplicates_deep_and_related_goldman_are_rejected(self):
        original = self.path("cfpb", True).read_bytes()
        business = json.loads((self.skill / "references" / "cases-business-deep.json").read_text(encoding="utf-8"))
        deep_url = business[0]["event_key"][len("cfpb:"):]
        for url in (deep_url, next(iter(verifier.RELATED_CFPB_URLS)) + "/"):
            with self.subTest(url_type="related" if "goldman" in url else "deep"):
                def mutation(snapshot):
                    record = snapshot["records"][0]
                    record["record_key"] = url.rstrip("/")
                    record["record_url"] = url
                    record["fields"]["url"] = url
                self.change("cfpb", mutation, snapshot=True)
                self.assert_failure("deep or related Goldman")
                self.path("cfpb", True).write_bytes(original)

    def test_cross_deep_event_episode_collision_is_rejected(self):
        path = self.skill / "references" / "cases.json"
        deep = json.loads(path.read_text(encoding="utf-8"))
        events = json.loads(self.path("fdic").read_text(encoding="utf-8"))
        deep[0]["event_key"] = events[0]["event_key"]
        path.write_text(json.dumps(deep, ensure_ascii=False), encoding="utf-8")
        self.assert_failure("already a deep case")

    def test_nobel_all_laureates_category_counts_and_delayed_awards(self):
        snapshot = json.loads(self.path("nobel", True).read_text(encoding="utf-8"))
        self.assertTrue(any(row["fields"]["date_awarded"][:4] != row["fields"]["award_year"]
                            for row in snapshot["records"]))
        self.assertTrue(verifier.verify_events(self.skill)["valid"])
        index = next(index for index, row in enumerate(snapshot["records"])
                     if len(row["fields"]["laureates"]) > 1)
        original = self.path("nobel", True).read_bytes()
        self.change("nobel", lambda value: value["records"][index]["fields"]["laureates"].pop(), snapshot=True)
        self.assert_failure("portions must sum to one")
        self.path("nobel", True).write_bytes(original)
        self.change("nobel", lambda value: value["records"][0]["fields"].__setitem__("category_code", "eco"), snapshot=True)
        self.assert_failure("category code")

    def test_path_escape_and_linked_snapshot_are_rejected(self):
        original = self.path("fdic").read_bytes()
        for value in ("../../outside.json", "event-data/../../outside.json", "/outside.json"):
            self.change("fdic", lambda rows: rows[0]["provenance"].__setitem__("snapshot_file", value))
            self.assert_failure("snapshot_file must exactly match")
            self.path("fdic").write_bytes(original)
        target = self.path("fdic", True).resolve()
        original_predicate = Path.is_symlink
        def linked(path):
            return path.resolve() == target or original_predicate(path)
        with mock.patch.object(Path, "is_symlink", linked):
            self.assert_failure("symbolic links")

    def test_missing_invalid_json_and_wrong_shapes_are_controlled_errors(self):
        original = self.path("cfpb").read_bytes()
        self.path("cfpb").unlink()
        self.assert_failure("cannot read JSON")
        self.path("cfpb").write_bytes(b"{invalid")
        self.assert_failure("JSONDecodeError")
        self.path("cfpb").write_text('[1,2,3]', encoding="utf-8")
        self.assert_failure("array of objects")
        self.path("cfpb").write_bytes(original)
        self.change("clinical", lambda value: value["records"][0].__setitem__("fields", []), snapshot=True)
        self.assert_failure("fields must be an object")

    def test_missing_renderer_is_a_controlled_error(self):
        with mock.patch.object(verifier, "RENDERER_PATH", self.workspace / "missing_renderer.py"):
            self.assert_failure("cannot load renderer")

    def test_cli_failure_returns_one_without_traceback(self):
        self.path("nobel", True).write_bytes(b"invalid-json")
        done = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SCRIPT),
                               "--root", str(self.skill)], capture_output=True,
                              text=True, encoding="utf-8")
        self.assertEqual(done.returncode, 1)
        self.assertNotIn("Traceback", done.stderr)
        result = json.loads(done.stdout)
        self.assertFalse(result["valid"])
        self.assertNotIn(str(self.workspace), done.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)

