"""Model operations, legacy compatibility and recommendation-boundary regressions."""
import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/civilization-os"
SCRIPT = SKILL / "scripts/catalog.py"
spec = importlib.util.spec_from_file_location("model_operations_test", SCRIPT)
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


def example_app():
    return {"status": "decision_support", "question": "fixture operation",
            "steps": [{"input": "known options", "action": "compare", "output": "tradeoffs"},
                      {"input": "tradeoffs", "action": "review constraints", "output": "next action"}],
            "example": {"type": "teaching_example", "context": "fictional choices",
                        "walkthrough": ["state conditions", "compare"], "takeaway": "conditional result"},
            "counterexample": {"context": "different conditions", "why_it_fails": "no support",
                               "better_approach": "check original assumptions"},
            "stop_conditions": ["missing decisive input"]}


class ModelOperationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = catalog.load_database(SKILL)

    def model(self):
        row = copy.deepcopy(self.db["models"][0])
        row["application"] = example_app()
        return row

    def test_library_operational_coverage_does_not_add_historical_cases(self):
        counts = catalog.database_counts(self.db)
        self.assertEqual(counts["model_applications"], 100)
        self.assertEqual(counts["model_teaching_examples"], 100)
        self.assertEqual(counts["model_counterexamples"], 100)
        self.assertEqual(counts["cases"], 1000)
        for row in self.db["models"]:
            self.assertEqual(catalog.check_model_application(row), [], row["id"])

    def test_optional_field_retains_legacy_model_validation(self):
        row = self.model(); del row["application"]
        self.assertEqual(catalog.check_model_application(row), [])
        db = copy.deepcopy(self.db)
        for model in db["models"]:
            model.pop("application", None)
        manifest = {"schema_version": "2.0", "library_version": "2.2.1",
                    "checked_on": "2026-10-12", "counts": catalog.database_counts(db)}
        for key in ("model_applications", "model_teaching_examples", "model_counterexamples"):
            manifest["counts"].pop(key)
        self.assertEqual(catalog.check_manifest(manifest, db), [])

    def test_new_manifest_detects_all_operations_removed(self):
        db = copy.deepcopy(self.db)
        manifest = {"schema_version": "2.0", "library_version": "2.3.0",
                    "checked_on": "2026-10-12", "counts": catalog.database_counts(db)}
        for model in db["models"]:
            model.pop("application", None)
        self.assertTrue(any("model_applications" in x for x in catalog.check_manifest(manifest, db)))

    def test_malformed_application_and_status_report_without_crash(self):
        for value in (None, [], "bad"):
            row = self.model(); row["application"] = value
            self.assertTrue(catalog.check_model_application(row))
        for value in ([], "unknown", True):
            row = self.model(); row["application"]["status"] = value
            self.assertTrue(any("status" in x for x in catalog.check_model_application(row)))

    def test_step_requires_input_action_and_output(self):
        row = self.model(); del row["application"]["steps"][0]["output"]
        self.assertTrue(any("output" in x for x in catalog.check_model_application(row)))
        for value in (None, [], ["bad"], [{"input": "x", "action": "y", "output": "z"}]):
            row = self.model(); row["application"]["steps"] = value
            self.assertTrue(catalog.check_model_application(row))
        row = self.model(); row["application"]["steps"][0] = None
        self.assertTrue(catalog.check_model_application(row))

    def test_teaching_example_cannot_claim_historical_identity(self):
        row = self.model(); row["application"]["example"]["type"] = "deep_case"
        self.assertTrue(any("teaching_example" in x for x in catalog.check_model_application(row)))
        row = self.model(); row["application"]["example"]["walkthrough"] = []
        self.assertTrue(catalog.check_model_application(row))

    def test_missing_counterexample_or_stop_conditions_rejected(self):
        for field, value in (("counterexample", None), ("stop_conditions", [])):
            row = self.model(); row["application"][field] = value
            self.assertTrue(catalog.check_model_application(row))
        row = self.model(); row["application"]["counterexample"]["better_approach"] = " "
        self.assertTrue(catalog.check_model_application(row))

    def test_positive_operation_question_and_teaching_context_are_searchable(self):
        row = self.model(); row["application"]["question"] = "op_question_positive_4851"
        self.assertEqual(catalog.search_rows([row], "op_question_positive_4851", 8)[0]["id"], row["id"])
        row["application"]["example"]["context"] = "op_context_positive_4851"
        hit = catalog.search_rows([row], "op_context_positive_4851", 8)[0]
        self.assertEqual(hit["application_status"], "decision_support")

    def test_operation_steps_and_example_walkthrough_are_searchable(self):
        for section, key in (("steps", "input"), ("steps", "action"), ("steps", "output"),
                             ("example", "walkthrough"), ("example", "takeaway")):
            row = self.model(); word = "op_deep_positive_9472"
            if section == "steps":
                row["application"]["steps"][0][key] = word
            else:
                row["application"]["example"][key] = [word] if key == "walkthrough" else word
            self.assertTrue(catalog.search_rows([row], word, 8), (section, key))

    def test_counterexample_and_stop_words_do_not_recommend_model(self):
        row = self.model(); word = "op_negative_only_4851"
        for field in ("context", "why_it_fails", "better_approach"):
            row["application"]["counterexample"][field] = word
        row["application"]["stop_conditions"] = [word]
        self.assertEqual(catalog.search_rows([row], word, 8), [])

    def test_filter_distinguishes_decision_and_learning_operations(self):
        row = self.model(); query = row["name"]
        self.assertTrue(catalog.search_rows([row], query, 8, model_application="decision_support"))
        self.assertEqual(catalog.search_rows([row], query, 8, model_application="learning_only"), [])

    def test_cli_model_filter_and_research_case_separation(self):
        for args, code in ((["search", "量子", "--model-application", "learning_only"], 0),
                           (["search", "选择", "--cases", "--model-application", "decision_support"], 2),
                           (["search", "前景", "--research", "--model-application", "decision_support"], 2)):
            run = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SCRIPT), *args],
                                 capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(run.returncode, code, (args, run.stderr))

    def test_show_returns_operations_with_existing_identity(self):
        run = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SCRIPT), "show", "P058"],
                             capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(run.returncode, 0, run.stderr)
        row = json.loads(run.stdout)
        self.assertEqual(row["id"], "P058")
        self.assertEqual(row["application"]["example"]["type"], "teaching_example")


if __name__ == "__main__":
    unittest.main()
