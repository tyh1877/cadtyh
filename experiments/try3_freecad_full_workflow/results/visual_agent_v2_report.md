# Visual Evidence Agent v2 Feature Zoom Report

## Scope

This stage tests VLM-guided visual scan and feature-level crop generation. It does not generate MEP or CAD.

## Configuration

- VLM model: `glm-5.3-flash`.
- Scan views: `front;isometric`.
- Request timeout seconds: `90.0`.
- Resized image max side: `384`.
- GT geometry used: `false`.

## Coverage

- Cases attempted: `5`.
- Successful cases: `5`.
- Links with packets: `63`.
- Crop records: `301`.
- Stage status: `SUCCESS`.

## Case rows

| case_id | status | links | crops | feature_crops | empty_crop_rate | error |
|---|---:|---:|---:|---:|---:|---|
| dev_arm-ab15a75247 | SUCCESS | 5 | 29 | 9 | 0.0 |  |
| dev_arm-4c7b408826 | SUCCESS | 10 | 47 | 7 | 0.0 |  |
| dev_arm-dcc2b0ce1e | SUCCESS | 10 | 51 | 11 | 0.0196 |  |
| dev_arm-43fa322555 | SUCCESS | 17 | 77 | 9 | 0.0 |  |
| dev_arm-551a9c392e | SUCCESS | 21 | 97 | 13 | 0.0412 |  |

## Gate decision

Automatic gate status: `PASS`.

Manual spot-check status: `PASS_WITH_CAVEAT`.

The v2 stage generated VLM-guided link crops and feature-level zoom crops for
all TrySet-5 robots. The contact sheets confirm that the pipeline now performs
local detail zoom rather than only fixed full-image crops. A caveat remains:
when several URDF links are visually contained in one continuous external shell,
some link crops necessarily overlap and are not strong evidence for link
separation. This should be passed forward as uncertainty rather than interpreted
as precise segmentation.
