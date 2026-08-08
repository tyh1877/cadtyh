"""Compile a validated robot blueprint to meshes, URDF, and optional CADIR graphs."""

from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import numpy as np
import trimesh


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def _transform_from_z(axis: list[float], center: list[float]) -> np.ndarray:
    matrix = trimesh.geometry.align_vectors([0.0, 0.0, 1.0], axis)
    if matrix is None:
        matrix = np.eye(4)
    matrix[:3, 3] = np.asarray(center, dtype=float)
    return matrix


def trimesh_primitive(item: dict[str, Any]) -> trimesh.Trimesh:
    kind, center = item["type"], item["center"]
    if kind == "box":
        mesh = trimesh.creation.box(extents=item["size"])
        mesh.apply_translation(center)
    elif kind == "cylinder":
        mesh = trimesh.creation.cylinder(radius=item["radius"], height=item["height"], sections=48)
        mesh.apply_transform(_transform_from_z(item["axis"], center))
    elif kind == "sphere":
        mesh = trimesh.creation.icosphere(subdivisions=3, radius=item["radius"])
        mesh.apply_translation(center)
    elif kind == "cone":
        # Trimesh has no frustum primitive; use a cone when top radius is zero,
        # otherwise create a conservative cylinder envelope.
        if item["top_radius"] <= 1e-9:
            mesh = trimesh.creation.cone(radius=item["bottom_radius"], height=item["height"], sections=48)
            mesh.apply_translation([0.0, 0.0, -item["height"] / 2.0])
        else:
            mesh = trimesh.creation.cylinder(
                radius=max(item["bottom_radius"], item["top_radius"]),
                height=item["height"], sections=48,
            )
        mesh.apply_transform(_transform_from_z(item["axis"], center))
    else:
        raise ValueError(f"unsupported primitive: {kind}")
    if not mesh.is_volume:
        raise ValueError(f"{kind} did not produce a volume")
    return mesh


def compile_direct(blueprint: dict[str, Any], output_dir: Path) -> Path:
    mesh_dir = output_dir / "meshes"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    for link in blueprint["links"]:
        meshes = [trimesh_primitive(item) for item in link["primitives"]]
        combined = trimesh.util.concatenate(meshes)
        combined.export(mesh_dir / f"{safe_name(link['name'])}.stl")
    return write_urdf(blueprint, output_dir)


def _scad_primitive(scad: Any, item: dict[str, Any], prefix: str) -> Any:
    kind, center = item["type"], np.asarray(item["center"], dtype=float)
    if kind == "box":
        width = scad.var(name=f"{prefix}_width", default=item["size"][0])
        height = scad.var(name=f"{prefix}_height", default=item["size"][1])
        depth = scad.var(name=f"{prefix}_depth", default=item["size"][2])
        bottom = center - np.asarray([0.0, 0.0, item["size"][2] / 2.0])
        return scad.make_box_rsolid(
            width=width, height=height, depth=depth,
            bottom_face_center=tuple(bottom), result_tag=f"{prefix}.body",
        )
    if kind == "sphere":
        radius = scad.var(name=f"{prefix}_radius", default=item["radius"])
        return scad.make_sphere_rsolid(radius=radius, center=tuple(center))
    axis = np.asarray(item["axis"], dtype=float)
    bottom = center - axis * (float(item["height"]) / 2.0)
    height = scad.var(name=f"{prefix}_height", default=item["height"])
    if kind == "cylinder":
        radius = scad.var(name=f"{prefix}_radius", default=item["radius"])
        return scad.make_cylinder_rsolid(
            radius=radius, height=height, bottom_face_center=tuple(bottom),
            axis=tuple(axis), result_tag=f"{prefix}.body",
        )
    if kind == "cone":
        bottom_radius = scad.var(name=f"{prefix}_bottom_radius", default=item["bottom_radius"])
        top_radius = scad.var(name=f"{prefix}_top_radius", default=item["top_radius"])
        return scad.make_cone_rsolid(
            bottom_radius=bottom_radius, top_radius=top_radius, height=height,
            bottom_face_center=tuple(bottom), axis=tuple(axis),
            result_tag=f"{prefix}.body",
        )
    raise ValueError(f"unsupported primitive: {kind}")


def compile_cadir(blueprint: dict[str, Any], output_dir: Path) -> Path:
    import simplecadapi as scad

    mesh_dir, step_dir, graph_dir = (
        output_dir / "meshes", output_dir / "step", output_dir / "cadir_graphs"
    )
    for directory in (mesh_dir, step_dir, graph_dir):
        directory.mkdir(parents=True, exist_ok=True)
    for link_index, link in enumerate(blueprint["links"]):
        graph_id = f"{safe_name(link['name'])}_cadir"

        @scad.model(graph_id=graph_id)
        def build_link() -> list[Any]:
            shapes = [
                _scad_primitive(scad, item, f"p{link_index}_{primitive_index}")
                for primitive_index, item in enumerate(link["primitives"])
            ]
            scad.capture_result(value=shapes)
            return shapes

        result = build_link()
        replayed = result.replay(strict=True)
        if not replayed:
            raise ValueError(f"strict CADIR replay returned no geometry for {link['name']}")
        filename = safe_name(link["name"])
        scad.export_stl(shapes=result.value, filename=str(mesh_dir / f"{filename}.stl"))
        scad.export_step(shapes=result.value, filename=str(step_dir / f"{filename}.step"))
        (graph_dir / f"{filename}.model.json").write_text(result.model_json, encoding="utf-8")
    return write_urdf(blueprint, output_dir)


def write_urdf(blueprint: dict[str, Any], output_dir: Path) -> Path:
    urdf_dir = output_dir / "urdf"
    urdf_dir.mkdir(parents=True, exist_ok=True)
    robot = ET.Element("robot", {"name": "blind_reconstruction"})
    for link in blueprint["links"]:
        node = ET.SubElement(robot, "link", {"name": link["name"]})
        visual = ET.SubElement(node, "visual")
        ET.SubElement(visual, "origin", {"xyz": "0 0 0", "rpy": "0 0 0"})
        geometry = ET.SubElement(visual, "geometry")
        ET.SubElement(geometry, "mesh", {
            "filename": f"../meshes/{safe_name(link['name'])}.stl",
            "scale": "0.001 0.001 0.001",
        })
    for joint in blueprint["joints"]:
        node = ET.SubElement(robot, "joint", {"name": joint["name"], "type": joint["type"]})
        ET.SubElement(node, "parent", {"link": joint["parent"]})
        ET.SubElement(node, "child", {"link": joint["child"]})
        xyz_m = [float(value) / 1000.0 for value in joint["origin_xyz"]]
        ET.SubElement(node, "origin", {
            "xyz": " ".join(f"{value:.9g}" for value in xyz_m),
            "rpy": " ".join(f"{float(value):.9g}" for value in joint["origin_rpy"]),
        })
        if joint["type"] != "fixed":
            ET.SubElement(node, "axis", {
                "xyz": " ".join(f"{float(value):.9g}" for value in joint["axis"])
            })
        if joint["type"] in {"revolute", "prismatic"}:
            ET.SubElement(node, "limit", {
                "lower": f"{float(joint['lower']):.9g}",
                "upper": f"{float(joint['upper']):.9g}",
                "effort": "1", "velocity": "1",
            })
    ET.indent(robot)
    path = urdf_dir / "model.urdf"
    ET.ElementTree(robot).write(path, encoding="utf-8", xml_declaration=True)
    return path
