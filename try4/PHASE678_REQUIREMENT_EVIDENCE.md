# Try-4 Phase 6–8 requirement-to-evidence checklist

Scope: continuously develop Structured Review, Selective Repair and the DEV_A/B
T2 run, with a two-part pilot gate before the formal 12-part matrix.

- [x] Phase 5 evaluator protocol, thresholds and T1 artifacts remain byte-identical.
- [x] Review and Repair Skills plus Repair Contract schema pass validation.
- [x] Review input records reference GT renders, generated renders, semantics, LOD,
  Feature Graph/tree, deterministic metrics, regional discrepancies and history.
- [x] Contracts use only the frozen finite action vocabulary and state WHAT/WHERE,
  numeric HOW MUCH, protected features and do-not-change constraints.
- [x] GT STEP/B-Rep, exact GT feature dimensions/sketches and feature tree never
  enter the repair executor or repair decision artifact.
- [x] Scheduler implements PASS/FROZEN, LOCAL_REPAIR, REPLAN, regression rollback,
  stagnation escalation and UNRESOLVED after at most three repair rounds.
- [x] R02_P02 LOCAL_REPAIR and R02_P05 REPLAN pilots prove executable contracts,
  independent round artifacts, reevaluation and protection checks.
- [x] Formal T2 controls are frozen after pilot and before the 12-part matrix. The post-review correction is versioned and the superseded numeric-only attempt is retained.
- [x] Every DEV_A/B part remains in the denominator; scheduler processes only
  actionable parts and stops immediately on PASS/FROZEN or UNRESOLVED.
- [x] Each executed round retains contract, repair log, Feature Graph, CAD IR,
  FCStd/STEP/STL, renders, feature tree, metrics and PartState.
- [x] Repair metrics include trigger/success/replan/regression/unresolved rates,
  rounds, early stopping, frozen preservation, metric deltas and calls saved.
- [x] Required Robot-B free-form versus structured repair ablation is preserved as
  a separate controlled result or explicitly marked incomplete with evidence.
- [x] No Robot C run occurs; Phase 8 report stops before protocol/transfer freeze.
- [x] Validation, method hashes and task-only local Git commit pass.
