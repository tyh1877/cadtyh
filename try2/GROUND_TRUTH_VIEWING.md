# Viewing assembled ground-truth meshes in Fusion

Run `export_gt_assembled_meshes.py` with the repository `.venv` to create one
canonical/home-pose STL per frozen case. The script loads the GT URDF, applies
zero joint values, and transforms every visual link mesh into the URDF base
frame before combining them. It does not use AI-generated geometry.

Open the corresponding `ground_truth_assembled_home.stl` through Fusion's
**Insert Mesh** command. Compare it with the AI native assembly at
`try2/runs/D/<case_id>/model.f3d` (or the B condition for no-URDF input).
The `manifest.json` alongside each STL records source URDF and output hashes.
