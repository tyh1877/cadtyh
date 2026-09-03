# Visual Evidence Input Ablation

## Purpose

This diagnostic experiment tests whether explicit link-color visual evidence
improves the Visual Evidence Agent's ability to localize robot links and
candidate mechanical details.

This is **not** a formal Try-3 input condition. Colored renders are generated
from ground-truth per-link meshes, so they intentionally use oracle information.
The result may diagnose a visual-grounding bottleneck, but it must not be
reported as the main RobotCAD reconstruction setting.

## Conditions

- A0: Formal Try-3 Visual Evidence Agent v2 on original multi-view renders.
- A1: Oracle colored full-assembly render, where every URDF link is rendered in
  a unique color while preserving full robot context.

## Current scope

The first pass implements A1 for the frozen TrySet-5 cases and compares its
coverage against the existing A0 summary table.
