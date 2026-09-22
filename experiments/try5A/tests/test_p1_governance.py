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


if __name__ == "__main__":
    unittest.main()
