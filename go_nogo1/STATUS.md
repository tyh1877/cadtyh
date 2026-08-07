# Go/No-Go 1 — v5 prototype feasibility result

## Decision: GO (17/20 complete)

The screenshot-defined 20-case prototype passes. Seventeen cases satisfy mesh,
URDF, Mesh–URDF/multi-pose, deterministic evaluator, multimodal-input, and visual
review requirements. The frozen threshold is at least 15 complete cases.

## Gate evidence

| Criterion | Result | Required | Status |
|---|---:|---:|---|
| Complete cases | 17/20 (85%) | at least 15/20 | pass |
| Prototype manufacturers | 16 | descriptive | — |
| Aggregate mesh-reference readability | 161/162 (99.38%) | at least 90% | pass |
| Complete-case URDF parse and graph | 17/17 | 100% | pass |
| Complete-case multi-pose consistency | 17/17 | 100% | pass |
| Complete-case deterministic evaluator | 17/17 | 100% | pass |
| Complete-case multimodal bundle | 17/17 | 100% | pass |
| Six-view reviews completed | 20/20 | 20/20 | pass |

## Three retained failures

1. **Kinova Gen3:** one referenced `EndEffector_Link.STL` is empty; per-case
   reference readability is 88.9%, below 90%.
2. **Trossen PhantomX Pincher:** six-view review finds the visual geometry dominated
   by coarse box-like proxy solids.
3. **Unimation PUMA 560:** only 5/6 joint connection checks satisfy the conservative
   AABB-distance rule (83.3%, below 90%).

All three remain in the denominator. They were not replaced with easier cases.

## Parser defect found and repaired

The first visual run exposed exploded KUKA geometry. Root cause analysis found two
pipeline defects:

- ambiguous short `package://visual/...` URIs could resolve to a same-named mesh
  from another robot package;
- internal Collada scene-node transforms were discarded before applying URDF
  link/visual transforms.

The resolver now prioritizes the candidate sharing the deepest path prefix with the
current URDF and rejects unresolved ties. Collada scenes are flattened with their
node transforms. Inventory, entity features, Benchmark-80 selection, and the full
20-case prototype were rebuilt and rerun after the fix.

## What the result establishes

- A small public Mesh+URDF prototype can support deterministic geometry and
  kinematic evaluation.
- Six-view and Text/Image/Text+Image inputs can be generated consistently.
- The evaluation API responds correctly to identity and synthetic corruption cases.

It does **not** establish release licensing, evaluator correlation with human quality,
train/test leakage safety, production-scale performance, or Benchmark-80 readiness.

Machine-readable evidence is in `results/prototype_feasibility/summary.json` and
`case_audit.csv`; the executable audit is in
`notebooks/03_prototype_feasibility_audit.ipynb`.
