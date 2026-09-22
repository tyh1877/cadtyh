# Try-5B.1-A1 Frozen Scaffold Preservation Ablation

This stage runs the six formal **development** candidates and stops before the
32-case formal holdout. The earlier mechanical-geometry-protection name and
multi-flag intervention are superseded.

- [ ] Freeze a tracked protocol in which the only condition difference is `preserve_frozen_scaffold`.
- [ ] Keep protected interface cuts and distal clearance enabled identically, and auto attachment closure disabled identically, in S1/S0.
- [ ] Create `formal_holdout_lock.json` before generation with case IDs/hash, protocol hash, committed implementation, timestamp, and `accessed=false`.
- [ ] Enforce that the development runner cannot deserialize or evaluate formal holdout configurations.
- [ ] Freeze commit, protocol, images, URDF, F2 schema, VisualEvidencePack, Interface Contract, seed, evaluator settings, configuration set, and joint sweeps.
- [ ] Pass a canonical parity audit with no difference outside `preserve_frozen_scaffold`.
- [ ] Execute exactly six one-shot generation runs: L03/L04/L07 × S1/S0, using original F2 and no repair/retry/controller.
- [ ] Freeze every generated candidate and retain build/export/reopen failures in the denominator.
- [ ] Run one shared independent Exact evaluator over the same 96 development configurations and relevant sweeps for each paired link.
- [ ] Compute primary BICR, attachment validity, and connected-solid count from actual FreeCAD artifacts.
- [ ] Compute secondary JR3, GCFR, Exact collision events/volume, and failed configuration IDs without threshold tuning.
- [ ] Compute final-link geometry metrics and retain body-only metrics only as paired diagnostic deltas.
- [ ] Save operation-level protection traces proving the effective condition difference is scaffold fusion only.
- [ ] Generate the paired main table, per-link deltas, mean, median, and complete failure accounting.
- [ ] Separate final report statements into `FACTS`, `INTERPRETATION`, and `NOT_SUPPORTED`.
- [ ] Run an independent result audit; stop without accessing formal holdout, Direct VLM baseline, or Metric Grounding.
