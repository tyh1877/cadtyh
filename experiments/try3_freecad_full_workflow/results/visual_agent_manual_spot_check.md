# Visual Evidence Agent Manual Spot Check

Date: 2026-09-02

## Inspected artifacts

- `results/visual_agent_contact_sheets/deterministic/dev_arm-ab15a75247_link_crops.png`
- `results/visual_agent_contact_sheets/deterministic/dev_arm-dcc2b0ce1e_link_crops.png`
- `results/visual_agent_contact_sheets/deterministic/dev_arm-551a9c392e_link_crops.png`

## Result

The deterministic visual evidence stage successfully generated packet and crop
artifacts for all 5 robots and 63 URDF links, but the crop quality is only
partially acceptable.

Observed behavior:

- Crops generally include robot pixels rather than empty background.
- Easy-case crops provide usable coarse local context.
- Medium and hard cases still show weak link localization because overlapping
  links and diagonal poses cannot be reliably separated by silhouette principal
  axis plus URDF link order alone.
- The generated observations intentionally avoid mechanical feature claims; they
  are placeholders for later VLM/manual interpretation.

## Gate decision

Do not feed the deterministic packets directly into Mechanical Embodiment Plan
generation as final visual evidence.

The stage is acceptable as infrastructure and manual-inspection material, but
not yet as a complete Try-3 Visual Evidence Agent.

Required next fix:

1. Repair GLM multimodal transport or use a smaller per-case/per-view VLM
   protocol.
2. Generate VLM-backed focus boxes and observable feature descriptions.
3. Re-run manual spot check before releasing packets to MEP.

## VLM smoke

Command attempted:

```text
.venv\Scripts\python.exe experiments\try3_freecad_full_workflow\scripts\run_visual_agent.py --mode vlm --case dev_arm-ab15a75247 --timeout-seconds 120
```

Result:

- `status=FAILURE`
- `error_type=APITimeoutError`
- `error=Request timed out.`

The failure is preserved in:

```text
experiments/try3_freecad_full_workflow/runs/visual_agent/vlm/dev_arm-ab15a75247/stage_manifest.json
```
