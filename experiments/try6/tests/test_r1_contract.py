"""R1 local representation and authority tests; no model, GT, or holdout cases."""

import copy
import json
import unittest
from pathlib import Path

from experiments.try6.scripts.r1_contract import ROOT, HERE, SemanticError, assemble, audit_functional_authority, canonical, frozen_inputs, load, validate_kfdg, validate_registry, validate_vfp


def fixture(): return load(HERE / "fixtures/r1_valid_vfp.json")


class R1ContractTests(unittest.TestCase):
    def setUp(self): self.valid = fixture()
    def reject_vfp(self, change):
        item = copy.deepcopy(self.valid); change(item)
        with self.assertRaises(Exception): validate_vfp(item)

    def test_valid_vfp_schema_and_semantics(self): self.assertEqual(validate_vfp(self.valid), self.valid)
    def test_wrong_root(self):
        with self.assertRaises(Exception): validate_vfp([self.valid])
    def test_extra_functional_field_rejected(self): self.reject_vfp(lambda x: x.update(joint_axis=[0,1,0]))
    def test_role_vocabulary_rejected(self): self.reject_vfp(lambda x: x["visual_features"][1].update(parameter_roles=["recess_depth_mm"]))
    def test_duplicate_role_rejected(self): self.reject_vfp(lambda x: x["visual_features"][1].update(parameter_roles=["length","length","depth"]))
    def test_signature_rejected(self): self.reject_vfp(lambda x: x["visual_features"][1].update(parameter_roles=["width","depth"]))
    def test_missing_feature_rejected(self): self.reject_vfp(lambda x: x["visual_features"].pop())
    def test_duplicate_feature_rejected(self): self.reject_vfp(lambda x: x["visual_features"].append(copy.deepcopy(x["visual_features"][0])))
    def test_unsupported_hidden_feature_rejected(self): self.reject_vfp(lambda x: x["visual_features"][1].update(local_name="hidden_bearing_seat"))
    def test_self_relation_rejected(self): self.reject_vfp(lambda x: x["visual_features"][1].update(relations=[{"type":"cuts_into","target_feature_type":"pocket"}]))
    def test_registry_valid(self): self.assertEqual(validate_registry()["active_parameter_count"], 8)
    def test_registry_duplicate_owner_role_rejected(self):
        _, registry, rules = frozen_inputs(); registry = copy.deepcopy(registry)
        registry["parameters"][1]["semantic_role"] = "width"
        with self.assertRaises(SemanticError): validate_registry(registry, rules)
    def test_registry_bounds_drift_rejected(self):
        _, registry, rules = frozen_inputs(); registry = copy.deepcopy(registry)
        registry["parameters"][0]["upper_bound"] = 100.0
        with self.assertRaises(SemanticError): validate_registry(registry, rules)
    def test_functional_authority_source(self): self.assertEqual(audit_functional_authority()["anchor_mm"], 63.0)
    def test_functional_authority_mutation_rejected(self):
        backbone, _, _ = frozen_inputs(); backbone = copy.deepcopy(backbone)
        backbone["functional_nodes"][0]["axis"] = [1.0,0.0,0.0]
        with self.assertRaises(SemanticError): audit_functional_authority(backbone)
    def test_deterministic_assembly(self): self.assertEqual(canonical(assemble(self.valid)), canonical(assemble(self.valid)))
    def test_proposal_to_kfdg_ownership(self):
        graph = assemble(self.valid)
        by_type = {f["type"]: f for f in graph["geometric_features"]}
        self.assertEqual(by_type["pocket"]["parameter_refs"], ["recess_length_mm","recess_depth_mm"])
        self.assertEqual(by_type["profile_transition"]["parameter_refs"], ["transition_length_mm","distal_width_mm","distal_height_mm"])
        self.assertEqual(graph["functional_nodes"], frozen_inputs()[0]["functional_nodes"])
        self.assertTrue(validate_kfdg(graph, self.valid))
    def test_duplicate_reference_rejected(self):
        graph = assemble(self.valid); graph["geometric_features"][1]["parameter_refs"].append("recess_length_mm")
        with self.assertRaises(Exception): validate_kfdg(graph)
    def test_dangling_reference_rejected(self):
        graph = assemble(self.valid); graph["geometric_features"][1]["parameter_refs"][0] = "missing"
        with self.assertRaises(Exception): validate_kfdg(graph)
    def test_wrong_parameter_owner_rejected(self):
        graph = assemble(self.valid); graph["parameters"][0]["owner_feature_id"] = "transition_01"
        with self.assertRaises(SemanticError): validate_kfdg(graph)
    def test_functional_override_rejected(self):
        graph = assemble(self.valid); graph["functional_nodes"][0]["axis"] = [1.0,0.0,0.0]
        with self.assertRaises(SemanticError): validate_kfdg(graph)
    def test_orphan_policy(self):
        graph = assemble(self.valid)
        dormant = next(p for p in graph["parameters"] if p["id"] == "fillet_radius_mm")
        self.assertTrue(dormant["allowed_orphan"])
        self.assertFalse(dormant["optimizable"])
    def test_holdout_lock_metadata(self):
        lock = load(ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
        self.assertIs(lock["accessed"], False)
        self.assertEqual(lock["evaluation_count"], 0)
        self.assertIs(lock["ordinary_runner_access"], False)


if __name__ == "__main__": unittest.main()
