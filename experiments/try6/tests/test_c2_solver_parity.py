"""Preformal C2 proposal/bounds parity against frozen C1 visual search."""

import unittest

import numpy as np
from scipy.stats import qmc

from experiments.try6.scripts.r1_contract import HERE,load


class C2SearchParityTests(unittest.TestCase):
    def test_initial_and_first_sobol_16_match_frozen_c1(self):
        c1=HERE/"results/try6_0_c1_v2"
        active=load(c1/"kfdg/active_parameters.json")
        config=load(c1/"solver/config.json")
        history=load(c1/"solver/candidate_history.json")["history"]
        ids=active["active_ids"]
        bounds=np.asarray([active["active_bounds"][pid] for pid in ids])
        vectors=[np.asarray([active["initial_theta"][pid] for pid in ids])]
        vectors.extend(bounds[:,0]+point*(bounds[:,1]-bounds[:,0]) for point in qmc.Sobol(d=len(ids),scramble=True,seed=config["seed"]).random_base2(m=4))
        self.assertEqual(len(vectors),17)
        for i,vector in enumerate(vectors):
            self.assertEqual(history[i]["candidate_id"],f"candidate_{i:03d}")
            self.assertTrue(np.allclose(vector,[history[i]["theta"][pid] for pid in ids],atol=1e-12,rtol=0))

    def test_same_optimizer_config_and_no_new_vlm(self):
        cfg=load(HERE/"protocol/try6_0_c2.json")
        c1=load(HERE/"results/try6_0_c1_v2/solver/config.json")
        self.assertEqual(cfg["c2_max_proposals_if_active"],c1["max_candidate_evaluations"])
        self.assertIs(cfg["no_new_vlm_call"],True)


if __name__=="__main__":unittest.main()
