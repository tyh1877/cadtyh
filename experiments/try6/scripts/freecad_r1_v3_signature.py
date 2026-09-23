"""Read-only FreeCAD BREP signatures for E2E interface/dimension audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import FreeCAD as App

from freecad_r0_edit import shape_signature


def main(job):
    out=Path(job["output"]);out.mkdir(parents=True,exist_ok=True)
    doc=App.openDocument(job["fcstd"]);doc.recompute()
    names=("FrozenProximalBoreTool","FrozenMatingEnvelopeTool","FrozenScaffold","MainHousingPad","RigidGroup")
    shapes={name:shape_signature(doc.getObject(name),out/"brep") for name in names}
    sheet=doc.getObject("ParameterTable")
    width=float(str(sheet.get("housing_width_mm")).split()[0])
    result={"shapes":shapes,"parameter_table_housing_width_mm":width,"valid":all(x["valid"] for x in shapes.values())}
    App.closeDocument(doc.Name)
    (out/"signature.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"valid":result["valid"],"housing_width_mm":width}))


if __name__=="__main__":main(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
