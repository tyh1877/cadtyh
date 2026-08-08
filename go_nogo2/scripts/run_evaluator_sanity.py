"""Exercise evaluator identity, small perturbations, and structural corruptions.

The fixtures are copied from the frozen pilot inputs and stored beneath the
ignored run directory.  No model output or judge is involved.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

from evaluate_prediction import evaluate, load_robot


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data" / "pilot10"
DEFAULT_OUTPUT = ROOT / "runs" / "final_validation" / "evaluator_sanity"
SEED = 20260808


def actuated(root: ET.Element) -> list[ET.Element]:
    return [joint for joint in root.findall("joint") if joint.get("type") in {"revolute", "continuous", "prismatic"}]


def rotate(axis: np.ndarray, degrees: float) -> np.ndarray:
    axis = axis / np.linalg.norm(axis)
    basis = np.array([1.0, 0.0, 0.0]) if abs(axis[0]) < 0.8 else np.array([0.0, 1.0, 0.0])
    perpendicular = np.cross(axis, basis)
    perpendicular /= np.linalg.norm(perpendicular)
    radians = math.radians(degrees)
    return math.cos(radians) * axis + math.sin(radians) * perpendicular


def set_vector(node: ET.Element, attribute: str, values: np.ndarray) -> None:
    node.set(attribute, " ".join(f"{value:.10g}" for value in values))


def mesh_nodes(root: ET.Element) -> list[ET.Element]:
    return list(root.iter("mesh"))


def target_visual_link(root: ET.Element) -> ET.Element:
    """Select a non-root link with an actual visual mesh, never a mesh-less frame."""
    links = root.findall("link")
    candidates = [link for link in links[1:] if list(link.iter("mesh"))]
    if not candidates:
        raise ValueError("fixture has no non-root visual link")
    return candidates[-1]


def apply_mutation(urdf: Path, name: str) -> None:
    tree = ET.parse(urdf)
    root = tree.getroot()
    joints = actuated(root)
    if not joints:
        raise ValueError("fixture has no actuated joint")

    if name.startswith("axis_"):
        degrees = float(name.split("_")[1])
        for joint in joints:
            axis = joint.find("axis")
            source = np.fromstring(axis.get("xyz", "1 0 0"), sep=" ")
            set_vector(axis, "xyz", rotate(source, degrees))
    elif name.startswith("origin_mm_"):
        offset = float(name.rsplit("_", 1)[1]) / 1000.0
        for joint in joints:
            origin = joint.find("origin")
            value = np.fromstring(origin.get("xyz", "0 0 0"), sep=" ")
            set_vector(origin, "xyz", value + np.array([offset, 0.0, 0.0]))
    elif name.startswith("link_scale_pct_"):
        percent = float(name.rsplit("_", 1)[1])
        factor = 1.0 + percent / 100.0
        target_link = target_visual_link(root)
        for mesh in target_link.iter("mesh"):
            existing = np.fromstring(mesh.get("scale", "1 1 1"), sep=" ")
            set_vector(mesh, "scale", existing * factor)
    elif name.startswith("visual_translation_mm_"):
        offset = float(name.rsplit("_", 1)[1]) / 1000.0
        target_link = target_visual_link(root)
        visual = target_link.find("visual")
        if visual is None:
            raise ValueError("target link has no visual")
        origin = visual.find("origin")
        if origin is None:
            origin = ET.SubElement(visual, "origin")
        value = np.fromstring(origin.get("xyz", "0 0 0"), sep=" ")
        set_vector(origin, "xyz", value + np.array([offset, 0.0, 0.0]))
    elif name == "remove_terminal_link":
        terminal = joints[-1]
        child = terminal.find("child").get("link")
        root.remove(terminal)
        root.remove(next(link for link in root.findall("link") if link.get("name") == child))
    elif name == "remove_terminal_joint":
        root.remove(joints[-1])
    elif name == "reparent_terminal_link":
        terminal = joints[-1]
        terminal.find("parent").set("link", root.findall("link")[0].get("name"))
    elif name == "revolute_fixed":
        for joint in joints:
            joint.set("type", "fixed")
    else:
        raise ValueError(f"unknown mutation: {name}")
    tree.write(urdf, encoding="utf-8", xml_declaration=True)


def flatten(case_id: str, mutation: str, status: str, payloads: tuple[dict, ...] | None, error: str | None) -> dict:
    row = {"case_id": case_id, "mutation": mutation, "status": status, "error": error}
    if payloads is None:
        return row
    geometry, assembly, kinematic, motion, outcome = payloads
    row.update({
        "chamfer": geometry["chamfer"], "hd95": geometry["hd95"], "voxel_iou": geometry["voxel_iou"],
        "part_f1": assembly["part_f1"], "graph_f1": assembly["assembly_graph_f1"],
        "joint_type_accuracy": kinematic["joint_type_accuracy"],
        "axis_error_degrees_median": kinematic["axis_error_degrees_median"],
        "origin_error_normalized_median": kinematic["joint_origin_error_normalized_median"],
        "link_translation_error_normalized_median": motion["link_translation_error_normalized_median"],
        "link_rotation_error_degrees_median": motion["link_rotation_error_degrees_median"],
        "simultaneous_success": outcome["simultaneous_success"],
        "failure_patterns": ";".join(outcome["failure_patterns"]),
    })
    return row


def evaluate_fixture(case_dir: Path, fixture_dir: Path, mutation: str) -> dict:
    if fixture_dir.exists():
        shutil.rmtree(fixture_dir)
    shutil.copytree(case_dir, fixture_dir)
    try:
        if mutation != "identity":
            apply_mutation(fixture_dir / "urdf" / "model.urdf", mutation)
        result = evaluate(load_robot(case_dir / "urdf" / "model.urdf"), load_robot(fixture_dir / "urdf" / "model.urdf"), SEED)
        return flatten(case_dir.name, mutation, "OK", result, None)
    except Exception as exc:
        return flatten(case_dir.name, mutation, "INVALID", None, f"{type(exc).__name__}: {exc}")


def median(rows: list[dict], mutation: str, field: str) -> float:
    values = [float(row[field]) for row in rows if row["mutation"] == mutation and row["status"] == "OK" and row.get(field) is not None]
    if not values:
        raise AssertionError(f"no valid values for {mutation}:{field}")
    return float(np.median(values))


def sanity_checks(rows: list[dict]) -> list[str]:
    notes: list[str] = []
    identities = [row for row in rows if row["mutation"] == "identity"]
    assert len(identities) == 10 and all(row["status"] == "OK" for row in identities)
    for row in identities:
        assert row["chamfer"] == 0 and row["hd95"] == 0 and row["voxel_iou"] == 1
        assert row["part_f1"] == 1 and row["graph_f1"] == 1 and row["joint_type_accuracy"] == 1
        assert row["axis_error_degrees_median"] == 0 and row["origin_error_normalized_median"] == 0
        assert row["link_translation_error_normalized_median"] == 0 and row["link_rotation_error_degrees_median"] == 0
    notes.append("GT-vs-GT is exact on all 10 cases.")

    series = [
        ("axis_0", "axis_5", "axis_10", "axis_error_degrees_median", "axis"),
        ("origin_mm_0", "origin_mm_5", "origin_mm_10", "origin_error_normalized_median", "origin"),
        ("link_scale_pct_1", "link_scale_pct_5", None, "chamfer", "local scale"),
        ("visual_translation_mm_1", "visual_translation_mm_5", None, "chamfer", "visual translation"),
    ]
    for low, middle, high, field, label in series:
        values = [median(rows, item, field) for item in (low, middle) if item]
        if high:
            values.append(median(rows, high, field))
        assert all(next_value >= current - 1e-12 for current, next_value in zip(values, values[1:])), (label, values)
        notes.append(f"{label} perturbations are monotonic in median {field}: {values}.")

    assert median(rows, "axis_45", "axis_error_degrees_median") > 10
    assert median(rows, "axis_90", "axis_error_degrees_median") >= median(rows, "axis_45", "axis_error_degrees_median")
    assert median(rows, "link_scale_pct_20", "chamfer") > median(rows, "link_scale_pct_5", "chamfer")
    structural = [row for row in rows if row["mutation"] in {"axis_45", "axis_90", "remove_terminal_link", "remove_terminal_joint", "reparent_terminal_link", "revolute_fixed"}]
    assert all(row["status"] == "INVALID" or row.get("simultaneous_success") is False for row in structural)
    notes.append("All large structural corruptions are invalid or fail simultaneous success.")
    notes.append("A 20% local-link scale perturbation degrades geometry metrics but can remain below the pilot's whole-robot pass thresholds; this is expected because thresholds evaluate the complete robot rather than a local manufacturing tolerance.")
    return notes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    cases = sorted(path for path in args.data_root.resolve().glob("case_*") if path.is_dir())
    if len(cases) != 10:
        raise SystemExit(f"expected frozen 10 cases, found {len(cases)}")
    mutations = ("identity", "axis_0", "axis_5", "axis_10", "origin_mm_0", "origin_mm_5", "origin_mm_10", "link_scale_pct_1", "link_scale_pct_5", "visual_translation_mm_1", "visual_translation_mm_5", "axis_45", "axis_90", "remove_terminal_link", "remove_terminal_joint", "reparent_terminal_link", "revolute_fixed", "link_scale_pct_20")
    rows = []
    for case_dir in cases:
        for mutation in mutations:
            print(f"{case_dir.name}: {mutation}", flush=True)
            rows.append(evaluate_fixture(case_dir, args.output_dir / "fixtures" / case_dir.name / mutation, mutation))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "sanity_results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted({key for row in rows for key in row}))
        writer.writeheader(); writer.writerows(rows)
    notes = sanity_checks(rows)
    report = ["# Evaluator sanity report", "", "## PASS", ""]
    report.extend(f"- {note}" for note in notes)
    report.extend(["", "## Scope", "", "All perturbations are deterministic copies of the frozen GT URDFs. `INVALID` is retained for corruptions that deliberately violate the rooted-tree contract."])
    (args.output_dir / "sanity_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("PASS: evaluator sanity check")


if __name__ == "__main__":
    main()
