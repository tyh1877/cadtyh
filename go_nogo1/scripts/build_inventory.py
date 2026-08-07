"""Build a provenance-rich URDF inventory for Go/No-Go 1.

Only Python's standard library is required. Outputs are deterministic for a fixed
dataset checkout and are intended to be inspected before Audit-30 is frozen.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict, deque
from pathlib import Path, PurePosixPath


MESH_EXTENSIONS = {".stl", ".dae", ".obj", ".ply"}


def norm(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").casefold()


def load_metadata(dataset_root: Path):
    entries = []
    source_by_root = {}
    for source_file in dataset_root.glob("*/source-information.json"):
        with source_file.open(encoding="utf-8") as handle:
            source_by_root[source_file.parent.resolve()] = json.load(handle)["source"]
    for meta_file in dataset_root.rglob("meta-information.json"):
        try:
            data = json.loads(meta_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        source = next(
            (value for root, value in source_by_root.items() if root in meta_file.resolve().parents),
            meta_file.relative_to(dataset_root).parts[0],
        )
        for robot in data.get("robots", []):
            for rel in robot.get("urdf", []):
                record = dict(robot)
                record["source"] = source
                record["meta_file"] = str(meta_file.resolve())
                record["urdf_abs"] = norm(meta_file.parent / rel)
                entries.append(record)
    return entries


def mesh_index(dataset_root: Path):
    by_name = defaultdict(list)
    all_meshes = []
    for path in dataset_root.rglob("*"):
        if path.is_file() and path.suffix.casefold() in MESH_EXTENSIONS:
            resolved = path.resolve()
            all_meshes.append(resolved)
            by_name[path.name.casefold()].append(resolved)
    return all_meshes, by_name


def clean_uri(uri: str) -> str:
    value = uri.strip().replace("\\", "/")
    value = re.sub(r"^(package|model|file)://", "", value, flags=re.I)
    return value.lstrip("/")


def suffix_score(candidate: Path, reference: str) -> tuple[int, int]:
    a = [x.casefold() for x in candidate.as_posix().split("/")]
    b = [x.casefold() for x in PurePosixPath(reference).parts]
    matched = 0
    while matched < min(len(a), len(b)) and a[-1 - matched] == b[-1 - matched]:
        matched += 1
    return matched, -len(a)


def common_prefix_depth(candidate: Path, urdf: Path) -> int:
    """Prefer a same-package mesh when short package URIs are ambiguous."""
    candidate_parts = [part.casefold() for part in candidate.resolve().parts]
    urdf_parts = [part.casefold() for part in urdf.resolve().parts]
    return sum(a == b for a, b in zip(candidate_parts, urdf_parts))


def resolve_mesh(uri: str, urdf: Path, dataset_root: Path, by_name):
    ref = clean_uri(uri)
    if not ref:
        return None, "empty"
    p = Path(ref)
    direct = (urdf.parent / p).resolve()
    if direct.is_file():
        return direct, "relative"
    parts = PurePosixPath(ref).parts
    for ancestor in [urdf.parent, *urdf.parents]:
        for start in range(len(parts)):
            candidate = ancestor.joinpath(*parts[start:]).resolve()
            if candidate.is_file() and dataset_root.resolve() in candidate.parents:
                return candidate, "ancestor_suffix"
        if ancestor.resolve() == dataset_root.resolve():
            break
    candidates = by_name.get(PurePosixPath(ref).name.casefold(), [])
    if candidates:
        ranked = sorted(
            candidates,
            key=lambda c: (suffix_score(c, ref)[0], common_prefix_depth(c, urdf),
                           suffix_score(c, ref)[1]),
            reverse=True,
        )
        best_key = (suffix_score(ranked[0], ref)[0], common_prefix_depth(ranked[0], urdf))
        tied = [c for c in ranked
                if (suffix_score(c, ref)[0], common_prefix_depth(c, urdf)) == best_key]
        if len(tied) == 1:
            return ranked[0], "indexed_suffix_nearest_package"
    return None, "unresolved"


def graph_metrics(root):
    links = {node.get("name", "") for node in root.findall("link")}
    edges = []
    joint_types = Counter()
    for joint in root.findall("joint"):
        joint_types[joint.get("type", "unknown")] += 1
        parent = joint.find("parent")
        child = joint.find("child")
        if parent is not None and child is not None:
            edges.append((parent.get("link", ""), child.get("link", "")))
    children = defaultdict(list)
    indegree = Counter()
    for parent, child in edges:
        children[parent].append(child)
        indegree[child] += 1
    roots = sorted(links - set(indegree))
    max_depth = 0
    visited = set()
    queue = deque((node, 0) for node in roots)
    while queue:
        node, depth = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        max_depth = max(max_depth, depth)
        queue.extend((child, depth + 1) for child in children[node])
    graph_valid = bool(links) and len(roots) >= 1 and len(visited) == len(links)
    actuated = sum(v for k, v in joint_types.items() if k not in {"fixed", "floating", "planar"})
    return len(links), len(edges), actuated, len(roots), max_depth, graph_valid, joint_types


def parse_urdf(urdf: Path, dataset_root: Path, by_name):
    row = {"parse_ok": False, "parse_error": "", "robot_xml_name": ""}
    try:
        root = ET.parse(urdf).getroot()
    except (ET.ParseError, OSError) as exc:
        row["parse_error"] = str(exc)
        return row
    row["parse_ok"] = True
    row["robot_xml_name"] = root.get("name", "")
    links, joints, actuated, roots, depth, valid, joint_types = graph_metrics(root)
    visual_meshes = []
    collision_meshes = []
    primitive_visuals = 0
    links_with_visual = 0
    links_with_mesh_visual = 0
    for link in root.findall("link"):
        visuals = link.findall("visual")
        if visuals:
            links_with_visual += 1
        has_mesh = False
        for visual in visuals:
            geometry = visual.find("geometry")
            if geometry is None:
                continue
            mesh = geometry.find("mesh")
            if mesh is not None and mesh.get("filename"):
                visual_meshes.append(mesh.get("filename"))
                has_mesh = True
            elif list(geometry):
                primitive_visuals += 1
        links_with_mesh_visual += int(has_mesh)
        for collision in link.findall("collision"):
            mesh = collision.find("geometry/mesh")
            if mesh is not None and mesh.get("filename"):
                collision_meshes.append(mesh.get("filename"))
    resolved = []
    methods = Counter()
    for uri in visual_meshes:
        path, method = resolve_mesh(uri, urdf, dataset_root, by_name)
        methods[method] += 1
        if path:
            resolved.append(path)
    nonfixed_links = max(1, actuated + 1)
    resolution_rate = len(resolved) / len(visual_meshes) if visual_meshes else 0.0
    coverage = min(1.0, links_with_mesh_visual / nonfixed_links)
    row.update({
        "n_links": links, "n_joints": joints, "n_actuated_joints": actuated,
        "n_graph_roots": roots, "max_chain_depth": depth, "graph_valid": valid,
        "joint_types": json.dumps(joint_types, sort_keys=True),
        "n_visual_mesh_refs": len(visual_meshes), "n_resolved_visual_mesh_refs": len(resolved),
        "visual_mesh_resolution_rate": round(resolution_rate, 6),
        "n_links_with_visual": links_with_visual,
        "n_links_with_mesh_visual": links_with_mesh_visual,
        "nonfixed_visual_coverage": round(coverage, 6),
        "n_primitive_visuals": primitive_visuals,
        "n_collision_mesh_refs": len(collision_meshes),
        "resolved_visual_meshes": json.dumps(sorted({str(x) for x in resolved})),
        "resolution_methods": json.dumps(methods, sort_keys=True),
    })
    if valid and resolution_rate >= 0.9 and coverage >= 0.8:
        grade = "A"
    elif valid and resolution_rate >= 0.7 and visual_meshes and coverage >= 0.5:
        grade = "B"
    else:
        grade = "C"
    row["qc_grade"] = grade
    return row


def write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    dataset_root = args.dataset_root.resolve()
    metadata = load_metadata(dataset_root)
    meta_by_urdf = {item["urdf_abs"]: item for item in metadata}
    all_meshes, by_name = mesh_index(dataset_root)
    rows = []
    for urdf in sorted(dataset_root.rglob("*.urdf")):
        meta = meta_by_urdf.get(norm(urdf), {})
        relative = urdf.relative_to(dataset_root)
        source = meta.get("source", relative.parts[0])
        row = {
            "urdf_path": str(urdf.resolve()), "relative_path": str(relative),
            "source": source, "metadata_matched": bool(meta),
            "dataset_id": meta.get("id", ""), "name": meta.get("name", ""),
            "type": meta.get("type", "unknown"), "manufacturer": meta.get("manufacturer", "unknown"),
            "variant": meta.get("variant") or "original",
            "xacro_generated": meta.get("xacro-generated", ""),
            "source_link": meta.get("source-link", ""),
        }
        row.update(parse_urdf(urdf, dataset_root, by_name))
        rows.append(row)
    write_csv(args.output, rows)
    summary = {
        "dataset_root": str(dataset_root), "n_urdf_files": len(rows),
        "n_metadata_records": len(metadata), "n_mesh_files": len(all_meshes),
        "metadata_matched": sum(bool(r["metadata_matched"]) for r in rows),
        "parse_ok": sum(bool(r["parse_ok"]) for r in rows),
        "qc_grades": dict(Counter(r.get("qc_grade", "C") for r in rows)),
        "types": dict(Counter(r["type"] for r in rows)),
        "sources": dict(Counter(r["source"] for r in rows)),
    }
    args.output.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
