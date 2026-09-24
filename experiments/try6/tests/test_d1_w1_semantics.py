"""Pure threshold/topology tests frozen before W1 real witness construction."""

import unittest

from experiments.try6.scripts.w1_semantics import relief_category, sensitivity_category, topology_class


class W1SemanticsTests(unittest.TestCase):
    def test_below_five(self):
        self.assertEqual(sensitivity_category([0.038, 0.0382])["category"], "SMALL_RELIEF")

    def test_cross_five(self):
        self.assertEqual(sensitivity_category([0.049, 0.051])["category_status"],
                         "RELIEF_CATEGORY_NUMERICALLY_AMBIGUOUS")

    def test_between_five_and_fifteen(self):
        self.assertEqual(relief_category(0.1), "MODERATE_RELIEF")

    def test_cross_fifteen(self):
        self.assertEqual(sensitivity_category([0.149, 0.151])["category_status"],
                         "RELIEF_CATEGORY_NUMERICALLY_AMBIGUOUS")

    def test_above_fifteen(self):
        self.assertEqual(relief_category(0.2), "LARGE_RELIEF")

    def test_frozen_boundaries(self):
        self.assertEqual(relief_category(0.05), "SMALL_RELIEF")
        self.assertEqual(relief_category(0.15), "MODERATE_RELIEF")

    def test_topology_classes(self):
        self.assertEqual(topology_class("VALID_SINGLE_SOLID", 1), "CONNECTED_SINGLE_SOLID")
        self.assertEqual(topology_class("VALID_MULTI_SOLID", 3), "DISCONNECTED_MULTI_SOLID")
        self.assertEqual(topology_class("EFFECTIVELY_EMPTY", 0), "EFFECTIVELY_EMPTY")


if __name__ == "__main__":
    unittest.main()
