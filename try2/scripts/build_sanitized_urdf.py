"""Build anonymous kinematic-only URDF inputs for Try-2 C/D conditions."""
from __future__ import annotations

import csv
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sanitize(source: Path, output: Path) -> dict[str, int]:
    root = ET.parse(source).getroot()
    links = [node.get("name") for node in root.findall("link")]
    if any(not name for name in links):
        raise ValueError(f"unnamed link in {source}")
    mapping = {name: f"L{index}" for index, name in enumerate(links)}
    result = ET.Element("robot", {"name": "kinematic_skeleton"})
    for name in links:
        ET.SubElement(result, "link", {"name": mapping[name]})
    joints = root.findall("joint")
    for index, node in enumerate(joints):
        parent, child = node.find("parent"), node.find("child")
        if parent is None or child is None or parent.get("link") not in mapping or child.get("link") not in mapping:
            raise ValueError(f"invalid joint endpoints in {source}")
        joint = ET.SubElement(result, "joint", {"name": f"J{index}", "type": node.get("type", "fixed")})
        ET.SubElement(joint, "parent", {"link": mapping[parent.get("link")]})
        ET.SubElement(joint, "child", {"link": mapping[child.get("link")]})
        for tag in ("origin", "axis", "limit"):
            value = node.find(tag)
            if value is not None:
                ET.SubElement(joint, tag, dict(value.attrib))
    ET.indent(result)
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(result).write(output, encoding="utf-8", xml_declaration=True)
    return {"links": len(links), "joints": len(joints)}


def main() -> None:
    cases = list(csv.DictReader((ROOT / "try1/frozen_cases.csv").open(encoding="utf-8-sig")))
    rows = []
    for row in cases:
        case_id = row["case_id"]
        counts = sanitize(ROOT / "go_nogo3/data/dev15" / case_id / "urdf/model.urdf", ROOT / "try2/inputs/sanitized_urdf" / f"{case_id}.urdf")
        rows.append({"case_id": case_id, **counts})
    with (ROOT / "try2/sanitized_urdf_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("case_id", "links", "joints")); writer.writeheader(); writer.writerows(rows)


if __name__ == "__main__":
    main()
