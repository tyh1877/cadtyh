"""Validate RobotCAD SkillCall artifacts without importing any CAD backend."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import jsonschema
ROOT=Path(__file__).resolve().parents[2]
def validate(path:Path):
 schema=json.loads((ROOT/'robotcad/schemas/skill_call_v1.schema.json').read_text())
 capabilities=json.loads((ROOT/'robotcad/capabilities/fusion_api_v1.json').read_text())
 allowed=set(capabilities['formal_allowed_skills'])
 schema_allowed=set(schema['properties']['calls']['items']['properties']['skill']['enum'])
 if allowed!=schema_allowed:raise ValueError('schema/capability skill mismatch')
 value=json.loads(path.read_text());jsonschema.validate(value,schema)
 ids=[x['call_id'] for x in value['calls']]
 if len(ids)!=len(set(ids)):raise ValueError('duplicate call_id')
 illegal=[x['skill'] for x in value['calls'] if x['skill'] not in allowed]
 if illegal:raise ValueError('unsupported formal skill(s): '+','.join(sorted(set(illegal))))
 return value
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('path',type=Path);a=p.parse_args();print(json.dumps({'calls':len(validate(a.path)['calls']),'status':'VALID'},indent=2))
