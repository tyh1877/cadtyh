"""C2 protocol/frozen-C1 isolation checks, with no GT/holdout case reads."""

import unittest

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try5A.scripts.kinematics import parse


class C2ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=load(HERE/"protocol/try6_0_c2.json")
        cls.c1=HERE/"results/try6_0_c1_v2"

    def test_no_new_vlm_or_pocket(self):
        self.assertIs(self.cfg["no_new_vlm_call"],True)
        slot=load(self.c1/"slot/validated_slots.json")
        self.assertEqual(next(x["status"] for x in slot["slots"] if x["slot_id"]=="visible_pocket"),"ABSENT")

    def test_visual_objective_identity(self):
        parity=load(self.c1/"solver/objective_definition.json")
        self.assertEqual(parity["weights"],{"visible_contour_distance":0.5,"visible_profile_width":0.5})
        self.assertEqual(parity["gt_terms"],0)
        self.assertEqual(parity["mechanical_terms"],0)

    def test_same_proposal_budget(self):
        c1=load(self.c1/"solver/config.json")
        self.assertEqual(self.cfg["c2_max_proposals_if_active"],c1["max_candidate_evaluations"])
        self.assertEqual(self.cfg["c1_replay_candidate_count"],32)

    def test_urdf_relative_scope(self):
        _,joints=parse(ROOT/self.cfg["sanitized_urdf"])
        by={x["joint_id"]:x for x in joints}
        self.assertEqual((by["J03"]["parent"],by["J03"]["child"]),("L03","L04"))
        self.assertEqual((by["J05"]["parent"],by["J05"]["child"]),("L05","L06"))
        self.assertEqual({x["link_id"] for x in self.cfg["neighbor_scope"]},{"L03","L05","L06","L07"})

    def test_independent_design_sweep(self):
        sweep=self.cfg["construction_sweep"]
        self.assertEqual(sweep["J03"]["sample_count"],7)
        self.assertEqual(len(sweep["J05"]["angles_radians"]),4)
        self.assertIs(sweep["not_from_final_development_configs"],True)

    def test_zero_margin_and_predeclared_tolerance(self):
        self.assertEqual(self.cfg["engineering_clearance_margin_mm"],0.0)
        self.assertEqual(self.cfg["numerical_forbidden_volume_tolerance_mm3"],1e-6)
        self.assertIs(self.cfg["kfde_hard_feasibility"],True)
        self.assertIs(self.cfg["visual_loss_penalty_for_infeasible"],False)

    def test_c1_final_cad_hash_frozen(self):
        lock=load(ROOT/self.cfg["c1_final_lock"])
        for item in lock["final_cad_artifacts"].values():
            self.assertEqual(sha(ROOT/item["path"]),item["sha256"])

    def test_holdout_lock_closed(self):
        lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
        self.assertIs(lock["accessed"],False)
        self.assertEqual(lock["evaluation_count"],0)


if __name__=="__main__":unittest.main()
