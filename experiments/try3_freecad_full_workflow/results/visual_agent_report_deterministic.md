# Visual Evidence Agent Stage Report

## Scope

This stage generates non-GT global-to-local visual evidence packets for the fixed TrySet-5.
Generation mode: `deterministic`.

## Crop localization method

- Deterministic mode computes a near-white-background silhouette bounding box and divides it by anonymous URDF link order.
- VLM mode asks `glm-5.3-flash` for normalized per-link focus boxes and observable local evidence.
- Generate front/isometric link, proximal-joint, and distal-joint crops for every URDF link.
- Do not use GT mesh, GT segmentation, STEP/CAD, product identity, or hidden part labels.

## Coverage

- Cases: `5`.
- Links: `63`.
- Crop records: `378`.
- Stage status: `SUCCESS` for crop/evidence-packet generation.

## Known limitations

- Crops must be manually spot-checked before downstream MEP generation.
- Deterministic crops are broad localization aids, not semantic annotations.
- Side-view occlusion and high-link-count robots may have weak per-link localization.
- Deterministic mode is not sufficient to release packets to MEP unless manual spot check explicitly passes.

## Manual inspection targets

- `dev_arm-ab15a75247` contact sheet: `D:\CADtest\papertest\experiments\try3_freecad_full_workflow\results\visual_agent_contact_sheets\deterministic\dev_arm-ab15a75247_link_crops.png`
- `dev_arm-4c7b408826` contact sheet: `D:\CADtest\papertest\experiments\try3_freecad_full_workflow\results\visual_agent_contact_sheets\deterministic\dev_arm-4c7b408826_link_crops.png`
- `dev_arm-dcc2b0ce1e` contact sheet: `D:\CADtest\papertest\experiments\try3_freecad_full_workflow\results\visual_agent_contact_sheets\deterministic\dev_arm-dcc2b0ce1e_link_crops.png`
- `dev_arm-43fa322555` contact sheet: `D:\CADtest\papertest\experiments\try3_freecad_full_workflow\results\visual_agent_contact_sheets\deterministic\dev_arm-43fa322555_link_crops.png`
- `dev_arm-551a9c392e` contact sheet: `D:\CADtest\papertest\experiments\try3_freecad_full_workflow\results\visual_agent_contact_sheets\deterministic\dev_arm-551a9c392e_link_crops.png`
