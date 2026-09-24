"""Synthetic preregistration checks; no frozen witness is opened."""

import unittest

from experiments.try6.scripts.w1_v2_zero_rule import epsilon_zero, normalize_removed_volume
from experiments.try6.scripts.w1_semantics import sensitivity_category


class ZeroRuleTests(unittest.TestCase):
    def setUp(self):
        self.epsilon = epsilon_zero(1000.0, 1e-8)

    def test_negative_inside(self):
        self.assertEqual(normalize_removed_volume(-self.epsilon/2, self.epsilon)["normalized_removed_volume_mm3"], 0)

    def test_negative_exact_boundary_inclusive(self):
        self.assertEqual(normalize_removed_volume(-self.epsilon, self.epsilon)["normalized_removed_volume_mm3"], 0)

    def test_negative_outside(self):
        self.assertEqual(normalize_removed_volume(-2*self.epsilon, self.epsilon)["status"], "WITNESS_NUMERICALLY_UNSTABLE")

    def test_tiny_positive_preserved(self):
        self.assertEqual(normalize_removed_volume(1e-12, self.epsilon)["normalized_removed_volume_mm3"], 1e-12)

    def test_positive_near_five_preserved(self):
        self.assertEqual(normalize_removed_volume(49.99, self.epsilon)["normalized_removed_volume_mm3"], 49.99)

    def test_cross_five_remains_ambiguous(self):
        self.assertEqual(sensitivity_category([0.0499, 0.0501])["category_status"], "RELIEF_CATEGORY_NUMERICALLY_AMBIGUOUS")

    def test_cross_fifteen_remains_ambiguous(self):
        self.assertEqual(sensitivity_category([0.1499, 0.1501])["category_status"], "RELIEF_CATEGORY_NUMERICALLY_AMBIGUOUS")

    def test_one_part_per_million_scale(self):
        self.assertEqual(self.epsilon, 0.001)
        self.assertAlmostEqual(0.05 / 1e-6, 50000)

    def test_absolute_floor_dominates_small_source(self):
        self.assertEqual(epsilon_zero(1e-5, 1e-8), 1e-8)


if __name__ == "__main__":
    unittest.main()
