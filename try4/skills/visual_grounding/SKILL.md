---
name: try4-visual-grounding
description: Produce structured, cross-view visual evidence for one Try-4 Semantic Macro-Part from its colored global and isolated reference renders; do not infer hidden CAD or use offline source geometry.
---

# Try-4 visual grounding

Use only the active PartInputPacket and referenced images. Locate the target by
its unique color in global views, then interpret its isolated front/side/top/
isometric views. Record each observed region with shape, supporting views,
confidence and ambiguity. Cross-check apparent openings and separate bodies in
at least two views where possible; distinguish a visible circle from a confirmed
hole. Treat different auto-fit view scales as nonmetric.

Do not copy source mappings, infer exact B-Rep dimensions, project unregistered
URDF frames into images, or distribute whole-robot features among parts. A region
that is occluded or not independently visible stays uncertain. Preserve visible
working gaps and multiple bodies. Output structured evidence only.

