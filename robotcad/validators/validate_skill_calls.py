"""Validate RobotCAD SkillCall artifacts without importing any CAD backend."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import jsonschema
ROOT=Path(__file__).resolve().parents[2]
def validate(path:Path):
 schema=json.loads((ROOT/'robotcad/schemas/skill_call_v1.schema.json').read_text())
 value=json.loads(path.read_text());jsonschema.validate(value,schema)
 ids=[x['call_id'] for x in value['calls']]
 if len(ids)!=len(set(ids)):raise ValueError('duplicate call_id')
 return value
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('path',type=Path);a=p.parse_args();print(json.dumps({'calls':len(validate(a.path)['calls']),'status':'VALID'},indent=2))
