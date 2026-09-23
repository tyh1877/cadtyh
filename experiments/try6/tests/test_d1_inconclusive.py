"""Post-run D1 fail-closed accounting, with no GT/holdout case reads."""

import unittest

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha

RESULT=HERE/"results/try6_0_d1"


class D1InconclusiveTests(unittest.TestCase):
    def test_all_five_frozen_geometries_available(self):
        x=load(RESULT/"frozen_inputs/geometry_set.json")
        self.assertEqual(x["status"],"PASS")
        self.assertEqual(len(x["geometries"]),5)
        self.assertTrue(all(sha(ROOT/g["source_path"])==g["source_sha256"] for g in x["geometries"]))

    def test_f0_mutable_scope_zero_volume(self):
        x=load(RESULT/"frozen_inputs/geometry_set.json")
        f0=next(g for g in x["geometries"] if g["geometry_id"]=="G5_F0_COARSE")
        self.assertEqual(f0["mutable_volume_mm3"],0.0)
        self.assertEqual(f0["extraction"],"full_link_minus_frozen_allowed_region")

    def test_only_one_recorded_technical_retry(self):
        marker=load(RESULT/"alignment/technical_retry_started.json")
        self.assertEqual(marker["max_technical_retries"],1)
        self.assertIs(marker["scientific_protocol_unchanged"],True)
        self.assertIn("ValueError: Null shape",load(RESULT/"alignment/failure.json")["error"])

    def test_no_partial_alignment_or_witness_promoted(self):
        self.assertFalse((RESULT/"alignment/raw_alignment.json").exists())
        self.assertFalse((RESULT/"witness/witness_summary.json").exists())

    def test_decision_cannot_claim_semantics(self):
        x=load(RESULT/"audit/independent_validation.json")
        self.assertEqual(x["decision"],"DIAGNOSTIC_INCONCLUSIVE")
        self.assertIs(x["alignment_rate_not_evaluable"],True)
        self.assertIs(x["relief_capacity_not_classified"],True)

    def test_gt_vlm_mechanics_and_holdout_zero(self):
        x=load(RESULT/"audit/independent_validation.json")
        self.assertEqual((x["VLM_calls"],x["GT_geometry_evaluations"],x["final_96_case_mechanics_evaluations"]),(0,0,0))
        lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
        self.assertIs(lock["accessed"],False)
        self.assertEqual(lock["evaluation_count"],0)


if __name__=="__main__":unittest.main()
