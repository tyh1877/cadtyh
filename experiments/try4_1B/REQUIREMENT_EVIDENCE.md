# Try-4.1B requirement-to-evidence checklist

- [x] Scope is exactly R02_P04 and R02_P06; Robot C and Try-4.1C are absent.
- [x] B0 references frozen Try-4.1A A1 outputs without regeneration or tuning.
- [x] Rule/offline evaluator-only topology GT is frozen before B1. It is procedurally isolated; no independent human annotator was available.
- [x] Executable Shape-Family v1 schema and documentation define substructures, parameters, frames, connectivity, symmetry, gaps, strategies and invalid configurations.
- [x] B1 expands stepped housing and gripper into schema-valid executable substructures and Mechanical Feature Graph/CAD IR.
- [x] B1 generator consumes no independent topology GT or GT geometry/dimensions.
- [x] Shape-Family Gate validates topology support, required substructures, open spaces, symmetry and parameter completeness before FreeCAD.
- [x] B1 is generated once with the same backend/evaluator/render settings and no iterative repair.
- [x] Structure Realization Gate checks successful CAD realization of every declared substructure.
- [x] Both failed B1 cases receive exactly one B2; each records a family/graph/strategy change beyond parameter updates.
- [x] Protected B1 joint-boss or rail operations remain byte-equivalent in B2.
- [x] B0/B1/B2 geometry, independent topology, substructure and CAD metrics are complete.
- [x] Unified GT | B0 | B1 | B2 contact sheets and required final report exist.
- [x] Validation, determinism, hashes, denominator and task-only Git commit pass.
