from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

from jsonschema import ValidationError

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))
from kfdg_contract import build_kfdg, canonical, load, validate_kfdg, validate_vlm  # noqa: E402


class KFDGContractTests(unittest.TestCase):
    def setUp(self):
        self.valid = load(HERE / "tests/fixtures/valid_vlm.json")
        self.params = load(HERE / "protocol/parameter_bounds.json")

    def test_round_trip_and_four_node_types(self):
        graph = build_kfdg(self.valid, self.params)
        self.assertTrue(validate_kfdg(json.loads(canonical(graph))))
        self.assertEqual(len(graph["parameter_nodes"]), 9)
        self.assertEqual(graph["metric_anchor"]["distance_mm"], 63.0)

    def test_invalid_fixture_rejects_ambiguous_feature_value(self):
        bad = copy.deepcopy(self.valid)
        bad["geometric_features"][2]["type"] = {"pocket": True}
        with self.assertRaises(ValidationError): validate_vlm(bad)

    def test_unknown_field_rejected(self):
        bad = copy.deepcopy(self.valid); bad["old_body_family"] = "wrist_block"
        with self.assertRaises(ValidationError): validate_vlm(bad)

    def test_missing_required_field_rejected(self):
        bad = copy.deepcopy(self.valid); del bad["relations"]
        with self.assertRaises(ValidationError): validate_vlm(bad)

    def test_unit_handling_rejects_inches(self):
        graph = build_kfdg(self.valid, self.params); graph["parameter_nodes"][0]["unit"] = "in"
        with self.assertRaises(ValidationError): validate_kfdg(graph)

    def test_relation_reference_rejected(self):
        bad = copy.deepcopy(self.valid); bad["relations"][0]["source"] = "unknown_part"
        with self.assertRaises(ValueError): validate_vlm(bad)


if __name__ == "__main__": unittest.main()
