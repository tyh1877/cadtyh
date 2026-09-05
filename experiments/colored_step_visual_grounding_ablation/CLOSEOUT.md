# Existing-run closeout audit (2026-09-05)

Status: **blocked for frozen-protocol scientific completion**. The historical
matrix has finished, and offline archival/verification is performed by
`scripts/finalize_existing_results.py`. This is a NO-GO for promotion to a
confirmatory experiment, not a claim that coloring has no benefit.

## Scope and evidence map

The source protocol is preserved unchanged. This document records deviations
found after execution; it is not a retroactive protocol amendment.

| Requirement | Evidence / command | Audit interpretation |
| --- | --- | --- |
| Five original STEP sources | `native_step5_v1.csv`, `results/source_provenance.csv` | Source hashes checked against the imported manifests; download URLs, archive hashes and dates retained. |
| Geometry/render parity | `scripts/audit_native_step_assets.py`, `results/asset_parity_*.csv` | All five pass; all 30 A0/A1 silhouette comparisons have IoU 1; A1/A2 images are byte-identical. Camera matrices were not serialized, so strict matrix parity is not independently proven. |
| Native B-Rep export/reopen | `results/native_step_asset_summary.csv`, local `artifacts/native_step5/*/asset_result.json` | Source/reopened solid counts and leaf counts agree. STEP color entities exist. Per-object reopened color values were not recorded; color-entity counts alone do not prove color identity. |
| Full E1 matrix | `results/closeout_e1_components.csv`, `results/closeout_failures.csv` | 45 case-condition cells, 43 successes, 2 explicit failures; 522 component rows including all failures. |
| Recompute historical E1 | `scripts/finalize_existing_results.py` | Re-evaluates saved scans against the original masks and compares every aggregate to the historical CSV without changing the evaluator. |
| Real multimodal/model evidence | local `runs/*/*/*/api_manifest.json`, E1/E2 call implementations | All 57 successful calls report six images and `glm-5.3-flash`; code supplies inline image data. Historical request payload hashes/provider snapshots are absent. |
| E2 matrix and schema | `results/e2_case_condition_summary.csv`, closeout script | 14 schema-valid plans, 1 upstream failure, all 15 cells retained; original metrics recomputed. |
| Paired plans | `results/closeout_e2_component_plans.csv` | 174 rows paired through E1 Hungarian matching, with roles, geometry families and feature/joint counts. Matching does not establish correct physical identity. |
| Resource accounting | `results/closeout_e1_aggregate.csv`, `results/closeout_audit.json` | Successful call tokens/time retained. Failed E1 calls lack usage/time; zero entries cannot be interpreted as zero billing or latency. |
| Contact sheets | local `results/e1_contact_sheets/replicate_*/*/*.png` | Regenerated from 43 successful scans; ignored in Git. |
| Reproducibility archive | `results/closeout_evidence_inventory.csv` | SHA-256 inventory of local source-derived assets, runs, scripts, prompt and schema. This is a closeout snapshot, not proof of a pre-run freeze. |

## Recorded progress and failure accounting

- E1 replicate 01: 14/15 success. `step_rx150/A2_color_legend` timed out.
- E1 replicate 02: 15/15 success.
- E1 replicate 03: 14/15 success. `step_wx250s/A2_color_legend` returned
  provider error 429/code 1113 (insufficient balance/resources).
- E2 replicate 01: 14/15 success; RX150 A2 was not called because E1 failed.
- No experiment process was running at inspection. No model call is retried or
  replaced during closeout, and no new paid calls are made.

The actual cohort comprises **58 STEP leaf components per condition**
(7/9/24/8/10), representing 66 solids. It is not the old 63-link TrySet-5 cohort.
No authoritative STEP-component-to-URDF-link mapping exists in this experiment.

## Metric and protocol limitations

1. Masks are **isolated component projections**, obtained by hiding all other
   objects. They include occluded geometry and overlap. Thus target purity is
   an isolated-projection proxy, not visible target-pixel purity. The historical
   `wrong_link_rate` is `1 - mean_target_purity`, not a categorical wrong-link
   crop rate. Its threshold cannot substantiate the protocol's 30% reduction
   requirement. Historical column names and values remain preserved.
2. E1 uses maximum IoU across views and optimal Hungarian region/component
   matching. It measures optimistic component localization, not URDF link
   identification. A2 identity accuracy is separate; anonymous A0/A1 identities
   should not be compared as a task with equivalent identity cues.
3. There are no explicit proximal/distal joint-localization annotations, no
   extracted feature-crop evaluation, and no frozen joint-housing labels.
   Candidate counts and generated joint-region counts do not measure coverage
   or mechanical correctness. E2 complete-region rate uses predicted E1 regions,
   not all GT components (e.g. VX300s A0 has 13 regions for 24 components).
4. E2 traceability checks only whether a region ID and view name exist in the
   permitted sets. It does not establish that the cited image supports the
   claim. Empty reference lists are allowed by the schema. Feature correctness
   remains **pending** without a blinded, frozen expert annotation set.
5. Condition-specific color instructions and expected component count are
   supplied to E1; the latter is additional oracle information. Only A2 receives
   the identity legend. Prompt parity is limited to the common contract plus
   these explicit condition cues.
6. No pre-repeat freeze record or approved amendment is present. Replicates
   02/03 are retained as exploratory diagnostics; they cannot repair a failed
   feasibility gate or count as independent held-out cases. There is no holdout
   in this five-case diagnostic, and no metric is tuned during closeout.

## Decision

Use `results/closeout_e1_aggregate.csv` for both equal-case macro and
component-weighted micro averages, and `results/closeout_e1_paired.csv` for
case-paired changes, including failed cases. Do not pool historical mesh results.

Even if the historical contamination proxy were provisionally used, the
feasibility replicate does not satisfy the full promotion rule. In the E2
failure-inclusive case macro, unsupported-reference rate rises from 0 to 0.20,
exceeding the permitted +0.05. Conditional on successful plans, all recorded
reference IDs/views are valid, which says nothing about semantic correctness.
The correct outcome is **NO-GO for confirmatory promotion; suggestive oracle
localization results only, no demonstrated improvement in MEP correctness**.

In replicate 01, the failure-inclusive, equal-case A2-minus-A0 IoU change is
**+0.142394**, with improvement on 4/5 cases. The historical contamination proxy
decreases by **16.3569%**, below 30% even before accounting for its definition
mismatch. Recorded token totals are **477,739 for E1** and **216,854 for E2**;
the E1 figure is a lower bound because failed calls have no usage record.

| E1 replicate | A0 macro IoU | A1 macro IoU | A2 macro IoU | A2 minus A0 |
| --- | ---: | ---: | ---: | ---: |
| 01 (feasibility) | 0.3361 | 0.5314 | 0.4785 | +0.1424 |
| 02 (exploratory) | 0.4224 | 0.4801 | 0.4421 | +0.0198 |
| 03 (exploratory) | 0.3802 | 0.4832 | 0.4911 | +0.1109 |

All entries retain five cases, with IoU zero for API failures. A2 does not
consistently outperform A1. Repeated calls on the same five related assemblies
do not establish statistical generalization.

Completion of the original scientific gates requires a separately declared
development protocol, visible-occlusion-aware masks, an authoritative link/joint
mapping and frozen annotations, plus a new untouched holdout. Past predictions
must not be relabeled as a fresh confirmatory run. Further model execution also
requires provider resources if the recorded balance condition persists; adding
funds alone does not resolve the methodological gates.

## Reproduce this offline audit

Run from the repository root with the existing local evidence and source cache:

```powershell
.venv/Scripts/python.exe experiments/colored_step_visual_grounding_ablation/scripts/audit_native_step_assets.py
.venv/Scripts/python.exe experiments/colored_step_visual_grounding_ablation/scripts/finalize_existing_results.py
.venv/Scripts/python.exe -m compileall -q experiments/colored_step_visual_grounding_ablation/scripts
```

Source download provenance names `go_nogo1/scripts/download_trossen_step.py`;
asset generation uses `prepare_native_step_assets.py` and its FreeCAD helper.
Do not rerun historical runners in place: they overwrite run directories/tables.
The FreeCAD helper uses the CAD application's bundled runtime for its native
modules; experiment orchestration and offline validation use the root `.venv`.
No dependencies were added. STEP, FCStd, masks, raw generations and preview
images stay outside Git. The pre-existing root `.gitignore` edits are left
untouched; the experiment's own `.gitignore` independently excludes its assets.
