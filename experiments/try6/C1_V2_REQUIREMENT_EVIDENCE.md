# Try-6.0-C1-v2 formal development requirement-to-evidence checklist

One L04 candidate only. Frozen C1-v1/R0/R1 results remain immutable. No C2,
KFDE, formal holdout, GT-guided generation, or repeated final evaluation.

- [ ] Audit frozen C0 source/metrics, R1-v3 readiness, input hashes, evaluator versions, and holdout lock.
- [ ] Extract visual metric evidence from raw images only; freeze usable views, approximate registration, residuals, contours, landmarks, station profiles, visibility policy and their hashes before solver.
- [ ] Fail closed as `CAMERA_REGISTRATION_BLOCKED` or `VISUAL_EVIDENCE_PIPELINE_BLOCKED` if those respective computed gates fail.
- [ ] Freeze one fresh slot call protocol, active-parameter rule, normalized visual-only objective, optimizer/bounds/seed/budget, technical retry policy, and GT-separation audit before the formal candidate.
- [ ] Run one fresh Qwen slot call, preserve raw response and exact request, validate full local contract and deterministic KFDG without repair.
- [ ] Evaluate every pre-registered solver candidate; select theta solely by lowest legal visual objective, with no mechanical or GT feedback.
- [ ] Build/export/reopen final CAD; verify feature/parameter mapping, connected solid and frozen interface before GT.
- [ ] Write `final_candidate_lock.json` with theta and all upstream hashes before first GT access.
- [ ] Run one final geometry evaluation and one diagnostic mechanical evaluation only after lock, preserving all failures/denominators.
- [ ] Independently validate exact C0-vs-C1 gates, objective alignment, leakage, process/failure accounting, holdout lock and final decision; stop before C2.
