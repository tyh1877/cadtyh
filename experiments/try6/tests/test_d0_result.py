"""Post-run D0 evidence and denominator checks; no GT/holdout case reads."""

import unittest

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha

RESULT=HERE/"results/try6_0_d0"


class D0ResultTests(unittest.TestCase):
    def test_all_frozen_phases_complete(self):
        x=load(RESULT/"all_candidate_records.json")
        self.assertEqual(x["completed"],322)
        self.assertEqual({phase:sum(r["phase"]==phase for r in x["records"]) for phase in ("canonical","repeat","sobol","local")},
            {"canonical":5,"repeat":1,"sobol":256,"local":60})
        self.assertTrue(all(r["status"]=="EVALUATED" for r in x["records"]))

    def test_same_theta_repeat(self):
        x=load(RESULT/"canonical_probes/reproducibility_check.json")
        self.assertTrue(x["same_theta"] and x["g_sum_match"] and x["g_max_match"])

    def test_strict_density_zero(self):
        x=load(RESULT/"feasible_search/feasible_density.json")
        self.assertEqual(x["stage_a_sample_count"],256)
        self.assertEqual(x["strict_feasible_sample_count"],0)
        self.assertEqual(x["empirical_feasible_sample_density"],0.0)

    def test_counterfactuals_diagnostic_only(self):
        x=load(RESULT/"counterfactual/semantic_suspect_summary.json")
        self.assertTrue(all(value==0 for value in x["strict_feasible_count_by_subset"].values()))
        self.assertEqual(x["SEMANTIC_MISMODEL_SUSPECT_neighbors"],[])
        self.assertIs(x["no_KFDE_artifact_modified"],True)

    def test_best_violation_above_frozen_epsilon(self):
        x=load(RESULT/"audit/independent_validation.json")
        self.assertEqual(x["decision"],"DOMAIN_KFDE_INCOMPATIBLE")
        self.assertGreater(x["best_g_max_mm3"],10.0)
        self.assertEqual(x["strict_epsilon_mm3"],1e-6)

    def test_exact_f0_mapping_not_invented(self):
        x=load(RESULT/"authority_audit/f0_consistency_audit.json")
        self.assertIs(x["exact_F0_equivalent_current_theta_mapping_available"],False)
        self.assertFalse((RESULT/"canonical_probes/P5_result.json").exists())

    def test_frozen_c1_c2_artifact_hashes(self):
        cfg=load(HERE/"protocol/try6_0_d0.json")
        self.assertEqual(sha(ROOT/cfg["active_parameter_source"]),load(RESULT/"pre_run_manifest.json")["active_bounds_sha256"])
        self.assertEqual(sha(ROOT/cfg["kfde_construction_source"]),load(RESULT/"pre_run_manifest.json")["kfde_construction_sha256"])

    def test_no_gt_vlm_mechanics_or_holdout(self):
        x=load(RESULT/"audit/independent_validation.json")
        self.assertEqual((x["VLM_calls"],x["GT_evaluations"],x["final_mechanics_evaluations"]),(0,0,0))
        lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
        self.assertIs(lock["accessed"],False)
        self.assertEqual(lock["evaluation_count"],0)


if __name__=="__main__":unittest.main()
