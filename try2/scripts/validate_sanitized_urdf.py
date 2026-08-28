"""Reject geometry, identity, paths and non-anonymous IDs from sanitized URDF."""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

FORBIDDEN = {"visual", "collision", "geometry", "mesh", "material", "texture", "inertial"}


def validate(path: Path) -> dict:
    root = ET.parse(path).getroot(); flags = []
    if root.get("name") != "kinematic_skeleton": flags.append("ROBOT_NAME")
    for node in root.iter():
        if node.tag in FORBIDDEN: flags.append(f"FORBIDDEN_TAG:{node.tag}")
        for key, value in node.attrib.items():
            text = f"{key}={value}".casefold()
            if any(token in text for token in ("package://", ".stl", ".dae", ".obj", ".step", "\\", "/", "manufacturer")):
                flags.append(f"LEAKAGE_ATTRIBUTE:{key}")
    for node in root.findall("link"):
        if not re.fullmatch(r"L[0-9]+", node.get("name", "")): flags.append("LINK_ID")
    for node in root.findall("joint"):
        if not re.fullmatch(r"J[0-9]+", node.get("name", "")): flags.append("JOINT_ID")
    return {"valid": not flags, "leakage_flags": sorted(set(flags))}


if __name__ == "__main__":
    report = validate(Path(sys.argv[1])); print(json.dumps(report, indent=2)); raise SystemExit(0 if report["valid"] else 1)
