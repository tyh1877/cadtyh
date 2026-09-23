# Try-6.0-C2 requirement-to-evidence checklist

C2 isolates KFDE against frozen C1-v2 L04. No new VLM call, GT/holdout in
construction or optimization, C1 repair, pocket reclassification, or C2 tuning.

- [x] Hash-audit frozen C1 and exact slot/KFDG/active theta/bounds/images/registration/objective/optimizer/compiler/evaluator parity; holdout closed (`pre_run_manifest.json`, `frozen_c1/parity_audit.json`).
- [x] Freeze independent URDF-derived J03/J05 sweep, L03/L05/L06/L07 neighbors, L04 frame, allowed scaffold/interface region, zero margin and 1e-6 mm³ numerical tolerance before replay (`protocol/try6_0_c2.json`).
- [x] Construct and independently audit a non-empty 13-component exact BREP keepout, pose sensitivity, L04 frame, interface exemption and no GT/development-case/C1-failure leakage (`kfde/`).
- [x] Replay all 32 frozen C1 CAD candidates without regeneration or final mechanics; 32/32 meaningfully KFDE-infeasible, including `candidate_031` (`replay/`).
- [x] Enforce activity gate: `KFDE_INACTIVE` false; independent validator permitted formal C2.
- [x] Run one same-policy frozen C2 search: 17 valid CAD proposals, 17 hard KFDE rejections before render, 0 feasible, 0 visual ranking (`solver/`, `audit/independent_no_feasible_validation.json`).
- [ ] Final C2 candidate lock: **impossible** because no feasible theta exists under the frozen search; do not invent or select a rejected candidate.
- [ ] Final GT geometry/96-case mechanics and preservation/benefit gates: **not reached**; GT and final mechanics count 0.
- [x] Independently verify all 17 rejections, source/protocol hashes, C1 proposal parity, no VLM/GT/holdout, no tuning. **Protocol gap:** no allowed final decision label exactly covers this zero-feasible state; direction requested from user before categorical closure.
