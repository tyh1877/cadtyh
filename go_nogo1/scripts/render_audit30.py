"""Render anonymous, material-neutral three-view sheets for expert scoring."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import trimesh
from matplotlib.collections import PolyCollection
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(Path(__file__).parent))
from build_inventory import mesh_index, resolve_mesh  # noqa: E402


def vector(text, default):
    if not text:
        return np.array(default, dtype=float)
    values = [float(x) for x in text.split()]
    return np.array(values if len(values) == len(default) else default, dtype=float)


def origin_transform(node):
    matrix = np.eye(4)
    if node is None:
        return matrix
    matrix[:3, :3] = Rotation.from_euler("xyz", vector(node.get("rpy"), [0, 0, 0])).as_matrix()
    matrix[:3, 3] = vector(node.get("xyz"), [0, 0, 0])
    return matrix


def link_transforms(root):
    links = [x.get("name") for x in root.findall("link")]
    children, child_names = defaultdict(list), set()
    for joint in root.findall("joint"):
        parent, child = joint.find("parent"), joint.find("child")
        if parent is None or child is None:
            continue
        p, c = parent.get("link"), child.get("link")
        children[p].append((c, origin_transform(joint.find("origin"))))
        child_names.add(c)
    roots = [x for x in links if x not in child_names]
    transforms = {x: np.eye(4) for x in roots}
    queue = deque(roots)
    while queue:
        parent = queue.popleft()
        for child, local in children[parent]:
            transforms[child] = transforms[parent] @ local
            queue.append(child)
    return transforms


def load_geometry(urdf_path, dataset_root, by_name):
    root = ET.parse(urdf_path).getroot()
    transforms = link_transforms(root)
    output, failures = [], []
    for link in root.findall("link"):
        link_tf = transforms.get(link.get("name"), np.eye(4))
        for visual in link.findall("visual"):
            mesh_node = visual.find("geometry/mesh")
            if mesh_node is None or not mesh_node.get("filename"):
                continue
            path, _ = resolve_mesh(mesh_node.get("filename"), urdf_path, dataset_root, by_name)
            if path is None:
                failures.append(mesh_node.get("filename"))
                continue
            try:
                loaded = trimesh.load(path, force="scene", process=True)
                parts = list(loaded.geometry.values()) if isinstance(loaded, trimesh.Scene) else [loaded]
                scale = vector(mesh_node.get("scale"), [1, 1, 1])
                visual_tf = origin_transform(visual.find("origin"))
                transform = link_tf @ visual_tf
                for part in parts:
                    if not isinstance(part, trimesh.Trimesh) or not len(part.faces):
                        continue
                    item = part.copy()
                    item.vertices *= scale
                    item.apply_transform(transform)
                    item.process(validate=True)
                    output.append(item)
            except Exception as exc:
                failures.append(f"{path.name}: {type(exc).__name__}")
    if not output:
        raise ValueError("no renderable visual mesh")
    return output, failures


def view_rotation(azimuth_deg, elevation_deg):
    az, elv = np.radians([azimuth_deg, elevation_deg])
    rz = Rotation.from_euler("z", -az).as_matrix()
    rx = Rotation.from_euler("x", elv).as_matrix()
    return rx @ rz


def prepare_render_meshes(meshes, max_faces=80000):
    total = sum(len(x.faces) for x in meshes)
    if total <= max_faces:
        return meshes
    output = []
    for mesh in meshes:
        target = max(100, int(max_faces * len(mesh.faces) / total))
        if len(mesh.faces) > target:
            try:
                mesh = mesh.simplify_quadric_decimation(face_count=target, aggression=5)
            except Exception:
                pass
        output.append(mesh)
    return output


def render_view(ax, meshes, rotation):
    polygons, depths, colors = [], [], []
    light = np.array([.25, -.35, .9]); light /= np.linalg.norm(light)
    for mesh in meshes:
        indices = np.arange(len(mesh.faces))
        vertices = np.asarray(mesh.vertices) @ rotation.T
        faces = np.asarray(mesh.faces)[indices]
        tri = vertices[faces]
        normal = np.asarray(mesh.face_normals)[indices] @ rotation.T
        shade = .48 + .42 * np.clip(normal @ light, -0.25, 1)
        polygons.extend(tri[:, :, :2])
        depths.extend(tri[:, :, 2].mean(axis=1))
        colors.extend([(0.25 * s, 0.48 * s, 0.72 * s, 1) for s in shade])
    order = np.argsort(depths)
    collection = PolyCollection([polygons[i] for i in order], facecolors=[colors[i] for i in order],
                                edgecolors="none", rasterized=True)
    ax.add_collection(collection)
    all_vertices = np.vstack([m.vertices @ rotation.T for m in meshes])
    mins, maxs = all_vertices[:, :2].min(axis=0), all_vertices[:, :2].max(axis=0)
    center, span = (mins + maxs) / 2, max(float((maxs - mins).max()), 1e-9) * .56
    ax.set_xlim(center[0] - span, center[0] + span)
    ax.set_ylim(center[1] - span, center[1] + span)
    ax.set_aspect("equal"); ax.axis("off")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    audit = pd.read_csv(args.manifest).sort_values("audit_order")
    _, by_name = mesh_index(args.dataset_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    log = []
    views = [(45, 25, "isometric"), (90, 10, "side"), (0, 88, "top")]
    for _, row in audit.iterrows():
        try:
            meshes, failures = load_geometry(Path(row.urdf_path), args.dataset_root, by_name)
            meshes = prepare_render_meshes(meshes)
            fig, axes = plt.subplots(1, 3, figsize=(12, 4), dpi=150, facecolor="white")
            for ax, (az, elv, title) in zip(axes, views):
                render_view(ax, meshes, view_rotation(az, elv))
                ax.set_title(title, fontsize=9, color="#444")
            fig.suptitle(row.blind_id, fontsize=14, fontweight="bold")
            fig.tight_layout(rect=(0, 0, 1, .94))
            output = args.output_dir / f"{int(row.audit_order):02d}_{row.blind_id}.png"
            fig.savefig(output, bbox_inches="tight", facecolor="white")
            plt.close(fig)
            log.append({"blind_id": row.blind_id, "render_ok": True, "n_mesh_parts": len(meshes),
                        "failures": "; ".join(failures), "output": str(output)})
        except Exception as exc:
            log.append({"blind_id": row.blind_id, "render_ok": False, "n_mesh_parts": 0,
                        "failures": f"{type(exc).__name__}: {exc}", "output": ""})
        print(f"rendered {len(log)}/{len(audit)}", flush=True)
    pd.DataFrame(log).to_csv(args.output_dir.parent / "render_log.csv", index=False, encoding="utf-8-sig")
    print(pd.DataFrame(log).render_ok.value_counts().to_dict())


if __name__ == "__main__":
    main()
