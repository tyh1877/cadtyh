"""Deterministic R0 contract checks; no CAD or GT reads."""

import copy
import json
import unittest
from pathlib import Path

from experiments.try6.scripts.kfdg_v1_contract import canonical, parse_raw, validate

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.full = fixture("kfdg_v1_valid_full.json")

    def reject(self, mutator):
        value = copy.deepcopy(self.full)
        mutator(value)
        with self.assertRaises((ValueError, Exception)):
            validate(value)

    def test_valid_minimal(self): self.assertEqual(validate(fixture("kfdg_v1_valid_minimal.json"))["link_id"], "TEST")
    def test_valid_full(self): self.assertEqual(validate(self.full), self.full)
    def test_missing_required(self): self.reject(lambda v: v.pop("constraints"))
    def test_wrong_root_type(self):
        with self.assertRaises(Exception): validate([self.full])
    def test_unknown_field(self): self.reject(lambda v: v.update(unexpected=1))
    def test_wrong_enum(self): self.reject(lambda v: v["parameters"][0].update(provenance="MANUFACTURING_RULE"))
    def test_wrong_parameter_type(self): self.reject(lambda v: v["parameters"][0].update(value="40"))
    def test_invalid_unit(self): self.reject(lambda v: v["parameters"][0].update(unit="inch"))
    def test_duplicate_id(self): self.reject(lambda v: v["parameters"][0].update(id="port_01"))
    def test_dangling_parameter_reference(self): self.reject(lambda v: v["geometric_features"][0].update(parameter_refs=["missing"]))
    def test_round_trip_serialization(self): self.assertEqual(json.loads(canonical(self.full)), self.full)
    def test_parse_serialize_parse_equality(self): self.assertEqual(parse_raw(canonical(parse_raw(canonical(self.full)))), self.full)


if __name__ == "__main__": unittest.main()
