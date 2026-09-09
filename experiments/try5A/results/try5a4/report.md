# Try-5A.4 final report

Status: **COMPLETE**

## Answer-first conclusion

The three Robot A pilots now have separately modeled parent/child rigid groups, strict own-body attachment, URDF-driven relative motion, and exact-collision-valid sampled ranges under M2. This is pilot-level K3 evidence, not a whole-robot claim.

## Pilot selection and frozen motion

| Pilot | Joint | Type | Parent → child | URDF axis | Limits (rad) | K1 family |
|---|---|---|---|---|---|---|
| shoulder | J01 | revolute | L01 → L02 | `[0.0, 1.0, 0.0]` | -1.937315…1.867502 | fork_pin_interface |
| elbow | J02 | revolute | L02 → L03 | `[0.0, 1.0, 0.0]` | -1.605703…2.111848 | fork_pin_interface |
| wrist_gripper_neighborhood | J03 | revolute | L03 → L04 | `[0.0, 1.0, 0.0]` | -2.146755…1.745329 | coaxial_rotary_interface |

The role-transition selector chose J01 (shoulder housing to upper arm), J02 (upper arm to forearm/elbow), and J03 (forearm to wrist/gripper body). No joint ID was invented or hard-coded as an experimental answer.

## M0 / M1 / M2 results

| Condition | Parent attach | Child attach | BICR | Floating interfaces | Forbidden fusions | Collision-free poses | JR3 |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 0.0% | 0.0% | 0.0% | 6 | 0 | 0.0% | 0.0% |
| M1 | 100.0% | 100.0% | 100.0% | 0 | 0 | 85.2% | 85.2% |
| M2 | 100.0% | 100.0% | 100.0% | 0 | 0 | 100.0% | 100.0% |

M0 freezes the current K1 family decisions but preserves the observed A.3 defect: named carriers are floating and overlapping static geometry. M1 expands the same families into separate parent/child rigid groups with strict own-body attachment and an explicit revolute corridor, without swept-body replanning. M2 applies one bounded R2 body-region repair per pilot, moving the parent load path outside the generated swept corridor.

| Joint | Condition | Collision-free poses | JR3 | Max collision-free interval (rad) | First collision (rad) | Swept collision volume (mm³-samples) | Min clearance (mm) |
|---|---|---:|---:|---|---:|---:|---:|
| J01 | M0 | 0.0% | 0.0% | none | -1.937315 | 31838.020 | 0.000 |
| J01 | M1 | 77.8% | 77.8% | [-1.461713248545251, 1.3919000784654776] | -1.937315 | 2404.383 | 0.000 |
| J01 | M2 | 100.0% | 100.0% | [-1.9373154697137058, 1.8675022996339325] | — | 0.000 | 1.000 |
| J02 | M0 | 0.0% | 0.0% | none | -1.605703 | 31838.020 | 0.000 |
| J02 | M1 | 88.9% | 88.9% | [-1.6057029118347832, 1.6471544815696486] | 2.111848 | 3807.846 | 0.000 |
| J02 | M2 | 100.0% | 100.0% | [-1.6057029118347832, 2.111848394913139] | — | 0.000 | 1.000 |
| J03 | M0 | 0.0% | 0.0% | none | -2.146755 | 31838.020 | 0.000 |
| J03 | M1 | 88.9% | 88.9% | [-1.6602444509596062, 1.7453292519943298] | -2.146755 | 4082.881 | 0.000 |
| J03 | M2 | 100.0% | 100.0% | [-2.1467549799530254, 1.7453292519943298] | — | 0.000 | 1.000 |

M1 is the first condition with non-zero mechanically valid motion intervals; M2 gives every pilot a complete sampled requested range. Parent/child remain two top-level CAD objects for every condition, and the forbidden-fusion count is zero. M0 still fails K3 because its carriers are floating, even though FK can move its named pieces.

## Mechanical and dataflow audit

All M1/M2 parent and child carriers are fused only into their owning link rigid group. Across each joint, parent and child are never Boolean-fused. Axis and center errors are 0 by direct consumption of the frozen URDF joint frame; FreeCAD exact B-Rep common/distance operations, not AABB, decide collision validity. Every generated feature carries mechanical role, owning rigid group, knowledge/design provenance, and CAD strategy; the meaningless-gap-box sentinel remains rejected.

The three counterfactuals pass: narrowing a joint limit changes swept occupancy; changing the knowledge family changes realized interface volume/strategy; and changing axial clearance changes CAD plus the exact motion metric. This proves both URDF→sweep→M2 and knowledge→contract→CAD consumption paths.

## Repair and representation assessment

Each pilot used one R2_BODY_REGION_REPLAN (within the two-repair cap). No R4 was executed because the frozen K1 family remained mechanically plausible after deterministic motion evaluation; therefore no interface family changed. Repair success is 100%, rollback/regression are 0%, and no meaningless geometry patch was accepted. VLM is not used as a motion judge; all final decisions are deterministic.

The result reaches K1 (pose-driven), K2 (collision-valid over all sampled requested poses in M2), and pilot-level K3 (mechanically realized) for J01/J02/J03. It does not yet establish whole-robot K3 because non-pilot joints were not rebuilt or swept in this protocol.

## Remaining answers and limitations

- Motion playback exists for all pilots and conditions; M2 GIFs and exact-collision contact sheets are indexed in `motion_playback_manifest.json`.
- Swept clearance materially changes the M2 parent CAD load path and eliminates sampled M1 motion-induced collisions.
- No sampled M2 collision remains in these pilots. Unmodeled bearing details, tolerances, fasteners, and full-robot neighbor interactions remain outside the claim.
- Knowledge now contributes construction and verification rules, not only a family label. It provides side ownership, non-fusion, DOF, clearance, and CAD strategy consumed by the contract/IR.
- FreeCAD is not the main bottleneck: all formal CAD builds and exact evaluations complete. The largest remaining bottleneck is scaling joint-local swept-corridor planning to the full robot while preserving morphology and accounting for all neighboring links.
- Extension to all Robot A physical joints is warranted, but should be a coarse whole-robot motion reconstruction stage before Try-5B. The pilot evidence supports that extension; it does not yet justify fine-detail Try-5B.
- Frozen A2 geometry metrics are reported only as auxiliary historical context; A.4 does not tune on GT or trade motion for IoU.

## Reproducibility

Run `./.venv/Scripts/python.exe experiments/try5A/scripts/run_try5a4.py`. The manifest freezes all inputs, hashes, samples, backend, and evaluator. Heavy FCStd/STEP/STL and individual frames live under ignored `experiments/try5A/artifacts/try5a4/`; tracked manifests preserve their hashes.
