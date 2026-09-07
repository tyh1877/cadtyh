# Phase 8 post-review gate amendment

Formal attempt 01 used the frozen Phase-5 numeric/trace gate as the complete
post-repair decision. Manual contact-sheet audit found three numeric PASS results
with major visible topology/LOD failures. This contradicted `try4.md` Gate B/C,
which also requires visible mechanical features, semantic role and LOD.

Attempt 01 is preserved under `results/phase8_attempt_01/` and its method hash is
preserved as `phase78_method_snapshot_attempt_01.json`. The continuation adds a
schema-valid current-agent post-review outcome to PASS decisions. A Part freezes
only when both the unchanged numeric gate and post-review pass. The Phase-5
evaluator, numeric thresholds, prior geometry and repair parameters are not
changed. R02_P01, R02_P02 and R02_P04 therefore continue through their remaining
round budget. This is a development-method correction on DEV_B, before Robot C.
