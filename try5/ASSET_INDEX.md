# Try5 asset index

This directory is the collaboration entry point for the Try5 series. Generated
FCStd, STEP, STL, render caches and raw collision caches are deliberately ignored;
the tracked CAD IR, contracts, scripts, manifests and metrics reproduce them.

| Asset | Location | Purpose |
| --- | --- | --- |
| Try5-A protocol | `try5/Try5-A.md` | Top-down URDF-guided coarse reconstruction protocol. |
| Try5-A.1 protocol | `try5/Try5-A.1.md` | Collision-aware one-shot body replanning. |
| Try5-A.2 protocol | `try5/Try-5A.2.md` | Attachment closure and quality-gated local repair. |
| Active implementation | `experiments/try5A/` | Shared scripts, inputs, planning layers, A0/A1/A2 and Try5-A.2 work. |
| A.1 historical experiment | `experiments/try5A_1/` | Frozen C0/C1/C2 evidence and exact collision evaluator. |
| A.2 attachment closure | `experiments/try5A/try5A_2/D0_physicalized/` | Attachment subregions, repair contracts and Phase 3.5 metrics. |
| A.2 local repair | `experiments/try5A/try5A_2/D1/` | Round contracts, lineage, rollback record and per-round collision summaries. |
| Co-guided pilot | `experiments/try5A/try5A_2/mechanism_validation/` | Joint visual/deterministic repair contracts and metrics. |

## Reproduction entry points

Run all commands with `.venv/Scripts/python.exe` from the repository root.

- Attachment baseline: `experiments/try5A/scripts/materialize_d0_physicalized.py`
- Attachment validation: `experiments/try5A/scripts/run_d0p_attachment_validation.py`
- D1 local repair compiler: `experiments/try5A/scripts/materialize_d1_round.py`
- D1 exact evaluator: `experiments/try5A/scripts/run_d1_round_evaluation.py`
- Co-guided repair pilot: `experiments/try5A/scripts/materialize_co_guided_candidate.py`

Do not commit generated geometry. Each experiment-local `.gitignore` identifies
regenerable heavy artifacts. The Git history preserves frozen experimental states:
`f2e83ae` (Try5-A), `2756e1e` (Try5-A.1), `c1c7d05` (attachment closure),
`74d0026` (D1 loop), and `9ed76d8` (co-guided pilot).
