"""Frozen D0 diagnostic policy, component arithmetic and leakage boundaries."""

import unittest

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha


class D0ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=load(HERE/"protocol/try6_0_d0.json")
        cls.c1=load(ROOT/cls.cfg["active_parameter_source"])
        cls.kfde=load(ROOT/cls.cfg["kfde_construction_source"])

    def test_exact_six_bounds_unchanged(self):
        self.assertEqual(len(self.c1["active_ids"]),6)
        self.assertEqual(set(self.c1["active_ids"]),set(self.c1["active_bounds"]))
        self.assertEqual(self.cfg["active_parameter_source"],"experiments/try6/results/try6_0_c1_v2/kfdg/active_parameters.json")

    def test_exact_kfde_hash_sources(self):
        self.assertEqual(len(self.kfde["components"]),13)
        self.assertEqual(sha(ROOT/self.kfde["keepout"]["path"]),self.kfde["keepout"]["sha256"])
        self.assertEqual(sha(ROOT/self.kfde["allowed_region"]["path"]),self.kfde["allowed_region"]["sha256"])
        self.assertEqual(self.cfg["strict_feasibility_epsilon_mm3"],self.kfde["numerical_tolerance_mm3"])

    def test_predeclared_budgets(self):
        self.assertEqual(self.cfg["stage_a"]["sample_count"],256)
        self.assertEqual(self.cfg["stage_b"]["seed_count"],5)
        self.assertEqual(self.cfg["stage_b"]["proposals_per_seed"],12)
        self.assertEqual(self.cfg["stage_b"]["total_proposal_budget"],60)
        self.assertEqual(self.cfg["maximum_total_runtime_seconds"],1800)

    def test_canonical_probe_ids(self):
        self.assertEqual(self.cfg["canonical_probes"],["P0_ALL_LOWER","P1_ALL_UPPER","P2_MIDPOINT","P3_C1_INITIAL","P4_C1_VISUAL_WINNER"])
        self.assertEqual(self.cfg["deterministic_repeat_probe"],"P3_C1_INITIAL")

    def test_component_decomposition_matches_frozen_C2(self):
        result=load(HERE/"artifacts/try6_0_d0/technical_smoke/component_result.json")
        c2=load(HERE/"artifacts/try6_0_c2/replay/candidate_000_check.json")
        self.assertEqual(len(result["components"]),13)
        self.assertAlmostEqual(result["g_sum_mm3"],sum(x["intersection_volume_mm3"] for x in result["components"]))
        self.assertAlmostEqual(result["g_max_mm3"],max(x["intersection_volume_mm3"] for x in result["components"]))
        self.assertAlmostEqual(result["g_max_mm3"],c2["maximum_forbidden_intersection_mm3"],places=6)

    def test_counterfactual_only_removes_named_neighbor(self):
        rows=load(HERE/"artifacts/try6_0_d0/technical_smoke/component_result.json")["components"]
        for subset,neighbor in (("MINUS_L05","L05"),("MINUS_L07","L07"),("MINUS_L06","L06"),("MINUS_L03","L03")):
            self.assertIn(subset,self.cfg["counterfactual_subsets"])
            remaining=[r for r in rows if r["neighbor_id"]!=neighbor]
            self.assertEqual(len(rows)-len(remaining),sum(r["neighbor_id"]==neighbor for r in rows))
            self.assertEqual({r["neighbor_id"] for r in remaining},{"L03","L05","L06","L07"}-{neighbor})

    def test_no_visual_gt_or_mechanics_ranking(self):
        self.assertEqual(self.cfg["ranking_terms"],["g_max_mm3","g_sum_mm3"])
        self.assertEqual(self.cfg["VLM_calls"],0)
        self.assertEqual(self.cfg["GT_evaluations"],0)
        self.assertEqual(self.cfg["final_96_case_mechanics_evaluations"],0)

    def test_holdout_lock_closed(self):
        lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
        self.assertIs(lock["accessed"],False)
        self.assertEqual(lock["evaluation_count"],0)


if __name__=="__main__":unittest.main()
