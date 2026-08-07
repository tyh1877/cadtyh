# Go/No-Go 1 blinded expert scoring

Score each anonymous robot from the supplied three-view image. Do not attempt to
identify the model, and do not inspect its source files or automated measurements.

Question: **How difficult is the visible exterior geometry to reconstruct as an
editable CAD model, considering surface and feature complexity rather than mesh
density?**

- 1 — mostly simple primitives, few transitions or details
- 2 — simple housings with limited fillets, cut-outs, or interfaces
- 3 — moderate compound surfaces and several distinct geometric features
- 4 — many curved transitions, recesses, interfaces, or tightly interacting parts
- 5 — highly intricate freeform/compound surfaces and dense geometric detailing

Ignore color/material, apparent triangle density, brand familiarity, and expected
kinematic/control difficulty. Use `unusable_or_incomplete=yes` if a view is clearly
broken or important arm geometry is absent. Record confidence as 1 (low), 2, or 3
(high). Work independently; do not discuss ratings until all files are submitted.

Minimum protocol: two raters with CAD/robotics geometry experience. Three raters
are preferred. Each rater should save a separate copy of `expert_rating_blank.csv`.
