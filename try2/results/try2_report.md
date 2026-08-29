# Try-2 final report (amended external-URDF protocol)

## Protocol and validity
C/D use sanitized URDF as the external authoritative kinematic representation. Fusion creates editable parameterized link components and places occurrences at canonical FK transforms; native Fusion joints are a non-gating demonstration. The acceptance checklist records remaining evidence.

## Coverage and execution
A=13/15, B=13/13 eligible A plans, C=15/15, D=15/15. All final B/D jobs produced native F3D/STEP/STL and per-component STL; logs record feature, component, joint and operation counts.

## Main geometry and motion
Median Chamfer/IoU: A 0.00291/0.341; B 0.00249/0.326; C 0.00088/0.505; D 0.00147/0.404. Median motion error: A 0.259, B 0.266, C 0.0264, D 0.0250. Per-link median Chamfer: A 0.017413, B 0.018141, C 0.001083, D 0.001499. Joint-local median Chamfer: A 0.001297, B 0.001060, C 0.000562, D 0.000725.

## 2x2 interpretation
URDF improves whole-robot, per-link and joint-local geometry substantially in the primitive track (A¡úC), while also making origin error zero and lowering motion error. Fusion improves no-URDF Chamfer but not IoU or per-link geometry consistently (A¡úB). Under URDF, Fusion preserves motion but is geometrically behind the primitive backend (C¡úD), reflecting the minimal primitive Tool Layer rather than a negative result about editable CAD.

## Recommendation
The evidence supports kinematic-conditioned CAD generation as the next paper direction. Keep Fusion as an editable execution substrate; improve the Fusion embodiment Tool Layer before claiming a backend advantage.
