"""Post-run evidence checks only; never called by the generator or solver."""

import unittest

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.r1_v3_contract import assemble,validate_kfdg,validate_slots

RESULT=HERE/"results/try6_0_c1_v2"


class C1V2ResultTests(unittest.TestCase):
    def test_fresh_slot_not_repaired(self):
        raw=load(RESULT/"slot/raw_response.txt")
        checked=validate_slots(raw)
        self.assertEqual(checked,load(RESULT/"slot/validated_slots.json"))
        graph=assemble(checked)
        self.assertEqual(graph,load(RESULT/"kfdg/canonical_kfdg.json"))
        self.assertTrue(validate_kfdg(graph,checked))

    def test_pocket_absent_and_inactive(self):
        active=load(RESULT/"kfdg/active_parameters.json")
        self.assertEqual(active["slot_statuses"]["visible_pocket"],"ABSENT")
        self.assertFalse(any(p.startswith("recess_") for p in active["active_ids"]))
        tree=load(RESULT/"cad/export_reopen.json")["feature_tree"]
        self.assertNotIn("VisibleRecessPocket",[item["name"] for item in tree])

    def test_full_candidate_denominator(self):
        history=load(RESULT/"solver/candidate_history.json")
        self.assertEqual(history["evaluated"],32)
        self.assertEqual(history["valid"]+history["invalid"],32)
        self.assertEqual([r["candidate_id"] for r in history["history"]],[f"candidate_{i:03d}" for i in range(32)])

    def test_selected_visual_minimum(self):
        history=load(RESULT/"solver/candidate_history.json")["history"]
        selected=load(RESULT/"solver/theta_selected.json")
        best=min((r for r in history if r["status"]=="PASS"),key=lambda r:r["total_visual_objective"])
        self.assertEqual(selected["selected_candidate_id"],best["candidate_id"])
        self.assertEqual(selected["theta_star"],best["theta"])
        self.assertIs(selected["mechanical_feedback"],False)
        self.assertIs(selected["gt_accessed"],False)

    def test_candidate_locked_before_gt(self):
        lock_path=RESULT/"evaluation/final_candidate_lock.json"
        lock=load(lock_path)
        start=load(RESULT/"evaluation/evaluation_started.json")
        self.assertLess(lock["timestamp_utc"],start["timestamp_utc"])
        self.assertEqual(start["final_candidate_lock_sha256"],sha(lock_path))
        self.assertEqual(lock["gt_evaluation_count_at_lock"],0)

    def test_final_cad_artifact_integrity(self):
        lock=load(RESULT/"evaluation/final_candidate_lock.json")
        for item in lock["final_cad_artifacts"].values():
            self.assertEqual(sha(ROOT/item["path"]),item["sha256"])
        self.assertEqual(lock["connected_solid_count"],1)
        self.assertIs(lock["interface_invariant"],True)

    def test_geometry_gate_from_exact_artifact(self):
        comparison=load(RESULT/"evaluation/c0_vs_c1.json")
        self.assertTrue(comparison["all_geometry_gates_pass"])
        self.assertGreaterEqual(comparison["c1"]["final_voxel_iou"],load(HERE/"protocol/try6_0_c1_v2.json")["primary_iou_gate"])
        self.assertEqual(comparison["decision"],"GO_C2")

    def test_mechanics_diagnostic_and_holdout_closed(self):
        m=load(RESULT/"evaluation/mechanical_metrics.json")
        self.assertEqual(m["configuration_count"],96)
        self.assertIs(m["mechanical_feedback_to_solver"],False)
        lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
        self.assertIs(lock["accessed"],False)
        self.assertEqual(lock["evaluation_count"],0)


if __name__=="__main__":unittest.main()
