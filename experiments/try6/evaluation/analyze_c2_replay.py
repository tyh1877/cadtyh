"""Post-hoc descriptive C1 replay correlations; never used by KFDE/optimizer."""

from __future__ import annotations

import json

from scipy.stats import spearmanr

from experiments.try6.scripts.r1_contract import HERE,load
from experiments.try6.scripts.run_r1_reliability import save


def main():
    root=HERE/"results/try6_0_c2"
    replay=load(root/"replay/c1_candidate_replay.json")
    params=load(HERE/"results/try6_0_c1_v2/kfdg/active_parameters.json")["active_ids"]
    rows=replay["records"]
    volumes=[r["maximum_forbidden_intersection_mm3"] for r in rows]
    correlations={pid:float(spearmanr([r["theta"][pid] for r in rows],volumes).statistic) for pid in params}
    output={"schema_version":"robotcad_try6_c2_replay_descriptive_v1","denominator":len(rows),
        "all_candidates_infeasible":all(r["feasible"] is False for r in rows),
        "target":"maximum per-pose forbidden intersection volume mm3",
        "spearman_rho_by_parameter":correlations,
        "interpretation_limit":"post-hoc descriptive correlation within 32 C1 proposals; no causal/GT claim and not consumed by KFDE or C2 optimizer"}
    save(root/"replay/descriptive_correlations.json",output)
    print(json.dumps({"denominator":len(rows),"spearman_rho_by_parameter":correlations}))


if __name__=="__main__":main()
