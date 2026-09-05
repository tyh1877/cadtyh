# Colored STEP Visual Grounding Ablation Protocol

## Status and purpose

This is a paired oracle diagnostic. It asks whether
explicit per-link color separation improves visual grounding and downstream
Mechanical Embodiment Planning (MEP).

It is not a formal Try-3 input condition. Per-link colors use GT-derived link
membership and therefore must never be reported as a deployable RobotCAD input.

## Frozen cohorts and source geometry

- Native STEP cohort (primary): `native_step5_v1.csv`, five frozen Trossen
  assemblies selected before viewing ablation results. These are original
  calibration STEP files, not generated CAD.
- Historical mesh cohort (secondary context only): the existing TrySet-5 A1
  results under `../visual_evidence_input_ablation/`. Those results are not
  pooled with the native STEP cohort.
- All five native STEP cases remain in every A0/A1/A2 denominator.
- Each original STEP is imported as B-Rep, its leaf components are colored in
  place, and a color-bearing STEP is re-exported. No STL-to-STEP conversion is
  permitted in the primary cohort.
- The current TrySet-5 cache itself has no source STEP. Four cases contain STL
  and one hard case contains DAE; this fact remains documented to prevent a
  generated/faceted STEP from being mislabeled as source GT.

## Paired image conditions

- `A0_controlled`: every visible link is neutral gray.
- `A1_color_only`: every visible link has a distinct color; no link-color legend
  is supplied to the VLM.
- `A2_color_legend`: identical to A1, with an explicit anonymous `L* -> RGB`
  legend supplied to the VLM.

Geometry, transforms, camera, projection, resolution, lighting, background,
view order, prompt contract, model, and token budget are frozen across the
three conditions. Only color and legend information may differ.

## Views

The six frozen views are `front`, `rear`, `left`, `right`, `top`, and
`isometric`.

## Model and calls

- Provider/model: the existing validated project configuration,
  `glm-5.3-flash`.
- Real multimodal image inputs are required; paths in text do not count.
- Temperature is zero, top-p is one, reasoning effort is low, and the maximum
  output is 8192 tokens.
- API retries are disabled for the formal matrix. Every API, parsing, schema, or
  crop failure remains in the denominator.
- The first execution is a full feasibility replicate (`replicate_01`). Formal
  repeated runs may be added only after this pipeline and evaluator are frozen.

## E1: visual grounding endpoints

Primary endpoints are computed per link and paired by case/link:

- best-view predicted bbox IoU against the withheld renderer link mask;
- link recall at bbox IoU >= 0.5;
- target-pixel purity inside the predicted bbox;
- wrong-link crop rate;
- blank crop rate;
- proximal/distal joint-region localization availability;
- evidence and feature crop counts as diagnostics only.

Evaluator masks are never sent to A0. A1/A2 visibly expose colors by design,
but the exact pixel masks remain evaluator-only.

## E2: MEP endpoints

The same Mechanical Embodiment Architect prompt/schema/model is run on each
condition's evidence packet. Endpoints include:

- schema-valid and complete-link rate;
- evidence traceability rate;
- joint-housing coverage;
- visible structural feature count and unsupported-reference rate;
- per-link A0/A1/A2 plan differences.

MEP feature correctness requiring expert labels is reported as pending unless a
frozen human annotation sheet is completed before inspecting condition labels.
More generated features are not automatically treated as better.

## Interpretation

- E1 improvement without E2 improvement means color helps segmentation/localization
  but has not demonstrated value to mechanical reasoning.
- E1 and E2 improvement means link disambiguation is a likely current bottleneck.
- Any improvement is an oracle upper-bound result and does not validate the
  formal Try-3 method under its original image/text/sanitized-URDF contract.

## Initial decision thresholds

The feasibility replicate supports proceeding to repeated formal runs only if:

- all 5 native STEP cases and every imported leaf component are accounted for
  in every condition;
- silent case dropping is zero;
- geometry and camera parity checks pass;
- A2 improves mean bbox IoU over A0 by at least 0.10;
- A2 reduces wrong-link crop rate by at least 30% relative to A0;
- A2 does not increase MEP unsupported-reference rate by more than 0.05;
- A2 improves on at least 4 of 5 cases for the primary grounding endpoint.
