# Try-5A.4 final report

Status: **PARTIAL — protocol completion gates remain open**

## Answer-first conclusion

The run establishes useful pilot-local evidence: separate parent/child CAD objects,
strict own-body attachment, sampled relative transforms, and exact B-Rep collision
improvement from M0 to M2. It does **not** complete every Try-5A.4 goal. The current
worker rotates child geometry about a local Z axis while the selected URDF axes are
Y; it does not compute the full URDF FK/world transform or EE pose. The cross-joint
geometry also lacks a pin/bearing/guide relation that physically constrains the
child to the intended DOF. Consequently K3 is not yet proven.

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

M1 is the first condition with non-zero collision-valid sampled intervals in the
pilot-local evaluator; M2 gives every pilot a complete sampled requested range in
that evaluator. Parent/child remain two top-level CAD objects and the
forbidden-fusion count is zero. These facts do not by themselves establish a
mechanically constrained joint or full URDF-FK correctness.

## Mechanical and dataflow audit

All M1/M2 parent and child carriers are fused only into their owning link rigid
group. Across each joint, parent and child are never Boolean-fused. The current
audit records zero axis/center error from copied contract values, but does not
independently verify CAD-axis/world-FK alignment; those gates remain open. FreeCAD
exact B-Rep common/distance operations, not AABB, decide the local pair-collision
result. Every generated feature carries mechanical role, owning rigid group,
knowledge/design provenance, and CAD strategy, but A.4 did not run a new
adversarial meaningless-geometry negative control.

The three counterfactuals pass at a limited level: narrowing a joint limit changes
the sampled occupancy bbox; changing the family changes interface volume; changing
axial clearance changes CAD bounds and the local collision metric. However, the M2
CAD constructor does not read a computed swept-envelope artifact—the U-shaped body
is selected directly from the `M2` condition. Therefore the full
URDF-limits→sweep→M2-planner→CAD causal chain remains unproven.

## Repair and representation assessment

Each pilot record contains one `R2_BODY_REGION_REPLAN` (within the two-repair cap),
but the scope is assigned directly rather than selected through the existing Repair
Scope Arbiter. No R4 was executed and no interface family changed. The recorded
local before/after acceptance rate is 100%, with zero rollback/regression. No VLM
was used; all reported motion decisions are deterministic.

The result demonstrates local pose playback and local exact-collision validity, but
does not yet pass the protocol's full K1/K2/K3 hierarchy. K1 still needs full URDF
FK/world-frame and EE-pose verification; K2 needs that corrected motion plus nearby
and nonadjacent-link collision coverage; K3 additionally needs mechanically
constraining pin/bearing/guide geometry rather than a clearance-separated boss.

## Remaining answers and limitations

- Motion playback exists for all pilots and conditions; M2 GIFs and exact-collision contact sheets are indexed in `motion_playback_manifest.json`.
- M2 changes the parent CAD load path and eliminates sampled M1 collisions, but the computed swept artifact is not a forward input to that construction.
- No sampled M2 collision remains in these pilots. Unmodeled bearing details, tolerances, fasteners, and full-robot neighbor interactions remain outside the claim.
- Knowledge now contributes construction and verification fields to the contract/IR, but family-specific mechanically constraining topology and causal motion benefit remain only partially demonstrated.
- FreeCAD is not the main bottleneck: all formal CAD builds and exact evaluations complete. The largest remaining bottleneck is scaling joint-local swept-corridor planning to the full robot while preserving morphology and accounting for all neighboring links.
- Extension to all Robot A physical joints is warranted, but should be a coarse whole-robot motion reconstruction stage before Try-5B. The pilot evidence supports that extension; it does not yet justify fine-detail Try-5B.
- Frozen A2 geometry metrics are reported only as auxiliary historical context; A.4 does not tune on GT or trade motion for IoU.

## Reproducibility

Run `./.venv/Scripts/python.exe experiments/try5A/scripts/run_try5a4.py`. The manifest freezes all inputs, hashes, samples, backend, and evaluator. Heavy FCStd/STEP/STL and individual frames live under ignored `experiments/try5A/artifacts/try5a4/`; tracked manifests preserve their hashes.

## Protocol questions 1–35

The answers below distinguish measured pilot evidence from unresolved protocol
requirements.

1. **Which three pilots were selected, and why?** J01 was selected from the real
   `shoulder_housing → upper_arm_link` transition; J02 from
   `upper_arm_link → forearm_link`; and J03 from
   `forearm_link → wrist_gripper_body`. The role-based selector records the reasons
   in `pilot_selection.json`.
2. **What are their URDF types, axes, and limits?** All are `revolute`. J01 uses
   axis `[0,1,0]`, limits `[-1.937315, 1.867502]` rad; J02 uses `[0,1,0]`,
   `[-1.605703, 2.111848]`; J03 uses `[0,1,0]`,
   `[-2.146755, 1.745329]`. These are local URDF joint-frame values.
3. **What families did K0/K1 choose?** J01: `fork_pin_interface →
   fork_pin_interface`; J02: `fork_pin_interface → fork_pin_interface`; J03:
   `coaxial_rotary_interface → coaxial_rotary_interface`. Thus the selected pilots
   have no K0/K1 family change; M0 freezes the recorded K1 labels.
4. **What motion rules were added to each family?** The rotary families add
   URDF-axis rotation, five constrained DOFs, parent/child side ownership,
   non-fusion, radial/axial/swept clearances, construction logic, and exact-sweep
   verification. `fork_pin_interface` specializes these as fork arms plus a child
   boss; `coaxial_rotary_interface` as paired bearing supports plus inner rotor;
   `nested_rotary_housing` as outer/inner envelopes with annular clearance.
   `rail_slider_interface` adds axial translation, keyed carriage/rail ownership,
   and a travel corridor. `flange_interface` and `planar_mount_interface` constrain
   all six relative DOFs for fixed joints. `end_tool_interface` remains a virtual
   frame with no child solid. The full rules are in the upgraded knowledge JSON.
5. **What are M0/M1/M2?** M0 is a reconstructed K1-style static/floating-carrier
   baseline; M1 adds owning rigid groups, attachments, non-fusion, and explicit
   clearance without swept-body replanning; M2 changes the parent body to a
   U-shaped corridor-avoiding form. Important limitation: M0 is not a direct replay
   of the original K1 CAD, and M2 is condition-driven rather than generated by
   reading the computed swept envelope.
6. **Parent Attachment Rate?** `0% → 100% → 100%` for M0/M1/M2.
7. **Child Attachment Rate?** `0% → 100% → 100%`.
8. **BICR?** `0% → 100% → 100%` in the new pilot-local attachment evaluator.
9. **Any floating interfaces?** Six interface sides in M0; zero in M1/M2. Across
   the joint, however, the child boss has clearance but no modeled bearing/pin
   constraint, so mechanical support of the allowed DOF remains incomplete.
10. **Any accidental parent-child fuse?** No Boolean parent-child fuse was created.
11. **Is Forbidden Fusion Count zero?** Yes, zero in all three conditions.
12. **Are each joint's rigid groups correct?** Top-level ownership and within-link
   connected-solid checks pass for M1/M2. Full kinematic rigid-group correctness in
   the URDF world frame is not yet directly evaluated.
13. **Does CAD retain independent parent/child rigid bodies?** Yes: two FreeCAD
   top-level objects are exported per pilot/condition. This proves separation, not
   a physically constraining bearing relationship.
14. **Can URDF FK drive CAD link movement?** Not fully proven. The worker consumes
   URDF limits but applies a local-Z rotation directly; it does not call the
   repository FK implementation, map the URDF Y axis into CAD, or transform the
   complete descendant rigid-link chain.
15. **Was motion playback generated?** Nine frames per joint/condition, nine
   contact sheets, and three M2 GIFs exist. They are schematic collision overlays,
   not renders of transformed FreeCAD B-Reps; the protocol's CAD-render playback
   requirement remains open.
16. **Collision-free pose rates?** M0 `0%`, M1 `85.19%`, M2 `100%`, over 27 sampled
   poses per condition in the pilot-local exact B-Rep evaluator.
17. **JR3?** Numerically `0%`, `85.19%`, and `100%`. The M2 value is provisional
   because axis/FK, mechanical constraint, neighboring-link, and EE gates are not
   included in its denominator.
18. **Which joint first obtained a nonzero interval?** All three have nonzero M1
   intervals. The earlier summary's “J01 first” reflects row order, not an
   experimental temporal distinction.
19. **Any full requested range collision-free?** J01/J02/J03 all pass all nine M2
   samples in the local pair evaluator. This is not a continuous-range proof or a
   whole-robot collision-free claim.
20. **Did swept clearance truly affect CAD?** CAD differs between M1 and M2 and
   collision improves, but direct artifact consumption is missing: the computed
   envelope is produced after construction and is not an input to the M2 CAD
   planner. This requirement is **not completed**.
21. **Did collision improve from M1 to M2?** Yes locally: events `4 → 0`, mean
   collision-free pose rate `85.19% → 100%`, and sampled collision volume becomes
   zero.
22. **Which collisions remain unresolved?** None among the sampled local
   parent/child pairs. Nearby/nonadjacent robot links, expected contact semantics,
   continuous inter-sample collisions, full descendant geometry, and EE collisions
   were not evaluated and remain unresolved.
23. **Which joints need R0–R4?** The result records R2 for J01/J02/J03. The choice
   is hard-coded in the A.4 driver rather than produced by the existing Repair
   Scope Arbiter; formal arbiter integration is **not completed**.
24. **Was R4 actually executed?** No.
25. **Did R4 change the interface family?** No; R4 was not run.
26. **Did meaningless patch geometry recur?** No generated A.4 feature lacks the
   required provenance fields, but no new adversarial geometric negative control
   was executed.
27. **Was the Mechanical Meaningfulness Gate effective?** Partially. It enforces
   required metadata fields, while deeper verification that geometry performs its
   declared mechanical role is not yet implemented.
28. **Was VLM limited to plausibility/root-cause and not motion judging?** No VLM
   was used in A.4. All reported motion decisions are deterministic, so VLM did not
   act as judge; VLM-assisted diagnosis was also not exercised.
29. **Did knowledge help motion realization beyond names?** Partially. Knowledge
   fields reach contracts/IR and a family counterfactual changes interface volume,
   but the current builder does not yet realize sufficiently distinct,
   mechanically constraining family topologies or show that knowledge caused the
   M1→M2 motion improvement.
30. **Which K level is reached?** Only pilot-local pose playback and exact pair
   collision evidence are established. Full K1 awaits correct URDF FK/axis/EE
   validation; therefore full K2 and mechanically realized K3 cannot be claimed.
31. **Is FreeCAD still not the main bottleneck?** Correct. All nine base CAD builds
   and exact B-Rep evaluations execute; the missing work is primarily method and
   evaluator integration.
32. **What is the largest bottleneck?** Converting the knowledge contract into a
   physically constraining joint, then driving complete link geometry with actual
   URDF FK while feeding computed swept envelopes forward into body planning.
33. **Should this be expanded to all Robot A joints?** Not yet. First close the
   pilot hard gaps and rerun the three pilots; only then scale.
34. **Ready for whole-robot coarse motion reconstruction?** No. The pilot provides
   reusable scaffolding but lacks validated world-FK, descendant/neighbor
   collision, and causal swept-body planning.
35. **Ready for Try-5B?** No. Try-5A.4 must first achieve verified K3 on the pilot
   joints and then demonstrate the coarse whole-robot motion stage.

## Revised completion decision

The original numeric run is reproducible and useful, but the Try-5A.4 protocol is
**not fully complete**. Completed portions include knowledge/schema enrichment,
pilot selection, CAD object separation, strict own-body attachment, exact local
B-Rep sampling, artifacts, and limited counterfactuals. Open hard gates are listed
in `protocol_gap_audit.json` and reflected by `validation.json = FAIL`.
