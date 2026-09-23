"""Post-run C2 evidence checks for the frozen zero-feasible execution."""

import unittest

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha

RESULT=HERE/"results/try6_0_c2"


class C2NoFeasibleTests(unittest.TestCase):
    def test_c1_parity_and_zero_new_vlm(self):
        p=load(RESULT/"frozen_c1/parity_audit.json")
        self.assertEqual(p["status"],"PASS")
        self.assertIs(p["no_new_vlm_call"],True)
        self.assertEqual(p["only_method_increment"],"hard KFDE feasibility before visual ranking")

    def test_constructor_independent_gate(self):
        x=load(RESULT/"kfde/independent_construction_validation.json")
        self.assertEqual(x["status"],"PASS")
        self.assertEqual(x["component_count"],13)
        self.assertIs(x["pose_sensitive"],True)
        self.assertIs(x["keepout_nonempty"],True)

    def test_replay_full_denominator(self):
        x=load(RESULT/"replay/independent_activity_validation.json")
        self.assertEqual((x["requested"],x["validated"],x["infeasible_count"]),(32,32,32))
        self.assertIs(x["c1_selected_feasible"],False)

    def test_formal_search_all_hard_rejected(self):
        h=load(RESULT/"solver/candidate_history.json")
        self.assertEqual((h["actual_proposals"],h["cad_builds"],h["kfde_rejects"]),(17,17,17))
        self.assertEqual((h["feasible_candidates"],h["visual_renders"],h["visual_objective_evaluations"]),(0,0,0))
        self.assertTrue(all(r["status"]=="KFDE_REJECTED" for r in h["history"]))

    def test_all_raw_kfde_checks_hashed(self):
        for row in load(RESULT/"solver/candidate_history.json")["history"]:
            self.assertEqual(sha(ROOT/row["kfde_check_path"]),row["kfde_check_sha256"])

    def test_no_final_candidate_or_gt(self):
        self.assertFalse((RESULT/"solver/theta_selected.json").exists())
        self.assertFalse((RESULT/"evaluation/final_candidate_lock.json").exists())
        self.assertFalse((RESULT/"evaluation/evaluation_started.json").exists())
        x=load(RESULT/"audit/independent_no_feasible_validation.json")
        self.assertEqual((x["gt_evaluations"],x["final_development_mechanics_evaluations"]),(0,0))

    def test_protocol_gap_not_mislabeled(self):
        x=load(RESULT/"validation.json")
        self.assertIsNone(x["protocol_terminal_decision"])
        self.assertIs(x["categorical_closure_pending_user_direction"],True)

    def test_holdout_lock_closed(self):
        lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
        self.assertIs(lock["accessed"],False)
        self.assertEqual(lock["evaluation_count"],0)


if __name__=="__main__":unittest.main()
