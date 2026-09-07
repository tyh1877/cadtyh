# Pre-Phase-9 repair v2 pilot report

Status: four fresh candidates were generated from T1 Round 0 with a generic CAD
vocabulary v2. The pilot gate failed, so the formal 12-part rerun and Robot C were
not started.

| Part | Phase-5 numeric gate | IoU | nChamfer | nHD95 | Section-area MAE | Max regional nChamfer |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| R01_P00 | PASS | 0.5823 | 0.02574 | 0.1317 | 0.1733 | 0.0420 |
| R02_P02 | PASS | 0.4037 | 0.02501 | 0.1349 | 0.3167 | 0.0307 |
| R02_P05 | LOCAL_REPAIR | 0.1550 | 0.12722 | 0.3270 | 0.2716 | 0.1376 |
| R02_P06 | LOCAL_REPAIR | 0.2196 | 0.06525 | 0.2865 | 0.3994 | 0.2526 |

All four produced valid native FCStd/STEP/STL, nonblank four-view renders, zero
silent fallback, successful reopen/recompute and ±5% edit/restore evidence.

Relative to T1, all four improve IoU. R01_P00 improves all main metrics strongly.
R02_P02 corrects the major web/fork topology and passes the old numeric gate,
although HD95 is slightly worse than T1 and visible detail remains incomplete.
R02_P05 improves substantially but still fails every principal distance/overlap
criterion. R02_P06 improves IoU only modestly and its regional/section diagnostics
remain worst among the pilot.

The new section and regional metrics are useful diagnostics: they expose the
gripper mismatch that a global Chamfer alone understates. They are not yet frozen
as Gate thresholds because the four-part development pilot is too small.

The next repair should focus on two missing generic families before another
pilot: curved plate sweep/profile with terminal notches, and articulated gripper
subgraph with carriage/rail/link/pivot constraints. The base and single-web fork
families can be retained and refined. No formal admission claim is made.
