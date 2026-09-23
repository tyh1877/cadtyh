"""Frozen D1 case/threshold/scope checks; no GT or holdout case reads."""

import unittest

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha


class D1ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.cfg=load(HERE/"protocol/try6_0_d1.json")

    def test_geometry_set_exact_frozen_files(self):
        self.assertEqual([x["geometry_id"] for x in self.cfg["geometry_set"]],
            ["G1_C1_FINAL","G2_D0_P0","G3_D0_P3","G4_C0_DIRECT","G5_F0_COARSE"])
        self.assertTrue(all((ROOT/x["path"]).is_file() for x in self.cfg["geometry_set"]))

    def test_all_thirteen_frozen_components(self):
        construction=load(ROOT/self.cfg["kfde_construction"])
        self.assertEqual(len(construction["components"]),13)
        self.assertEqual(sha(ROOT/construction["keepout"]["path"]),construction["keepout"]["sha256"])
        self.assertEqual(sha(ROOT/construction["allowed_region"]["path"]),construction["allowed_region"]["sha256"])

    def test_alignment_descriptive_thresholds(self):
        self.assertEqual(self.cfg["alignment_high_min_fraction"],0.9)
        self.assertEqual(self.cfg["substantial_false_positive_min_fraction"],0.1)
        self.assertEqual(self.cfg["material_exact_overlap_mm3"],1.0)

    def test_witness_thresholds_and_fixed_subsets(self):
        self.assertEqual((self.cfg["witness_small_removed_ratio_max"],self.cfg["witness_moderate_removed_ratio_max"]),(0.05,0.15))
        self.assertEqual(self.cfg["witness_localized_one_longitudinal_third_min_fraction"],0.8)
        self.assertEqual(self.cfg["witness_subsets"],["FULL","L03","L05","L06","L07","L03_L05","L03_L06","L05_L06","L03_L05_L06"])

    def test_exact_mechanics_source_unchanged(self):
        pre=load(HERE/"results/try6_0_c1_v2/pre_run_manifest.json")
        self.assertEqual(sha(ROOT/"experiments/try5A/evaluation/mechanical/freecad_holdout_evaluator.py"),pre["evaluator_hashes"]["mechanical_evaluator"])
        self.assertTrue((ROOT/self.cfg["exact_mechanics_source"]).is_file())

    def test_no_gt_vlm_visual_or_full_mechanics(self):
        self.assertTrue(self.cfg["no_GT_geometry"] and self.cfg["no_VLM"] and self.cfg["no_C1_visual_objective_call"] and self.cfg["no_final_96_case_mechanics"])
        self.assertEqual(self.cfg["kfde_numerical_epsilon_mm3"],1e-6)

    def test_holdout_lock_closed(self):
        lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
        self.assertIs(lock["accessed"],False)
        self.assertEqual(lock["evaluation_count"],0)


if __name__=="__main__":unittest.main()
