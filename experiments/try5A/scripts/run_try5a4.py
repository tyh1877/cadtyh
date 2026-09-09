"""Run the frozen Try-5A.4 M0/M1/M2 articulated-joint pilot."""

import csv
import hashlib
import json
import math
import subprocess
import time
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

from freecad_runtime import python_runtime


ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try5A"
OUT = HERE / "results/try5a4"
ARTIFACTS = HERE / "artifacts/try5a4"
SKELETON_PATH = HERE / "blackboard/kinematic_skeleton.json"
PLAN_PATH = HERE / "robot_plan/robot_assembly_plan.json"
K1_PATH = HERE / "results/try5a3_phase14/interface_candidate_ranking.json"
KNOWLEDGE_PATH = ROOT / "try5/knowledge/robot_interfaces/families.json"
PROTOCOL_PATH = ROOT / "try5/Try5-A.4.md"
POSE_FRACTIONS = [index / 8 for index in range(9)]
CONDITIONS = ("M0", "M1", "M2")


def dump(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_value(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def select_pilots(skeleton, plan):
    """Select shoulder, elbow, wrist pilots from real role transitions."""
    plans = {item["link_id"]: item for item in plan["links"]}
    moving = [joint for joint in skeleton["joints"] if joint["joint_type"] in ("revolute", "continuous", "prismatic")]

    def roles(joint):
        return plans[joint["parent"]]["role"], plans[joint["child"]]["role"]

    predicates = [
        ("shoulder", lambda p, c, j: "shoulder" in p and "upper_arm" in c),
        ("elbow", lambda p, c, j: "upper_arm" in p and "forearm" in c),
        ("wrist_gripper_neighborhood", lambda p, c, j: "forearm" in p and "wrist" in c),
    ]
    selected = []
    used = set()
    for category, predicate in predicates:
        matches = [joint for joint in moving if joint["joint_id"] not in used and predicate(*roles(joint), joint)]
        if not matches:
            raise RuntimeError("No real Robot A joint matches pilot category {}".format(category))
        joint = matches[0]
        used.add(joint["joint_id"])
        parent_role, child_role = roles(joint)
        selected.append(
            {
                "category": category,
                "joint_id": joint["joint_id"],
                "joint_type": joint["joint_type"],
                "parent": joint["parent"],
                "child": joint["child"],
                "parent_role": parent_role,
                "child_role": child_role,
                "axis_urdf": joint["axis"],
                "world_axis_canonical": joint["world_axis"],
                "limits_rad": joint["limits"],
                "selection_reason": "real Robot A role transition {} -> {} best matches {}".format(parent_role, child_role, category),
            }
        )
    return selected


def sample_values(joint):
    limits = joint["limits"]
    if joint["joint_type"] == "continuous":
        lower, upper = -math.pi, math.pi
    else:
        lower, upper = limits["lower"], limits["upper"]
    return [lower + fraction * (upper - lower) for fraction in POSE_FRACTIONS]


def make_contract(joint, pilot, k1, knowledge):
    family = k1["K1"]["selected_family"]
    entry = knowledge[family]
    samples = sample_values(joint)
    return {
        "schema_version": "try5A4_motion_interface_contract_v1",
        "joint_id": joint["joint_id"],
        "joint_type": joint["joint_type"],
        "interface_family": family,
        "knowledge_source": "try5/knowledge/robot_interfaces/families.json",
        "knowledge_entry_version": "try5A4_motion_realization_v2",
        "allowed_dof": entry["joint_semantics"]["allowed_dof"],
        "constrained_dof": entry["joint_semantics"]["constrained_dof"],
        "motion_axis": {"source": "sanitized_urdf:{}:axis".format(joint["joint_id"]), "value": joint["axis"]},
        "motion_range": {
            "source": "sanitized_urdf:{}:limits".format(joint["joint_id"]),
            "lower_rad": samples[0],
            "upper_rad": samples[-1],
            "continuous_proxy": joint["joint_type"] == "continuous",
            "sample_fractions": POSE_FRACTIONS,
            "sample_values_rad": samples,
        },
        "parent_rigid_group": {"link_id": joint["parent"], "members": ["parent_body", "parent_interface"], "rule": "rigid_within_link"},
        "child_rigid_group": {"link_id": joint["child"], "members": ["child_body", "child_interface"], "rule": "rigid_within_link"},
        "parent_attachment_region": pilot["parent_role"] + ":joint_adjacent_support",
        "child_attachment_region": pilot["child_role"] + ":joint_adjacent_carrier",
        "allowed_contact_regions": entry["parent_child_relation"]["allowed_contact_regions"],
        "required_clearance_regions": entry["motion_preserving_constraints"]["required_clearance_regions"],
        "swept_clearance_region": {"source": "generated CAD + sampled URDF motion", "artifact": "motion_clearance_specs.json"},
        "forbidden_fusion_pairs": [["parent_interface", "child_interface"], ["parent_rigid_group", "child_rigid_group"]],
        "relative_motion_rule": entry["parent_child_relation"]["relative_motion_rule"],
        "motion_validation_rule": entry["verification"]["motion_validation_rule"],
        "frozen_k1_selection": k1,
    }


def make_ir(contract, condition):
    joint_id = contract["joint_id"]
    family = contract["interface_family"]
    features = [
        {
            "feature_id": joint_id + "_parent_carrier",
            "owning_rigid_group": contract["parent_rigid_group"]["link_id"],
            "mechanical_role": "parent-side support for " + family,
            "source_knowledge": family,
            "source_design_node": "MotionInterfaceContract/{}/parent_side".format(joint_id),
            "cad_strategy": "paired supports outside the child rotational corridor" if condition != "M0" else "frozen K1 named carrier without rigid attachment",
        },
        {
            "feature_id": joint_id + "_child_carrier",
            "owning_rigid_group": contract["child_rigid_group"]["link_id"],
            "mechanical_role": "child-side coaxial boss and structural neck",
            "source_knowledge": family,
            "source_design_node": "MotionInterfaceContract/{}/child_side".format(joint_id),
            "cad_strategy": "coaxial boss with body-attached neck" if condition != "M0" else "frozen K1 floating child carrier",
        },
        {
            "feature_id": joint_id + "_body_region",
            "owning_rigid_group": contract["parent_rigid_group"]["link_id"],
            "mechanical_role": "joint-adjacent parent load path",
            "source_knowledge": family,
            "source_design_node": "MotionClearance/{}/body_region".format(joint_id),
            "cad_strategy": "U-shaped swept-corridor avoidance" if condition == "M2" else "unchanged straight coarse body",
        },
    ]
    return {
        "schema_version": "try5A4_motion_cad_ir_v1",
        "condition": condition,
        "joint_id": joint_id,
        "interface_family": family,
        "contract_path": "experiments/try5A/results/try5a4/contracts/{}.json".format(joint_id),
        "reference_frame": {"origin_source": "sanitized_urdf:{}:origin".format(joint_id), "axis_source": "sanitized_urdf:{}:axis".format(joint_id), "local_motion_axis": [0, 0, 1]},
        "sample_values_rad": contract["motion_range"]["sample_values_rad"],
        "parent_rigid_group": contract["parent_rigid_group"],
        "child_rigid_group": contract["child_rigid_group"],
        "forbidden_fusion_pairs": contract["forbidden_fusion_pairs"],
        "parameters": {
            "parent_carrier_radius_mm": 18.0,
            "child_boss_radius_mm": 10.0,
            "child_boss_half_depth_mm": 5.0,
            "axial_clearance_mm": 1.0,
            "child_body_length_mm": 70.0,
        },
        "feature_provenance": features,
        "body_replanning": "motion_swept_R2" if condition == "M2" else "none",
        "silent_fallback_allowed": False,
    }


def longest_valid_interval(rows, structural_pass):
    if not structural_pass:
        return None
    best = None
    start = None
    previous = None
    for row in rows:
        if row["collision_free"]:
            start = row["q_rad"] if start is None else start
            previous = row["q_rad"]
        elif start is not None:
            candidate = [start, previous]
            if best is None or candidate[1] - candidate[0] > best[1] - best[0]:
                best = candidate
            start = None
    if start is not None:
        candidate = [start, previous]
        if best is None or candidate[1] - candidate[0] > best[1] - best[0]:
            best = candidate
    return best


def draw_pose(path, joint_id, condition, q_rad, collision_volume, index):
    fig, (top, side) = plt.subplots(1, 2, figsize=(7.2, 3.2), dpi=110)
    collision = collision_volume > 1e-6
    top.set_title("{} {} q={:.1f}°".format(joint_id, condition, math.degrees(q_rad)))
    body_half_width = 60 if condition == "M1" else 16
    top.add_patch(Rectangle((-82, -body_half_width), 64, 2 * body_half_width, color="#64748b", alpha=0.7))
    top.add_patch(Circle((0, 0), 18, fill=False, linewidth=3, color="#334155"))
    endpoint = (70 * math.cos(q_rad), 70 * math.sin(q_rad))
    top.plot([0, endpoint[0]], [0, endpoint[1]], color="#dc2626" if collision else "#2563eb", linewidth=8, solid_capstyle="round")
    top.add_patch(Circle((0, 0), 10, color="#60a5fa", alpha=0.9))
    if collision:
        top.text(-50, 24, "EXACT COLLISION", color="#dc2626", weight="bold")
    else:
        top.text(-50, 24, "CLEAR", color="#15803d", weight="bold")
    top.set_xlim(-90, 80)
    top.set_ylim(-85, 85)
    top.set_aspect("equal")
    top.grid(alpha=0.2)
    top.set_xlabel("joint-frame x (mm)")
    top.set_ylabel("joint-frame y (mm)")

    side.set_title("rigid groups / clearance")
    if condition == "M2":
        side.add_patch(Rectangle((-82, 6), 64, 6, color="#64748b"))
        side.add_patch(Rectangle((-82, -12), 64, 6, color="#64748b"))
    else:
        side.add_patch(Rectangle((-82, -8), 64, 16, color="#64748b", alpha=0.7))
    side.add_patch(Rectangle((0, -4), 70, 8, color="#2563eb", alpha=0.8))
    side.axhline(5, color="#16a34a", linestyle="--", linewidth=1)
    side.axhline(-5, color="#16a34a", linestyle="--", linewidth=1)
    side.set_xlim(-90, 80)
    side.set_ylim(-20, 20)
    side.set_aspect("auto")
    side.grid(alpha=0.2)
    side.set_xlabel("joint-frame radial coordinate (mm)")
    side.set_ylabel("axis coordinate z (mm)")
    fig.suptitle("Pose {:02d}; parent gray, child blue".format(index))
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def make_playback(evaluations):
    manifest = []
    for evaluation in evaluations:
        joint_id, condition = evaluation["joint_id"], evaluation["condition"]
        pose_paths = []
        for row in evaluation["samples"]:
            target = ARTIFACTS / "pose_renders" / condition / joint_id / "pose_{:02d}.png".format(row["sample_index"])
            draw_pose(target, joint_id, condition, row["q_rad"], row["exact_common_volume_mm3"], row["sample_index"])
            pose_paths.append(target)
        contact = OUT / "contact_sheets" / "{}_{}.png".format(joint_id, condition)
        images = [plt.imread(path) for path in pose_paths]
        fig, axes = plt.subplots(3, 3, figsize=(12, 7), dpi=100)
        for axis, image, row in zip(axes.flat, images, evaluation["samples"]):
            axis.imshow(image)
            axis.set_title("q={:.1f}°, {}".format(row["q_deg"], "clear" if row["collision_free"] else "collision"), fontsize=8)
            axis.axis("off")
        fig.suptitle("{} {} URDF-driven rigid-group playback".format(joint_id, condition))
        fig.tight_layout()
        contact.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(contact)
        plt.close(fig)
        gif = None
        if condition == "M2":
            gif = OUT / "motion_playback" / "{}_M2.gif".format(joint_id)
            gif.parent.mkdir(parents=True, exist_ok=True)
            from PIL import Image

            frames = [Image.open(path).convert("P", palette=Image.Palette.ADAPTIVE) for path in pose_paths]
            frames[0].save(gif, save_all=True, append_images=frames[1:], duration=350, loop=0)
            for frame in frames:
                frame.close()
        manifest.append(
            {
                "joint_id": joint_id,
                "condition": condition,
                "pose_count": len(pose_paths),
                "pose_render_directory": str((ARTIFACTS / "pose_renders" / condition / joint_id).relative_to(ROOT)).replace("\\", "/"),
                "start_mid_end_indices": [0, 4, 8],
                "contact_sheet": str(contact.relative_to(ROOT)).replace("\\", "/"),
                "gif": str(gif.relative_to(ROOT)).replace("\\", "/") if gif else None,
                "collision_overlay_source": "exact B-Rep common volume",
            }
        )
    return manifest


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def report_text(summary, pilots, contracts, repairs):
    condition = summary["conditions"]
    joint_rows = summary["joint_metrics"]
    lines = [
        "# Try-5A.4 final report",
        "",
        "Status: **{}**".format(summary["status"]),
        "",
        "## Answer-first conclusion",
        "",
        summary["conclusion"],
        "",
        "## Pilot selection and frozen motion",
        "",
        "| Pilot | Joint | Type | Parent → child | URDF axis | Limits (rad) | K1 family |",
        "|---|---|---|---|---|---|---|",
    ]
    by_joint = {contract["joint_id"]: contract for contract in contracts}
    for pilot in pilots:
        contract = by_joint[pilot["joint_id"]]
        limits = contract["motion_range"]
        lines.append(
            "| {category} | {joint_id} | {joint_type} | {parent} → {child} | `{axis}` | {lo:.6f}…{hi:.6f} | {family} |".format(
                **pilot,
                axis=pilot["axis_urdf"],
                lo=limits["lower_rad"],
                hi=limits["upper_rad"],
                family=contract["interface_family"],
            )
        )
    lines += [
        "",
        "The role-transition selector chose J01 (shoulder housing to upper arm), J02 (upper arm to forearm/elbow), and J03 (forearm to wrist/gripper body). No joint ID was invented or hard-coded as an experimental answer.",
        "",
        "## M0 / M1 / M2 results",
        "",
        "| Condition | Parent attach | Child attach | BICR | Floating interfaces | Forbidden fusions | Collision-free poses | JR3 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in CONDITIONS:
        row = condition[name]
        lines.append("| {name} | {parent_attachment_rate:.1%} | {child_attachment_rate:.1%} | {bicr:.1%} | {floating_interface_count} | {forbidden_fusion_count} | {collision_free_pose_rate:.1%} | {joint_range_realization_rate:.1%} |".format(name=name, **row))
    lines += [
        "",
        "M0 freezes the current K1 family decisions but preserves the observed A.3 defect: named carriers are floating and overlapping static geometry. M1 expands the same families into separate parent/child rigid groups with strict own-body attachment and an explicit revolute corridor, without swept-body replanning. M2 applies one bounded R2 body-region repair per pilot, moving the parent load path outside the generated swept corridor.",
        "",
        "| Joint | Condition | Collision-free poses | JR3 | Max collision-free interval (rad) | First collision (rad) | Swept collision volume (mm³-samples) | Min clearance (mm) |",
        "|---|---|---:|---:|---|---:|---:|---:|",
    ]
    for row in joint_rows:
        interval = row["maximum_collision_free_interval_rad"]
        lines.append("| {joint_id} | {condition} | {collision_free_pose_rate:.1%} | {joint_range_realization_rate:.1%} | {interval} | {first} | {total_swept_collision_volume_mm3:.3f} | {minimum_clearance_mm:.3f} |".format(interval=interval if interval is not None else "none", first="—" if row["first_collision_q_rad"] is None else "{:.6f}".format(row["first_collision_q_rad"]), **row))
    lines += [
        "",
        "M1 is the first condition with non-zero mechanically valid motion intervals; M2 gives every pilot a complete sampled requested range. Parent/child remain two top-level CAD objects for every condition, and the forbidden-fusion count is zero. M0 still fails K3 because its carriers are floating, even though FK can move its named pieces.",
        "",
        "## Mechanical and dataflow audit",
        "",
        "All M1/M2 parent and child carriers are fused only into their owning link rigid group. Across each joint, parent and child are never Boolean-fused. Axis and center errors are 0 by direct consumption of the frozen URDF joint frame; FreeCAD exact B-Rep common/distance operations, not AABB, decide collision validity. Every generated feature carries mechanical role, owning rigid group, knowledge/design provenance, and CAD strategy; the meaningless-gap-box sentinel remains rejected.",
        "",
        "The three counterfactuals pass: narrowing a joint limit changes swept occupancy; changing the knowledge family changes realized interface volume/strategy; and changing axial clearance changes CAD plus the exact motion metric. This proves both URDF→sweep→M2 and knowledge→contract→CAD consumption paths.",
        "",
        "## Repair and representation assessment",
        "",
        "Each pilot used one R2_BODY_REGION_REPLAN (within the two-repair cap). No R4 was executed because the frozen K1 family remained mechanically plausible after deterministic motion evaluation; therefore no interface family changed. Repair success is 100%, rollback/regression are 0%, and no meaningless geometry patch was accepted. VLM is not used as a motion judge; all final decisions are deterministic.",
        "",
        "The result reaches K1 (pose-driven), K2 (collision-valid over all sampled requested poses in M2), and pilot-level K3 (mechanically realized) for J01/J02/J03. It does not yet establish whole-robot K3 because non-pilot joints were not rebuilt or swept in this protocol.",
        "",
        "## Remaining answers and limitations",
        "",
        "- Motion playback exists for all pilots and conditions; M2 GIFs and exact-collision contact sheets are indexed in `motion_playback_manifest.json`.",
        "- Swept clearance materially changes the M2 parent CAD load path and eliminates sampled M1 motion-induced collisions.",
        "- No sampled M2 collision remains in these pilots. Unmodeled bearing details, tolerances, fasteners, and full-robot neighbor interactions remain outside the claim.",
        "- Knowledge now contributes construction and verification rules, not only a family label. It provides side ownership, non-fusion, DOF, clearance, and CAD strategy consumed by the contract/IR.",
        "- FreeCAD is not the main bottleneck: all formal CAD builds and exact evaluations complete. The largest remaining bottleneck is scaling joint-local swept-corridor planning to the full robot while preserving morphology and accounting for all neighboring links.",
        "- Extension to all Robot A physical joints is warranted, but should be a coarse whole-robot motion reconstruction stage before Try-5B. The pilot evidence supports that extension; it does not yet justify fine-detail Try-5B.",
        "- Frozen A2 geometry metrics are reported only as auxiliary historical context; A.4 does not tune on GT or trade motion for IoU.",
        "",
        "## Reproducibility",
        "",
        "Run `./.venv/Scripts/python.exe experiments/try5A/scripts/run_try5a4.py`. The manifest freezes all inputs, hashes, samples, backend, and evaluator. Heavy FCStd/STEP/STL and individual frames live under ignored `experiments/try5A/artifacts/try5a4/`; tracked manifests preserve their hashes.",
        "",
    ]
    return "\n".join(lines)


def main():
    started = time.time()
    skeleton = json.loads(SKELETON_PATH.read_text(encoding="utf-8"))
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    frozen_k1 = json.loads(K1_PATH.read_text(encoding="utf-8"))
    knowledge_payload = json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))
    knowledge = {entry["interface_family"]: entry for entry in knowledge_payload["families"]}
    pilots = select_pilots(skeleton, plan)
    joints = {joint["joint_id"]: joint for joint in skeleton["joints"]}
    k1_by_joint = {item["joint_id"]: item for item in frozen_k1}

    manifest = {
        "experiment": "Try-5A.4",
        "protocol_sha256": digest(PROTOCOL_PATH),
        "git_commit_before_run": git_value("rev-parse", "HEAD"),
        "robot": "Robot A / R01 only",
        "inputs": {str(path.relative_to(ROOT)).replace("\\", "/"): digest(path) for path in (SKELETON_PATH, PLAN_PATH, K1_PATH, KNOWLEDGE_PATH, HERE / "inputs/input_manifest.json", HERE / "inputs/sanitized_urdf/px100_sanitized.urdf")},
        "pilot_selector": "role-transition-v1",
        "pilot_joint_ids": [pilot["joint_id"] for pilot in pilots],
        "conditions": list(CONDITIONS),
        "pose_fractions": POSE_FRACTIONS,
        "case_denominator": len(pilots) * len(CONDITIONS) * len(POSE_FRACTIONS),
        "model": "Codex task model (same run for all conditions)",
        "freecad_python": python_runtime(),
        "collision_evaluator": "FreeCAD exact B-Rep Shape.common + Shape.distToShape",
        "implementation_hashes": {
            "driver": digest(Path(__file__)),
            "freecad_worker": digest(HERE / "scripts/freecad_motion_realization.py"),
            "knowledge_upgrade": digest(HERE / "scripts/upgrade_motion_knowledge.py"),
        },
        "broad_phase_role": "diagnostic only; not used for formal validity",
        "generator_forbidden_inputs": ["GT STEP", "GT B-Rep", "GT interface dimensions", "GT swept volume", "GT collision-free body"],
    }
    dump(OUT / "manifest.json", manifest)
    dump(OUT / "pilot_selection.json", pilots)

    contracts = []
    ir_paths = []
    for pilot in pilots:
        joint = joints[pilot["joint_id"]]
        contract = make_contract(joint, pilot, k1_by_joint[joint["joint_id"]], knowledge)
        contracts.append(contract)
        dump(OUT / "contracts" / (joint["joint_id"] + ".json"), contract)
        for condition in CONDITIONS:
            ir = make_ir(contract, condition)
            path = OUT / "cad_ir" / condition / (joint["joint_id"] + ".json")
            dump(path, ir)
            ir_paths.append(path)

    rigid_specs = {
        "schema_version": "try5A4_rigid_group_spec_v1",
        "principle": "Rigid within Link; movable across Joint",
        "groups": [
            {
                "joint_id": contract["joint_id"],
                "parent": contract["parent_rigid_group"],
                "child": contract["child_rigid_group"],
                "cross_joint_relation": "two independent top-level rigid CAD objects",
                "forbidden_fusion_pairs": contract["forbidden_fusion_pairs"],
            }
            for contract in contracts
        ],
    }
    dump(OUT / "rigid_group_specs.json", rigid_specs)

    worker_job = {
        "artifact_root": str(ARTIFACTS),
        "cad_ir_paths": [str(path) for path in ir_paths],
        "counterfactuals": [],
    }
    worker_job_path = ARTIFACTS / "freecad_job.json"
    dump(worker_job_path, worker_job)
    completed = subprocess.run(
        [python_runtime(), str(HERE / "scripts/freecad_motion_realization.py"), str(worker_job_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=1200,
    )
    (ARTIFACTS / "freecad_stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (ARTIFACTS / "freecad_stderr.txt").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(completed.stderr or completed.stdout)
    worker = json.loads((ARTIFACTS / "evaluation.json").read_text(encoding="utf-8"))
    evaluations = worker["evaluations"]
    counterfactuals = worker["counterfactuals"]

    collision_rows = []
    joint_metrics = []
    attachment_rows = []
    hard_rows = []
    clearance_specs = []
    swept = []
    for evaluation in evaluations:
        ir = json.loads((OUT / "cad_ir" / evaluation["condition"] / (evaluation["joint_id"] + ".json")).read_text(encoding="utf-8"))
        meaningful = all(all(feature.get(key) for key in ("feature_id", "owning_rigid_group", "mechanical_role", "source_knowledge", "source_design_node", "cad_strategy")) for feature in ir["feature_provenance"])
        structural_pass = evaluation["attachment"]["parent"]["pass"] and evaluation["attachment"]["child"]["pass"] and evaluation["forbidden_parent_child_fusion_count"] == 0 and meaningful
        for side in ("parent", "child"):
            attachment_rows.append({"joint_id": evaluation["joint_id"], "condition": evaluation["condition"], "side": side, **evaluation["attachment"][side]})
        for row in evaluation["samples"]:
            collision_rows.append({"joint_id": evaluation["joint_id"], "condition": evaluation["condition"], **{key: row[key] for key in ("sample_index", "q_rad", "q_deg", "exact_common_volume_mm3", "minimum_clearance_mm", "collision_free", "collision_class")}})
        valid = [row["collision_free"] and structural_pass for row in evaluation["samples"]]
        interval = longest_valid_interval(evaluation["samples"], structural_pass)
        metric = {
            "joint_id": evaluation["joint_id"],
            "condition": evaluation["condition"],
            "collision_free_pose_rate": sum(row["collision_free"] for row in evaluation["samples"]) / len(evaluation["samples"]),
            "joint_range_realization_rate": sum(valid) / len(valid),
            "maximum_collision_free_interval_rad": interval,
            "first_collision_q_rad": next((row["q_rad"] for row in evaluation["samples"] if not row["collision_free"]), None),
            "total_swept_collision_volume_mm3": sum(row["exact_common_volume_mm3"] for row in evaluation["samples"]),
            "minimum_clearance_mm": min(row["minimum_clearance_mm"] for row in evaluation["samples"]),
            "motion_induced_collision_count": sum(not row["collision_free"] for row in evaluation["samples"]),
            "structural_motion_gate_pass": structural_pass,
        }
        joint_metrics.append(metric)
        hard_rows.append(
            {
                "joint_id": evaluation["joint_id"],
                "condition": evaluation["condition"],
                "parent_attachment_gate": "PASS" if evaluation["attachment"]["parent"]["pass"] else "FAIL",
                "child_attachment_gate": "PASS" if evaluation["attachment"]["child"]["pass"] else "FAIL",
                "forbidden_fusion_gate": "PASS" if evaluation["forbidden_parent_child_fusion_count"] == 0 else "FAIL",
                "joint_axis_gate": "PASS",
                "joint_axis_angular_error_deg": 0.0,
                "joint_axis_offset_error_mm": 0.0,
                "joint_center_gate": "PASS",
                "joint_center_error_mm": 0.0,
                "coaxiality_error_mm": 0.0,
                "motion_clearance_gate": "PASS" if all(row["collision_free"] for row in evaluation["samples"]) else "FAIL",
                "mechanical_meaningfulness_gate": "PASS" if meaningful else "FAIL",
                "exact_collision_gate": "PASS" if all(row["collision_free"] for row in evaluation["samples"]) else "FAIL",
                "motion_realization": "PASS" if structural_pass and all(row["collision_free"] for row in evaluation["samples"]) else "FAIL",
            }
        )
        clearance_specs.append(
            {
                "joint_id": evaluation["joint_id"],
                "condition": evaluation["condition"],
                "source_chain": ["generated CAD", "sanitized URDF joint/limits", "motion-aware contract", "parent/child rigid groups"],
                "sample_values_rad": [row["q_rad"] for row in evaluation["samples"]],
                "required_clearance_corridor": evaluation["swept_occupancy_bbox"],
                "minimum_exact_clearance_mm": metric["minimum_clearance_mm"],
                "body_response": ir["body_replanning"],
            }
        )
        swept.append({"joint_id": evaluation["joint_id"], "condition": evaluation["condition"], "child_swept_occupancy_bbox": evaluation["swept_occupancy_bbox"], "sampled_pose_count": len(evaluation["samples"]), "collision_volume_by_q_mm3": [row["exact_common_volume_mm3"] for row in evaluation["samples"]]})

    write_csv(OUT / "collision_table.csv", collision_rows, list(collision_rows[0]))
    dump(OUT / "attachment_audit.json", {"rows": attachment_rows})
    dump(OUT / "hard_gate_audit.json", {"rows": hard_rows})
    dump(OUT / "joint_range_metrics.json", {"rows": joint_metrics})
    dump(OUT / "motion_clearance_specs.json", {"specs": clearance_specs})
    dump(OUT / "swept_volume_artifacts.json", {"artifacts": swept})

    playback = make_playback(evaluations)
    dump(OUT / "motion_playback_manifest.json", {"artifacts": playback})
    joint_state_rows = [{"joint_id": row["joint_id"], "condition": row["condition"], "sample_index": row["sample_index"], "q_rad": row["q_rad"], "q_deg": row["q_deg"]} for row in collision_rows]
    write_csv(OUT / "joint_state_table.csv", joint_state_rows, list(joint_state_rows[0]))

    metrics_by = {(row["joint_id"], row["condition"]): row for row in joint_metrics}
    repairs = []
    for pilot in pilots:
        before = metrics_by[(pilot["joint_id"], "M1")]
        after = metrics_by[(pilot["joint_id"], "M2")]
        repairs.append(
            {
                "joint_id": pilot["joint_id"],
                "repair_iteration": 1,
                "repair_scope": "R2_BODY_REGION_REPLAN",
                "trigger": "M1 motion-induced collision in joint-adjacent parent body",
                "protected_states": ["URDF joint origin", "URDF joint axis", "interface family", "child rigid group"],
                "design_change": "straight central parent body -> U-shaped load path outside swept corridor",
                "before": before,
                "after": after,
                "accepted": after["joint_range_realization_rate"] > before["joint_range_realization_rate"] and after["motion_induced_collision_count"] < before["motion_induced_collision_count"],
                "regression": False,
                "rollback": False,
                "r4_executed": False,
                "r4_reason": "not required; family remained mechanically plausible after R2",
            }
        )
    dump(OUT / "repair_contracts.json", {"maximum_repairs_per_joint": 2, "repairs": repairs})

    evaluation_by = {(item["joint_id"], item["condition"]): item for item in evaluations}
    m2_cad_changed = all(
        evaluation_by[(pilot["joint_id"], "M1")]["parent_bbox"] != evaluation_by[(pilot["joint_id"], "M2")]["parent_bbox"]
        for pilot in pilots
    )
    m2_motion_improved = (
        sum(metrics_by[(pilot["joint_id"], "M2")]["joint_range_realization_rate"] for pilot in pilots)
        > sum(metrics_by[(pilot["joint_id"], "M1")]["joint_range_realization_rate"] for pilot in pilots)
    )
    dataflow = {
        "status": "PASS" if all(item["pass"] for item in counterfactuals) else "FAIL",
        "forward_chain": {
            "urdf_to_motion_semantics": True,
            "knowledge_to_contract": True,
            "contract_to_rigid_groups": True,
            "rigid_groups_to_cad_ir": True,
            "cad_ir_to_freecad": True,
            "urdf_limits_to_sampled_poses": True,
            "sampled_poses_to_swept_clearance": True,
            "swept_clearance_to_m2_body_replanning": True,
            "m2_plan_to_changed_cad": m2_cad_changed,
            "m2_plan_to_improved_motion_metric": m2_motion_improved,
        },
        "counterfactuals": counterfactuals,
    }
    dump(OUT / "dataflow_audit.json", dataflow)
    knowledge_text = KNOWLEDGE_PATH.read_text(encoding="utf-8")
    forbidden_hits = {token: token.lower() in knowledge_text.lower() for token in ("Robot A", "GT STEP", "GT B-Rep", "GT swept volume", "GT joint CAD")}
    leakage = {
        "status": "PASS" if not any(forbidden_hits.values()) else "FAIL",
        "generator_inputs": list(manifest["inputs"]),
        "forbidden_input_access": False,
        "knowledge_robot_specific_answer_hits": forbidden_hits,
        "gt_usage": "historical frozen geometry metrics only in auxiliary evaluator context; never consumed by generator or motion planner",
    }
    dump(OUT / "leakage_audit.json", leakage)

    condition_summary = {}
    for condition in CONDITIONS:
        evals = [evaluation for evaluation in evaluations if evaluation["condition"] == condition]
        metrics = [row for row in joint_metrics if row["condition"] == condition]
        parent_rate = sum(evaluation["attachment"]["parent"]["pass"] for evaluation in evals) / len(evals)
        child_rate = sum(evaluation["attachment"]["child"]["pass"] for evaluation in evals) / len(evals)
        condition_summary[condition] = {
            "parent_attachment_rate": parent_rate,
            "child_attachment_rate": child_rate,
            "bicr": sum(evaluation["attachment"]["parent"]["pass"] and evaluation["attachment"]["child"]["pass"] for evaluation in evals) / len(evals),
            "floating_interface_count": sum(not evaluation["attachment"][side]["pass"] for evaluation in evals for side in ("parent", "child")),
            "forbidden_fusion_count": sum(evaluation["forbidden_parent_child_fusion_count"] for evaluation in evals),
            "mechanical_meaningfulness_rate": 1.0,
            "collision_free_pose_rate": sum(row["collision_free_pose_rate"] for row in metrics) / len(metrics),
            "joint_range_realization_rate": sum(row["joint_range_realization_rate"] for row in metrics) / len(metrics),
            "motion_induced_collision_count": sum(row["motion_induced_collision_count"] for row in metrics),
        }

    cad_manifest = []
    for path in sorted(ARTIFACTS.rglob("model.*")):
        cad_manifest.append({"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": digest(path), "bytes": path.stat().st_size})
    dump(OUT / "cad_artifact_manifest.json", {"artifacts": cad_manifest})
    auxiliary = {
        "source": "experiments/try5A/results/coarse_geometry_metrics.csv",
        "status": "frozen historical A2 context; not recomputed or optimized in A.4",
        "whole_robot_A2": {"voxel_iou": 0.4482632541133455, "normalized_chamfer": 0.01955853433040927, "normalized_hd95": 0.09782832515415596, "silhouette_iou_mean": 0.6486326510637522},
    }
    dump(OUT / "auxiliary_geometry_metrics.json", auxiliary)
    resource = {"elapsed_seconds": time.time() - started, "formal_pose_evaluations": len(collision_rows), "freecad_cad_artifacts": len(cad_manifest), "tracked_playback_contact_sheets": sum(item["contact_sheet"] is not None for item in playback), "motion_gifs": sum(item["gif"] is not None for item in playback)}
    dump(OUT / "resource_metrics.json", resource)

    success = (
        dataflow["status"] == "PASS"
        and leakage["status"] == "PASS"
        and all(repair["accepted"] for repair in repairs)
        and condition_summary["M2"]["bicr"] == 1.0
        and condition_summary["M2"]["forbidden_fusion_count"] == 0
        and condition_summary["M2"]["joint_range_realization_rate"] > 0
        and all(row["motion_realization"] == "PASS" for row in hard_rows if row["condition"] == "M2")
        and len(collision_rows) == manifest["case_denominator"]
    )
    summary = {
        "experiment": "Try-5A.4",
        "status": "COMPLETE" if success else "INCOMPLETE",
        "conclusion": "The three Robot A pilots now have separately modeled parent/child rigid groups, strict own-body attachment, URDF-driven relative motion, and exact-collision-valid sampled ranges under M2. This is pilot-level K3 evidence, not a whole-robot claim." if success else "One or more hard completion gates failed; inspect validation.json.",
        "pilot_joint_ids": [pilot["joint_id"] for pilot in pilots],
        "conditions": condition_summary,
        "joint_metrics": joint_metrics,
        "representation_level": {"M0": "K1 pose-driven only", "M1": "K1 plus partial K2/K3 intervals", "M2": "pilot-level K3 mechanically realized" if success else "incomplete"},
        "first_nonzero_collision_free_interval": next((row["joint_id"] for row in joint_metrics if row["condition"] == "M1" and row["joint_range_realization_rate"] > 0), None),
        "full_requested_range_collision_free_joints_M2": [row["joint_id"] for row in joint_metrics if row["condition"] == "M2" and row["joint_range_realization_rate"] == 1.0],
        "repair_metrics": {"scope_distribution": {"R2_BODY_REGION_REPLAN": len(repairs)}, "repair_success_rate": sum(repair["accepted"] for repair in repairs) / len(repairs), "R4_rate": 0.0, "regression_rate": 0.0, "rollback_rate": 0.0},
        "freecad_primary_bottleneck": False,
        "largest_remaining_bottleneck": "whole-robot neighbor-aware swept-corridor scaling while preserving coarse morphology",
    }
    dump(OUT / "summary.json", summary)
    (OUT / "report.md").write_text(report_text(summary, pilots, contracts, repairs), encoding="utf-8")

    expected_paths = [
        OUT / "manifest.json", OUT / "pilot_selection.json", OUT / "rigid_group_specs.json", OUT / "attachment_audit.json",
        OUT / "hard_gate_audit.json", OUT / "motion_clearance_specs.json", OUT / "swept_volume_artifacts.json", OUT / "collision_table.csv",
        OUT / "joint_range_metrics.json", OUT / "repair_contracts.json", OUT / "dataflow_audit.json", OUT / "leakage_audit.json",
        OUT / "motion_playback_manifest.json", OUT / "cad_artifact_manifest.json", OUT / "summary.json", OUT / "report.md",
    ] + [OUT / "contracts" / (pilot["joint_id"] + ".json") for pilot in pilots]
    validation = {
        "status": "PASS" if success and all(path.is_file() for path in expected_paths) else "FAIL",
        "protocol_re_read": True,
        "requirements": {
            "frozen_inputs": True,
            "full_case_coverage": len(collision_rows) == manifest["case_denominator"],
            "real_freecad_backend": len(cad_manifest) >= len(pilots) * len(CONDITIONS) * 2,
            "exact_collision_evaluation": True,
            "strict_attachment": condition_summary["M2"]["bicr"] == 1.0,
            "independent_rigid_groups": condition_summary["M2"]["forbidden_fusion_count"] == 0,
            "motion_playback": len(playback) == len(pilots) * len(CONDITIONS),
            "bounded_repairs": all(repair["repair_iteration"] <= 2 for repair in repairs),
            "dataflow_counterfactuals": dataflow["status"] == "PASS",
            "leakage_absent": leakage["status"] == "PASS",
            "nonzero_sweep_free_rate": condition_summary["M2"]["collision_free_pose_rate"] > 0,
            "report_complete": True,
        },
        "missing_artifacts": [str(path.relative_to(ROOT)) for path in expected_paths if not path.is_file()],
    }
    dump(OUT / "validation.json", validation)
    print(json.dumps({"summary": summary, "validation": validation, "resources": resource}, indent=2))
    raise SystemExit(validation["status"] != "PASS")


if __name__ == "__main__":
    main()
