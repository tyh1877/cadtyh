"""Canonical/API divergence is exactly three uniqueItems removals."""

import copy
import unittest

from jsonschema import Draft202012Validator

from experiments.try6.scripts.r1_contract import HERE, load, validate_vfp
from experiments.try6.scripts.r1_v2_projection import project


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.canonical = load(HERE / "protocol/r1_vfp.schema.json")
        self.rules = load(HERE / "protocol/r1_v2_projection_rules.json")
        self.api, self.removed = project(self.canonical,self.rules)
        self.valid = load(HERE / "fixtures/r1_valid_vfp.json")

    def test_only_uniqueitems_removed(self):
        self.assertEqual(len(self.removed),3)
        self.assertEqual({x["keyword"] for x in self.removed},{"uniqueItems"})
        self.assertTrue(all("/properties/" in x["path"] for x in self.removed))

    def test_canonical_unchanged(self):
        self.assertEqual(sum("uniqueItems" in str(x) for x in [self.canonical]),1)
        self.assertNotIn("uniqueItems",str(self.api))

    def test_no_other_keyword_deleted(self):
        def strip(value):
            if isinstance(value,dict): return {k:strip(v) for k,v in value.items() if k != "uniqueItems"}
            if isinstance(value,list): return [strip(v) for v in value]
            return value
        self.assertEqual(self.api,strip(self.canonical))

    def test_projection_deterministic(self): self.assertEqual(project(self.canonical,self.rules),project(self.canonical,self.rules))

    def test_unexpected_removal_count_rejected(self):
        rules = copy.deepcopy(self.rules); rules["expected_removed_count"] = 2
        with self.assertRaises(ValueError): project(self.canonical,rules)

    def test_local_duplicate_roles_still_rejected(self):
        item = copy.deepcopy(self.valid); item["visual_features"][0]["parameter_roles"].append("width")
        Draft202012Validator(self.api).validate(item)
        with self.assertRaises(Exception): validate_vfp(item)

    def test_local_duplicate_evidence_still_rejected(self):
        item = copy.deepcopy(self.valid); item["visual_features"][0]["evidence_views"].append("isometric")
        Draft202012Validator(self.api).validate(item)
        with self.assertRaises(Exception): validate_vfp(item)

    def test_local_duplicate_relations_still_rejected(self):
        item = copy.deepcopy(self.valid); item["visual_features"][1]["relations"].append(copy.deepcopy(item["visual_features"][1]["relations"][0]))
        Draft202012Validator(self.api).validate(item)
        with self.assertRaises(Exception): validate_vfp(item)


if __name__ == "__main__": unittest.main()
