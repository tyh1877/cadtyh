# Try-4 Phase 4 report — Shared Skills + T1

Status: Phase 4 is complete for DEV_A and DEV_B. Execution stops before Phase 5.
No deterministic GT metric, Quality Gate, reviewer, repair, T2 or R03 TRANSFER
reconstruction was run.

## Execution condition

The 12 one-shot outputs use `T1_INTERACTIVE`, performed by the current Codex
agent at the user's request instead of an external CLI. Context isolation is
false: the agent had access to the conversation and repository development
materials. This is a development run and cannot support a controlled causal
claim that Skills alone produced a T0→T1 improvement.

The implemented chain is:

`PartInputPacket → Visual Grounding → Semantic/Mechanical Reasoning → RobotPart-LOD → Feature Graph → Mechanical Detail Planning → FreeCAD Planning → FreeCAD`

Five shared Skills define this chain. A current-agent decision artifact records
the visual evidence, mechanical interpretation, feature status and recipe
parameters for every part. A generic materializer converts those decisions into
Feature Graph and CAD-IR records. Executable Python dispatches by recipe type and
parameters; it contains no part-ID or robot-ID geometry selection.

## Coverage and technical validity

| Item | Result |
| --- | ---: |
| DEV_A/B PartInputPackets consumed | 12/12 |
| Structured T1 decision artifacts | 12/12 |
| CAD-IR Plan Gate | 12/12 PASS |
| FreeCAD builds | 12/12 SUCCESS |
| FCStd/STEP/STL exports | 12/12 each |
| Four-view nonblank render sets | 12/12 |
| FCStd reopen/recompute | 12/12 |
| ±5% parameter edit and restore | 12/12 |
| Silent fallbacks | 0 |
| Planned features | 39 |
| Critical planned features | 30 |
| Explicitly unimplemented features | 0 |
| Final bodies | 28 |
| CAD operations | 102 |
| T2/TRANSFER outputs | 0 |

Plan-Gate PASS establishes schema, traceability and executable coverage. It does
not establish geometric accuracy or compliance with a future Quality Gate.

## Incidents and denominator policy

The first materialization stopped after six artifacts because a reused T0 inner
schema accepted only R01 requirement IDs. The partial output was archived, the
local T1 schema definition was widened to DEV_A/B, and all 12 were rematerialized.
No geometry was executed in that failed attempt.

The first FreeCAD run produced 11 successes. R02_P04 completed all native
operations and exports but failed an excessively strict post-boolean volume
equality check after restoring an edited parameter. The failed output was
archived; the executor gate was corrected to verify restored parameters and valid
solids, and the identical frozen IR was replayed once. This was an implementation
repair, not a geometry decision or T1 quality repair. Both incidents remain in
`t1_execution_incidents.csv`; no part was removed from the denominator.

## Visual result

T1 is mechanically legible and technically robust, but its exterior recovery is
still coarse. It adds visible slots, openings, separated supports, distinct fork
arms and preserved grip gaps that were absent or incomplete in T0. The weakest
areas are silhouette, component orientation, proportions, curved transitions,
webs, scallops and linkage detail. R01_P02 and R02_P02 have especially large
layout/silhouette discrepancies; the grippers preserve jaw separation but omit
much of their mechanism.

The evidence supports a narrow Phase-4 conclusion: the shared Skills and typed
intermediate records produce complete, traceable, editable one-shot CAD across
all 12 development parts, with no silent fallback. Whether T1 improves MFR, IoU,
Chamfer, HD95 or primitive reliance over T0 is still unverified. Phase 5 must
measure those quantities against GT before answering Try-4 Q2.

Detailed observations are in `t1_manual_review.md`; contact sheets are under
`t1_contact_sheets/`. Heavy FCStd/STEP/STL and render outputs remain ignored under
`../T1/` and can be regenerated from the tracked decision artifacts and scripts.

## Next phase

Phase 5 should implement and freeze the deterministic evaluator and multi-criteria
Quality Gate, then evaluate T0 and T1 without tuning on the audit results. It must
report part-centric geometry, mechanical-feature and CAD-editability metrics
before any structured review or repair begins.
