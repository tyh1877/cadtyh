# Try5 Knowledge-Role Ablation

Status: **PASS**

F0 is image-first without knowledge, F1 is the legacy template dispatcher, and F2 is image-first with post-draft advisory knowledge.

- Unregistered formal-mask IoU F0/F1/F2 (diagnostic only): 0.185739 / 0.187416 / 0.186077
- Mean exposed cylindrical-surface ratio F0/F1/F2: 0.083609 / 0.151353 / 0.082743
- Full twin-disc templates F0/F1/F2: 0 / 3 / 0
- Image-stability delta F0-F2: 0.008236; template-to-F2 delta: 0.012339
- F2 BICR: 100.0%; all JR3: True; GCFR: 0.906250
- F2 template dispatch: 0.0%; auto-bridge-enabled links: 0

The F2 knowledge source can critique and add declared transition details, but cannot select visible interface topology.  GT meshes were unavailable locally, so no GT-CAD metric is claimed; the formal-mask metric is explicitly non-registered and non-gating.
