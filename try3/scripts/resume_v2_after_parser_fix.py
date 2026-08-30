"""Resume only the unissued V2 blueprint stage after a recorded parser failure.

This preserves the original visual and MEP responses, archives the failed
manifest, and makes exactly the one downstream CAD-blueprint request that had
not been reached. It is not a retry of either earlier model call.
"""
from __future__ import annotations
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'try3' / 'scripts')]
from generate_try3_plans import (VIEWS, content, enforce, extract_json, invoke,
                                  load_glm, skeleton, validate_plan)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', required=True)
    args = parser.parse_args()
    run = ROOT / 'try3' / 'runs' / 'V2' / args.case
    manifest_path = run / 'manifest.json'
    prior = json.loads(manifest_path.read_text())
    if prior['status'] != 'FAILURE' or prior['calls'] != 2:
        raise RuntimeError('resume requires the recorded two-call V2 parser failure')
    history = json.loads((run / 'raw_history.json').read_text())
    if [x['stage'] for x in history] != ['visual_evidence', 'mep_interface_feature_plan']:
        raise RuntimeError('resume source history is not the expected two-stage record')

    packet = json.loads((ROOT / 'try1' / 'inputs' / 'image_text_v1' / f'{args.case}.json').read_text())
    links, joints = skeleton(ROOT / 'try2' / 'inputs' / 'sanitized_urdf' / f'{args.case}.urdf')
    urdf = (ROOT / 'try2' / 'inputs' / 'sanitized_urdf' / f'{args.case}.urdf').read_text()
    evidence = json.loads((run / 'visual_evidence.json').read_text())
    plan = validate_plan(extract_json(history[1]['response']), joints)
    (run / 'mechanical_embodiment_plan.json').write_text(json.dumps(plan['mep'], indent=2))
    (run / 'interface_graph.json').write_text(json.dumps(plan['interfaces'], indent=2))
    (run / 'feature_graph.json').write_text(json.dumps(plan['features'], indent=2))

    shutil.copy2(manifest_path, run / 'manifest_attempt_01_parser_failure.json')
    cfg = load_glm(); client = cfg.create_client()
    plan_context = '\nSanitized URDF:\n' + urdf + '\nVisual evidence:\n' + json.dumps(evidence, separators=(',', ':'))
    plan_context += '\nMEP/Interface/Feature plan:\n' + json.dumps(plan, separators=(',', ':'))
    system = 'Return JSON only Robot CAD blueprint. Instantiate every anonymous URDF link exactly once. URDF joints are binding and will be overwritten deterministically, so focus on detailed exterior link primitives: housings, tapered bodies, flanges, recesses and rounded transitions visible in the evidence. Each link may emit at most 8 base primitives and each primitive must contain only its required geometry fields (no primitive_id, notes, geometry wrapper, or extra metadata). Put extra detail into the Feature Graph plan, not the primitive list.'
    raw, usage = invoke(client, cfg.model, system, content(packet, plan_context, run / 'crops' / 'contact_sheet.png'))
    history.append({'stage': 'cad_blueprint_resumed_after_parser_fix', 'response': raw, 'usage': usage})
    total = dict(prior['budget'])
    for key in total: total[key] += usage[key]
    status, error = 'SUCCESS', None
    try:
        blueprint = enforce(raw, links, joints)
        (run / 'blueprint.json').write_text(json.dumps(blueprint, indent=2))
    except Exception as exc:
        status, error = 'FAILURE', f'{type(exc).__name__}: {exc}'
    (run / 'raw_history.json').write_text(json.dumps(history, indent=2))
    manifest_path.write_text(json.dumps({
        'case_id': args.case, 'version': 'V2', 'status': status, 'model': cfg.model,
        'calls': len(history), 'budget': total, 'error': error,
        'resume_of': 'manifest_attempt_01_parser_failure.json',
        'resume_reason': 'implementation parser fix; retained the two original model responses'
    }, indent=2))
    print(args.case, status)


if __name__ == '__main__':
    main()
