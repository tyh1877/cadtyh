# Visual Evidence Input Ablation Checklist

## Protocol and leakage

- [x] Experiment directory is separate from the formal Try-3 FreeCAD workflow.
- [x] A1 is explicitly marked as GT-derived oracle input, not formal planner
  input.
- [x] Frozen TrySet-5 cases are reused without replacement.
- [x] A1 colored full-assembly renders are generated for all 5 cases under
  ignored `artifacts/a1_colored/colored_renders/`.
- [x] A1 VLM scan preserves all cases in the denominator.

## Execution evidence

- [x] `results/a1_colored_case_summary.csv` records 5 attempted cases and 5
  successes.
- [x] `results/a1_colored_report.md` compares A0 and A1 coverage.
- [x] Contact sheets are generated for manual inspection.
- [x] Failures, if any, are explicit and not silently dropped. Current run has
  no case failures after handling no-visual helper links.

## Repository discipline

- [x] Heavy and GT-derived raw artifacts remain under ignored `runs/` or
  `artifacts/`.
- [x] Validation commands run with `.venv/Scripts/python.exe`.
- [x] Diff inspected before local commit.
- [x] Local Git commit created; no push.
