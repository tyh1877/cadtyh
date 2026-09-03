# Visual Evidence Input Ablation: A1 Colored Link Render

## Status

- A1 attempted cases: `5`.
- A1 successful cases: `5`.
- A1 input is GT-derived colored full-assembly render: `true`.
- Formal Try-3 input: `false`.

## A0 vs A1 coverage

| condition | input | cases | successes | links | crops | feature_crops |
|---|---|---:|---:|---:|---:|---:|
| A0 | original multi-view render | 5 | 5 | 63 | 301 | 49 |
| A1 | colored full-assembly oracle render | 5 | 5 | 63 | 289 | 55 |

## Case rows

| case_id | status | links | crops | feature_crops | empty_crop_rate | error |
|---|---:|---:|---:|---:|---:|---|
| dev_arm-ab15a75247 | SUCCESS | 5 | 30 | 12 | 0.0333 |  |
| dev_arm-4c7b408826 | SUCCESS | 10 | 48 | 8 | 0.0 |  |
| dev_arm-dcc2b0ce1e | SUCCESS | 10 | 49 | 11 | 0.0 |  |
| dev_arm-43fa322555 | SUCCESS | 17 | 81 | 13 | 0.0 |  |
| dev_arm-551a9c392e | SUCCESS | 21 | 81 | 11 | 0.0247 |  |

## Interpretation guard

A1 uses GT-derived link color information. If A1 improves over A0, the result diagnoses a visual grounding/link disambiguation bottleneck. It is not evidence that the formal method works under the original input contract.

## Manual spot-check

Status: `PASS_WITH_CAVEAT`.

The colored full-assembly renders preserve global robot context while making
link boundaries visibly separable. On hard cases, the contact sheets show that
the VLM can now place several crops on color-separated curved housings and wrist
segments that were ambiguous in A0.

Caveat: some URDF links are helper/fixed links with no visual mesh, or are
heavily occluded in the selected two views. The script now preserves those links
in the denominator and tells the VLM to return unknown/occluded broad boxes
rather than inventing visible geometry.

Immediate diagnostic reading: A1 increases feature crops from A0's `49` to
`55` while preserving the same `63` link denominator. This supports, but does
not conclusively prove, that link visual disambiguation is a real bottleneck for
the formal A0 Visual Evidence Agent.
