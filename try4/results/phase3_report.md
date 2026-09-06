# Try-4 Phase 3 report — T0 direct baseline

Status: Phase 3 execution complete for DEV_A; awaiting user review before Phase 4.
No T1/T2 or TRANSFER generation has started.

## Execution condition

The user replaced the slow external Codex CLI route during execution. The three
completed CLI outputs, one interrupted request and one unstarted Part are retained
as `T0_CLI_partial` and excluded from the active condition. `T0_INTERACTIVE`
contains one current-agent artifact for each of the five DEV_A Macro-Parts.

This execution mode is consistent across the five active outputs, but context
isolation is false: the current conversation inspected offline annotations,
repository material and prior results. T0_INTERACTIVE is a development baseline,
not a confirmatory or controlled model comparison. See
`../AMENDMENT_T0_INTERACTIVE.md` and `t0_cli_partial_status.csv`.

## Coverage and engineering validity

| Item | Result |
| --- | ---: |
| PartInputPackets consumed | 5/5 |
| Structured agent artifacts | 5/5 |
| CAD-IR Plan Gate | 5/5 |
| FreeCAD builds after recorded implementation replay | 5/5 |
| FCStd/STEP/STL exports | 5/5 each |
| Four-view render sets | 5/5 |
| FCStd reopen/recompute | 5/5 |
| ±5% parameter edit and restore | 5/5 |
| Silent fallbacks | 0 |
| Planned features | 14 |
| Explicitly unimplemented features | 4 (one critical) |
| Final bodies | 12 |
| CAD operations | 39 |

Native execution records 14 Part::Box, 3 Part::Loft, 9 Part::Cylinder,
8 sequential Fuse and 5 Cut operations. Counts are diagnostics, not quality.
Plan-Gate PASS means schema/IR/evidence/reference integrity; it does not mean LOD
or reconstruction quality passed. Phase 5 Quality Gates are not implemented yet.

The first FreeCAD pass reached model/export but failed the editability test because
the executor resolved a primitive ID to its downstream Fuse object. All five
outputs/logs were archived, the generic object lookup was fixed, and identical
frozen IR was replayed once. No geometry decision changed.

## Visual result

T0 is intentionally coarse. It preserves useful semantic structure: separate
upper-arm/forearm plates, fork openings, a proximal pivot, separate gripper jaws,
and the working grip gap. It does not recover the reference exterior well.
Scalloped/tapered base structure, inset cover, side slots, stepped plate outlines,
curved transitions, bracket profiles and gripper linkage detail remain absent or
poorly proportioned. R01_P02 and R01_P04 show the largest silhouette/layout gap.

Four features are explicitly UNIMPLEMENTED: shoulder top inset, upper-arm slots,
forearm slot and gripper-bracket side slot. The latter is critical. Their absence
is preserved rather than treated as a successful hidden fallback. Detailed visual
notes are in `t0_manual_review.md`; sheets are under `t0_contact_sheets/`.

## Current interpretation

Phase 3 establishes a runnable T0 development baseline and proves basic
multi-body FreeCAD generation/editability. It does not yet provide IoU, Chamfer,
HD95, MFR/precision or Quality Gate outcomes; those belong to Phase 5 after T1.
The active T0 context limitation means later causal T0→T1 claims require either
the same current-agent mode for T1 with careful disclosure or a new consistently
isolated experiment run.

Next authorized phase after user review is Phase 4: implement the shared Visual,
Semantic/Mechanical, Detail and CAD Planning Skills, then generate T1 once on
DEV_A/B without repair. No T0 artifact will be repaired in place.

