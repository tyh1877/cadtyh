"""Status-dependent closed-set contract and KFDG checks; no GT or holdout cases."""

import copy
import unittest

from jsonschema import Draft202012Validator

from experiments.try6.scripts.r1_contract import ROOT, HERE, canonical, load
from experiments.try6.scripts.r1_v2_projection import project
from experiments.try6.scripts.r1_v3_contract import assemble, registry, slot_schema, validate_kfdg, validate_slot_registry, validate_slots


def fixture(): return load(HERE/"fixtures/r1_v3_valid_slots.json")


class SlotContractTests(unittest.TestCase):
    def setUp(self): self.valid=fixture()
    def reject(self,change):
        value=copy.deepcopy(self.valid);change(value)
        with self.assertRaises(Exception): validate_slots(value)

    def test_valid_fixture(self): self.assertEqual(validate_slots(self.valid),self.valid)
    def test_missing_slot(self): self.reject(lambda x:x["slots"].pop())
    def test_unknown_slot(self): self.reject(lambda x:x["slots"][0].update(slot_id="unknown"))
    def test_duplicate_slot_id(self): self.reject(lambda x:x["slots"][1].update(slot_id="main_housing"))
    def test_invalid_status_enum(self): self.reject(lambda x:x["slots"][1].update(status="MAYBE"))
    def test_invalid_confidence_enum(self): self.reject(lambda x:x["slots"][1].update(confidence="VERY_HIGH"))
    def test_present_evidence_required(self): self.reject(lambda x:x["slots"][0].update(evidence_views=[]))
    def test_uncertain_evidence_required(self): self.reject(lambda x:x["slots"][1].update(evidence_views=[]))
    def test_absent_empty_evidence_allowed(self):
        self.valid["slots"][1].update(status="ABSENT",evidence_views=[])
        self.assertEqual(validate_slots(self.valid)["slots"][1]["status"],"ABSENT")
    def test_duplicate_evidence_rejected(self): self.reject(lambda x:x["slots"][0].update(evidence_views=["front","front"]))
    def test_vlm_role_field_rejected(self): self.reject(lambda x:x["slots"][0].update(parameter_roles=["width"]))
    def test_vlm_relation_field_rejected(self): self.reject(lambda x:x["slots"][0].update(relations=[]))
    def test_slot_registry_owner_mapping(self): self.assertEqual(validate_slot_registry()["active_parameter_count"],8)
    def test_present_only_instantiation(self):
        graph=assemble(self.valid)
        self.assertEqual({f["id"] for f in graph["geometric_features"]},{"housing_01","transition_01"})
        self.assertEqual({x["slot_id"]:x["status"] for x in graph["slot_provenance"]}["visible_pocket"],"UNCERTAIN")
        self.assertTrue(validate_kfdg(graph,self.valid))
    def test_all_absent_valid_empty_graph(self):
        for slot in self.valid["slots"]: slot.update(status="ABSENT",evidence_views=[])
        graph=assemble(self.valid)
        self.assertEqual(graph["geometric_features"],[])
        self.assertEqual(graph["constraints"],[])
        self.assertTrue(all(not p["active"] for p in graph["parameters"]))
        self.assertTrue(validate_kfdg(graph,self.valid))
    def test_all_uncertain_non_instantiation(self):
        for slot in self.valid["slots"]: slot.update(status="UNCERTAIN",evidence_views=["front"])
        self.assertEqual(assemble(self.valid)["geometric_features"],[])
    def test_parameter_mapping(self):
        graph=assemble(self.valid)
        housing=next(f for f in graph["geometric_features"] if f["id"]=="housing_01")
        self.assertEqual(housing["parameter_refs"],["housing_width_mm","housing_height_mm","proximal_section_length_mm"])
        recess=next(p for p in graph["parameters"] if p["id"]=="recess_depth_mm")
        self.assertFalse(recess["active"])
        self.assertTrue(recess["allowed_orphan"])
    def test_relations_deterministic(self):
        graph=assemble(self.valid)
        self.assertEqual([r["type"] for r in graph["constraints"]],["interface_fixed","profile_continuity","connected_to"])
    def test_assembly_deterministic(self): self.assertEqual(canonical(assemble(self.valid)),canonical(assemble(self.valid)))
    def test_absent_feature_injection_rejected(self):
        graph=assemble(self.valid)
        graph["geometric_features"].append({"id":"recess_01","type":"pocket","parameter_refs":["recess_length_mm","recess_depth_mm"],"source_slot_id":"visible_pocket","evidence_views":["left"],"confidence":"MEDIUM"})
        with self.assertRaises(Exception): validate_kfdg(graph,self.valid)
    def test_dangling_ref_rejected(self):
        graph=assemble(self.valid);graph["geometric_features"][0]["parameter_refs"][0]="missing"
        with self.assertRaises(Exception): validate_kfdg(graph,self.valid)
    def test_duplicate_ref_rejected(self):
        graph=assemble(self.valid);graph["geometric_features"][0]["parameter_refs"].append("housing_width_mm")
        with self.assertRaises(Exception): validate_kfdg(graph,self.valid)
    def test_functional_authority_rejected(self):
        graph=assemble(self.valid);graph["functional_nodes"][0]["axis"]=[1,0,0]
        with self.assertRaises(Exception): validate_kfdg(graph,self.valid)
    def test_canonical_to_api_projection_only_uniqueitems(self):
        canonical_schema=slot_schema();rules=load(HERE/"protocol/r1_v3_projection_rules.json")
        api,removed=project(canonical_schema,rules)
        self.assertEqual(len(removed),1)
        self.assertEqual(removed[0]["keyword"],"uniqueItems")
        item=copy.deepcopy(self.valid);item["slots"][0]["evidence_views"]=["front","front"]
        Draft202012Validator(api).validate(item)
        with self.assertRaises(Exception): validate_slots(item)
    def test_no_repair_duplicate_slot(self):
        item=copy.deepcopy(self.valid);item["slots"][1]["slot_id"]="main_housing"
        original=copy.deepcopy(item)
        with self.assertRaises(Exception): assemble(item)
        self.assertEqual(item,original)
    def test_holdout_lock_metadata(self):
        lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
        self.assertIs(lock["accessed"],False)
        self.assertEqual(lock["evaluation_count"],0)


if __name__=="__main__": unittest.main()
