"""Freeze evaluator-only coarse geometry code and source mesh hashes."""
import hashlib,json,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';SRC=ROOT/'go_nogo1/sources/urdf_files_dataset/urdf_files/robotics-toolbox/xacro_generated/interbotix_descriptions/urdf/px100.urdf';meshroot=SRC.parent.parent/'meshes/meshes_px100'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
meshes=sorted({meshroot/Path(x.attrib['filename']).name for x in ET.parse(SRC).getroot().findall('link/visual/geometry/mesh')});out={'frozen_at':datetime.now(timezone.utc).isoformat(),'before_coarse_metrics':True,'evaluator_sha256':sha(HERE/'scripts/evaluate_coarse_geometry.py'),'source_urdf_sha256':sha(SRC),'evaluator_only_meshes':{str(p.relative_to(ROOT)):sha(p) for p in meshes}};(HERE/'results/coarse_evaluation_snapshot.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'meshes':len(meshes)}))

