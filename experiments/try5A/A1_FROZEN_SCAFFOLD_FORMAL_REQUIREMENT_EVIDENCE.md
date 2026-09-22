# Try-5B.1-A1 Frozen Scaffold Preservation Ablation

This stage runs the six formal **development** candidates and stops before the
32-case formal holdout. The earlier mechanical-geometry-protection name and
multi-flag intervention are superseded.

- [x] Freeze a tracked protocol in which the only condition difference is `preserve_frozen_scaffold`.
- [x] Keep protected interface cuts and distal clearance enabled identically, and auto attachment closure disabled identically, in S1/S0.
- [x] Create `formal_holdout_lock.json` before generation with case IDs/hash, protocol hash, committed implementation, timestamp, and `accessed=false`.
- [x] Enforce that the development runner cannot deserialize or evaluate formal holdout configurations.
- [x] Freeze commit, protocol, images, URDF, F2 schema, VisualEvidencePack, Interface Contract, seed, evaluator settings, configuration set, and joint sweeps.
- [x] Pass a canonical parity audit with no difference outside `preserve_frozen_scaffold`.
- [x] Execute exactly six one-shot generation runs: L03/L04/L07 × S1/S0, using original F2 and no repair/retry/controller.
- [x] Freeze every generated candidate and retain build/export/reopen failures in the denominator.
- [x] Run one shared independent Exact evaluator over the same 96 development configurations and relevant sweeps for each paired link.
- [x] Compute primary BICR, attachment validity, and connected-solid count from actual FreeCAD artifacts.
- [x] Compute secondary JR3, GCFR, Exact collision events/volume, and failed configuration IDs without threshold tuning.
- [x] Compute final-link geometry metrics and retain body-only metrics only as paired diagnostic deltas.
- [x] Save operation-level protection traces proving the effective condition difference is scaffold fusion only.
- [x] Generate the paired main table, per-link deltas, mean, median, and complete failure accounting.
- [x] Separate final report statements into `FACTS`, `INTERPRETATION`, and `NOT_SUPPORTED`.
- [x] Run an independent result audit; stop without accessing formal holdout, Direct VLM baseline, or Metric Grounding.

Final state: `FORMAL_DEVELOPMENT_COMPLETE_HOLDOUT_UNACCESSED`; independent
validation `PASS`; formal holdout `accessed=false`, `evaluation_count=0`.
