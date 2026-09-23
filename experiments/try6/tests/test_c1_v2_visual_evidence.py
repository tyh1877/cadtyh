"""Deterministic raw-evidence and generator/GT separation checks."""

import math
import unittest

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.c1_v2_visual_objective import VisibleObjective


class C1V2EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=load(HERE/"protocol/try6_0_c1_v2.json")
        cls.result=HERE/"results/try6_0_c1_v2"
        cls.registration=load(cls.result/"visual_metric_evidence/view_registration_report.json")
        cls.evidence=load(cls.result/"visual_metric_evidence/visual_metric_evidence.json")

    def test_raw_source_hashes(self):
        for item in self.evidence["views"].values():
            self.assertEqual(sha(ROOT/item["source_path"]),item["source_sha256"])

    def test_no_claim_of_calibrated_camera(self):
        self.assertIs(self.registration["calibrated"],False)
        self.assertIs(self.registration["candidate_specific_reregistration"],False)

    def test_registration_gate_and_anchor(self):
        self.assertTrue(self.registration["registration_gate_pass"])
        self.assertEqual(self.registration["anchor_distance_mm"],63.0)
        self.assertLessEqual(self.registration["cross_view_relative_scale_discordance"],0.1)

    def test_visible_color_mask_not_gt(self):
        self.assertIs(self.evidence["full_link_silhouette_available"],False)
        for item in self.evidence["views"].values():
            self.assertEqual(sha(ROOT/item["mask_path"]),item["mask_sha256"])
            self.assertIn("raw-color-visible",item["mask_semantics"])

    def test_profile_stations_from_pixels_and_urdf(self):
        for item in self.evidence["views"].values():
            self.assertEqual(len(item["profile_stations"]),3)
            for sample in item["profile_stations"]:
                self.assertAlmostEqual(sample["visible_width_mm"],sample["visible_width_px"]/item["scale_px_per_mm"])

    def test_objective_weights_dimensionless(self):
        self.assertEqual(self.cfg["visual_objective"]["weights"],{"visible_contour_distance":0.5,"visible_profile_width":0.5})
        self.assertEqual(self.cfg["visual_objective"]["gt_terms"],0)
        self.assertEqual(self.cfg["visual_objective"]["mechanical_terms"],0)

    def test_two_candidate_non_gt_smoke(self):
        smoke=load(self.result/"infrastructure_smoke.json")
        self.assertEqual(smoke["candidate_count"],2)
        self.assertEqual(smoke["gt_evaluations"],0)
        self.assertNotEqual(smoke["candidates"][0]["objective"],smoke["candidates"][1]["objective"])
        self.assertTrue(all(math.isfinite(x["objective"]) for x in smoke["candidates"]))

    def test_real_urdf_anchor_changes_visual_target_and_objective(self):
        x=load(self.result/"infrastructure_smoke.json")["anchor_sensitivity"]
        self.assertNotEqual(x["raw_right_station_width_target_mm_at_63"],x["raw_right_station_width_target_mm_at_64"])
        self.assertNotEqual(x["fixed_cad_objective_at_63"],x["fixed_cad_objective_at_64"])

    def test_active_parameter_rule_is_subset_of_registry(self):
        registry={p["id"] for p in load(HERE/"protocol/r1_parameter_registry.json")["parameters"]}
        rule=self.cfg["active_parameter_rule"]
        self.assertLessEqual(set(rule["base"]+rule["if_visible_pocket_present_add"]),registry)
        self.assertNotIn("fillet_radius_mm",rule["base"])

    def test_holdout_lock_metadata(self):
        lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
        self.assertIs(lock["accessed"],False)
        self.assertEqual(lock["evaluation_count"],0)


if __name__=="__main__":unittest.main()
