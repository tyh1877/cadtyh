# Try-6.0-C2 requirement-to-evidence checklist

C2 isolates KFDE against frozen C1-v2 L04. No new VLM call, GT/holdout in
construction or optimization, C1 repair, pocket reclassification, or C2 tuning.

- [ ] Hash-audit frozen C1 artifacts, exact parity of slot/KFDG/active theta/bounds/images/view registration/objective/optimizer/compiler/evaluators, and holdout lock.
- [ ] Freeze independent URDF-derived J03/J05 design sweep, L03/L05/L06/L07 neighbor geometry, L04 frame, explicit allowed scaffold/interface region and zero-margin/numerical tolerance before replay.
- [ ] Build non-empty exact FreeCAD BREP keepout; prove pose-transform sensitivity, L04-frame correctness, interface exemption, and zero GT/final-mechanics leakage.
- [ ] Replay all 32 frozen C1 candidates without regeneration, GT or 96-case evaluator; compute meaningful activity and C1 selected-candidate feasibility.
- [ ] If all 32 feasible and C1 selected has no meaningful violation, stop as `KFDE_INACTIVE` without formal C2.
- [ ] Otherwise run the identical 32-proposal visual optimizer with hard KFDE pre-render rejection, preserving every proposal and never ranking by mechanics/GT.
- [ ] Lock final C2 CAD/theta/KFDE/config/history hashes before any GT or full mechanics evaluation.
- [ ] Run one final same-evaluator geometry and 96-case exact mechanics diagnosis; independently compute geometry preservation, mechanical non-regression and ≥10% incremental benefit.
- [ ] Independently validate final decision, leakage/failure accounting, holdout lock and frozen C1 immutability; stop before Try-6.1.
