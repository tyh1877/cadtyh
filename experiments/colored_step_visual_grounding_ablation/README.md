# Colored STEP Visual Grounding Ablation

This experiment is a paired GT-oracle diagnostic of whether per-link coloring
improves RobotCAD visual grounding and downstream Mechanical Embodiment Planning.

**2026-09-05: existing runs audited and archived; NO-GO for confirmatory promotion.**
E1 has 43/45 successful calls across three recorded replicates; E2 has 14/15
successful cells (one upstream failure). The native cohort is 58 STEP leaf
components, not an authoritatively mapped URDF-link cohort. Scientific completion
remains blocked by unmet protocol gates. See [CLOSEOUT.md](CLOSEOUT.md) for results,
deviations, resource accounting and reproducible offline validation.

See `protocol.md` for the frozen comparison and interpretation guard. Heavy
FreeCAD, STEP, render, mask, crop, and raw model artifacts are written below
`artifacts/` and `runs/` and are intentionally excluded from Git.
