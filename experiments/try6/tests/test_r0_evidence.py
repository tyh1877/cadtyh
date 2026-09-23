"""Post-run R0 evidence checks; never open GT or formal holdout cases."""

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try6"
RESULT = HERE / "results/try6_0_r0"
ARTIFACT = HERE / "artifacts/try6_0_r0"


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))


class R0EvidenceTests(unittest.TestCase):
    def test_schema_transport_wrapper_and_raw(self):
        report = load(RESULT / "schema_transport/transport_report.json")
        schemas = {v["level"]: v["schema"] for v in load(HERE / "protocol/r0_schema_levels.json")["levels"]}
        schemas[4] = load(HERE / "protocol/kfdg_v1.schema.json")
        self.assertTrue(report["all_pass"])
        for level in range(5):
            request = load(RESULT / f"schema_transport/level{level}_request.json")
            http = load(RESULT / f"schema_transport/level{level}_http_response.json")
            sdk = load(RESULT / f"schema_transport/level{level}_response.json")
            raw = (RESULT / f"schema_transport/level{level}_raw_response.txt").read_text(encoding="utf-8")
            self.assertEqual(request["response_format"]["json_schema"]["schema"], schemas[level])
            self.assertIs(request["response_format"]["json_schema"]["strict"], True)
            self.assertEqual(raw, http["choices"][0]["message"]["content"])
            self.assertEqual(raw, sdk["choices"][0]["message"]["content"])
            Draft202012Validator(schemas[level]).validate(json.loads(raw))

    def test_semantic_feature_selection_and_fillet_deferment(self):
        mapping = load(ARTIFACT / "parametric_rebuild/baseline/feature_mapping.json")
        flattened = [name for names in mapping["kfdg_to_cad"].values() for name in names]
        self.assertIn("MainHousingPad", flattened)
        self.assertIn("VisibleRecessPocket", flattened)
        self.assertIn("FrozenProximalBore", flattened)
        self.assertNotIn("VisibleEdgeFillet", flattened)
        self.assertIn("fillet", mapping["deferred_features"])

    def test_parameter_binding_changes_final_shape(self):
        report = load(RESULT / "parametric_rebuild/rebuild_report.json")
        baseline = report["baseline"]["builder_result"]["final_volume_mm3"]
        self.assertEqual({item["parameter"] for item in report["edits"]}, {"housing_width_mm", "housing_height_mm", "recess_depth_mm"})
        for item in report["edits"]:
            self.assertNotAlmostEqual(item["result"]["final_volume_mm3"], baseline, places=6)

    def test_feature_tree_recompute(self):
        report = load(RESULT / "parametric_rebuild/rebuild_report.json")
        self.assertEqual(len(report["edits"]), 3)
        for item in report["edits"]:
            self.assertTrue(item["result"]["cad_valid"])
            self.assertTrue(all(node["valid"] and node["error_state"] == "['Up-to-date']" for node in item["result"]["feature_tree"]))
            self.assertEqual(item["result"]["connected_solid_count"], 1)

    def test_interface_invariance(self):
        for item in load(RESULT / "parametric_rebuild/rebuild_report.json")["edits"]:
            result = item["result"]
            self.assertEqual(result["protected_shape_signatures_before"], result["protected_shape_signatures_after"])
            self.assertTrue(result["interface_invariant"])

    def test_export_and_reopen(self):
        for item in load(RESULT / "parametric_rebuild/rebuild_report.json")["edits"]:
            result = item["result"]
            self.assertTrue(result["export_success"] and result["reopen_valid"])
            folder = ARTIFACT / "parametric_rebuild" / f"edit_{item['id']}"
            self.assertTrue(all((folder / name).stat().st_size > 0 for name in ("edited.FCStd", "edited.step", "edited.stl")))

    def test_holdout_lock_metadata_remains_closed(self):
        lock = load(ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
        self.assertIs(lock["accessed"], False)
        self.assertEqual(lock["evaluation_count"], 0)
        self.assertIs(lock["ordinary_runner_access"], False)


if __name__ == "__main__": unittest.main()
