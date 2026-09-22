from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import trimesh

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "evaluation"))
sys.path.insert(0, str(HERE / "scripts"))

from geometry_holdout_evaluator import metric as holdout_metric  # noqa: E402
from run_try5b1 import metric as frozen_runner_metric  # noqa: E402


class P1GovernanceTests(unittest.TestCase):
    def test_holdout_geometry_metric_matches_frozen_runner(self):
        reference = trimesh.creation.box(extents=(10.0, 20.0, 30.0))
        prediction = trimesh.creation.box(extents=(11.0, 19.0, 29.0))
        prediction.apply_translation((0.5, -0.25, 0.75))
        expected = frozen_runner_metric(reference, prediction, 12003)
        actual = holdout_metric(reference, prediction, 12003)
        self.assertEqual(set(actual), set(expected))
        for key in expected:
            self.assertAlmostEqual(actual[key], expected[key], places=12)

    def test_analysis_plan_freezes_denominator_and_failure_policy(self):
        plan = json.loads((HERE / "protocol/try5b1_a1_p1_analysis_plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["comparison"]["paired_holdout_configuration_count"], 32)
        self.assertFalse(plan["analysis_rules"]["drop_failed_cases"])
        self.assertFalse(plan["analysis_rules"]["post_holdout_code_or_metric_change"])
        self.assertTrue(plan["failure_policy"]["crash_or_interrupt_consumes_attempt"])
        self.assertFalse(plan["failure_policy"]["delete_lock_to_retry"])

    def test_evaluator_only_modules_do_not_import_generator(self):
        for relative in (
            "evaluation/geometry_holdout_evaluator.py",
            "evaluation/mechanical/freecad_holdout_evaluator.py",
        ):
            source = (HERE / relative).read_text(encoding="utf-8")
            self.assertNotIn("run_try5b1", source)
            self.assertNotIn("freecad_link_refinement", source)

    def test_geometry_protection_protocol_has_no_runtime_controller(self):
        protocol = json.loads((HERE / "protocol/try5b1_a1_geometry_protection.json").read_text(encoding="utf-8"))
        self.assertFalse(protocol["shared"]["runtime_rejection"])
        self.assertFalse(protocol["shared"]["runtime_rollback"])
        self.assertFalse(protocol["shared"]["post_generation_repair"])
        for condition in protocol["conditions"].values():
            self.assertEqual(set(condition), {"mechanical_geometry_policy"})
            self.assertNotIn("mechanical_rejection", condition["mechanical_geometry_policy"])
            self.assertNotIn("rollback_on_failure", condition["mechanical_geometry_policy"])

    def test_declarative_metrics_are_excluded_from_main_analysis(self):
        protocol = json.loads((HERE / "protocol/try5b1_a1_geometry_protection.json").read_text(encoding="utf-8"))
        self.assertEqual(
            set(protocol["shared"]["excluded_declarative_metrics"]),
            {"swept_clearance_preserved", "forbidden_fusion_count", "virtual_solid_count", "meaningless_patch_count"},
        )

    def test_protection_effect_audit_is_geometry_only(self):
        protocol = json.loads((HERE / "protocol/try5b1_a1_protection_effect_audit.json").read_text(encoding="utf-8"))
        self.assertEqual(protocol["links"], ["L03", "L04", "L07"])
        self.assertEqual(protocol["refinement_condition"], "F2")
        self.assertEqual(len(protocol["operations"]), 5)
        self.assertTrue(all(protocol["prohibited"].values()))

    def test_generic_joint_sample_schema_has_no_holdout_label(self):
        source = (HERE / "evaluation/mechanical/freecad_holdout_evaluator.py").read_text(encoding="utf-8")
        self.assertNotIn('"holdout_samples"', source)
        self.assertNotIn('"all_holdout_samples_pass"', source)
        self.assertIn('"sample_count"', source)

    def test_scaffold_protocol_has_exactly_one_condition_difference(self):
        protocol = json.loads((HERE / "protocol/try5b1_a1_frozen_scaffold_ablation.json").read_text(encoding="utf-8"))
        self.assertEqual(protocol["allowed_condition_differences"], ["mechanical_geometry_policy.preserve_frozen_scaffold"])
        s1 = protocol["conditions"]["S1_SCAFFOLD_PRESERVED"]["mechanical_geometry_policy"]
        s0 = protocol["conditions"]["S0_SCAFFOLD_REMOVED"]["mechanical_geometry_policy"]
        self.assertTrue(s1["preserve_frozen_scaffold"])
        self.assertFalse(s0["preserve_frozen_scaffold"])
        self.assertEqual({key: value for key, value in s1.items() if key != "preserve_frozen_scaffold"}, {key: value for key, value in s0.items() if key != "preserve_frozen_scaffold"})
        self.assertFalse(s1["auto_attachment_closure"])

    def test_formal_runner_input_contains_development_only(self):
        formal_input = json.loads((HERE / "protocol/try5b1_a1_development_input.json").read_text(encoding="utf-8"))
        split = json.loads((HERE / "results/try5b1_a1_development/case_split.json").read_text(encoding="utf-8"))
        case_ids = {item["config_id"] for item in formal_input["coupled_configurations"]}
        self.assertEqual(len(case_ids), 96)
        self.assertEqual(case_ids, set(split["development"]["case_ids"]))
        self.assertFalse(case_ids & set(split["holdout"]["case_ids"]))
        self.assertFalse(formal_input["contains_formal_holdout_configurations"])

    def test_a2a_budget_and_scaffold_are_paired(self):
        protocol = json.loads((HERE / "protocol/try5b1_a2a_same_model_l04.json").read_text(encoding="utf-8"))
        self.assertEqual(protocol["model"]["requested_identifier"], "qwen3.7-plus")
        self.assertEqual(protocol["model"]["max_vlm_calls_per_condition"], 1)
        self.assertEqual(protocol["model"]["max_refinement_rounds"], 0)
        self.assertEqual(protocol["model"]["max_retries"], 0)
        self.assertTrue(protocol["shared_inputs"]["mechanical_policy"]["preserve_frozen_scaffold"])
        self.assertEqual(set(protocol["conditions"]), {"STRUCTURED_QWEN", "DIRECT_QWEN"})

    def test_direct_prompt_contains_no_structured_family_answers(self):
        direct = (HERE / "prompts/a2a_direct_qwen_l04.md").read_text(encoding="utf-8")
        for forbidden in ("central_web", "compound_profile_housing", "gripper_support", "span_mm", "major_recess"):
            self.assertNotIn(forbidden, direct)
        structured = (HERE / "prompts/a2a_structured_qwen_l04.md").read_text(encoding="utf-8")
        self.assertIn("compound_profile_housing", structured)


if __name__ == "__main__":
    unittest.main()
