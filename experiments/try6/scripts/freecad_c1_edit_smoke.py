"""Check native parameter-sheet edit and recompute without changing formal CAD."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import FreeCAD as App


def main():
    source=Path(sys.argv[1]).resolve(); output=Path(sys.argv[2]).resolve()
    doc=App.openDocument(str(source))
    sheet=doc.getObject("ParameterTable"); final=doc.getObject("RigidGroup")
    if sheet is None or final is None: raise RuntimeError("feature-history table or final group missing")
    original=float(final.Shape.Volume)
    old_depth=float(sheet.get("B8").split()[0])
    new_depth=old_depth+0.3 if old_depth<=8.6 else old_depth-0.3
    sheet.set("B8",f"{new_depth} mm")
    doc.recompute()
    changed=float(final.Shape.Volume)
    valid=not final.Shape.isNull() and final.Shape.isValid()
    expressions=[str(pair) for obj in doc.Objects for pair in getattr(obj,"ExpressionEngine",[])]
    names=["housing_width_mm","housing_height_mm","proximal_section_length_mm","transition_length_mm","distal_width_mm","distal_height_mm","recess_length_mm","recess_depth_mm","fillet_radius_mm"]
    bound={name:any(name in expression for expression in expressions) for name in names}
    if not valid or abs(changed-original)<=1e-6 or not all(bound.values()):
        raise RuntimeError(json.dumps({"valid":valid,"original":original,"changed":changed,"bound":bound}))
    output.parent.mkdir(parents=True,exist_ok=True)
    doc.saveAs(str(output))
    App.closeDocument(doc.Name)
    print(json.dumps({"status":"PASS","edited_parameter":"recess_depth_mm","original_value_mm":old_depth,"edited_value_mm":new_depth,"original_volume_mm3":original,"edited_volume_mm3":changed,"all_nine_parameters_bound":all(bound.values()),"bound":bound},indent=2))


if __name__=="__main__": main()
