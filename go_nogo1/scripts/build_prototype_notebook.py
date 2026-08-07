"""Build the reproducible screenshot-defined Go/No-Go 1 audit notebook."""

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "03_prototype_feasibility_audit.ipynb"


def md(text):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text):
    return nbf.v4.new_code_cell(text.strip())


nb = nbf.v4.new_notebook()
nb["metadata"]["kernelspec"] = {"display_name": "Paper .venv", "language": "python",
                                    "name": "python3"}
nb["metadata"]["language_info"] = {"name": "python", "version": "3.12"}
nb["cells"] = [
    md("""
# Go/No-Go 1: 20-case Benchmark Feasibility Audit

## tl;dr

The screenshot-defined experiment is **GO**: 17 of the frozen 20 prototypes are
complete, exceeding the required 15. Failures remain in the denominator and are
reported individually. This proves a small Mesh+URDF evaluation prototype is viable;
it does not prove the future Benchmark-80 is release-ready.
"""),
    md("""
## Context & Methods

Twenty cases were chosen without complexity fields: one per manufacturer, then a
second case in stable order. A complete case requires mesh quality, URDF integrity,
Mesh-URDF/multi-pose consistency, deterministic evaluator smoke tests, six renders,
a text prompt, and completed visual review.

### Key Assumptions

- The denominator remains 20 even when a case fails.
- A per-case mesh reference rate below 90% is a failure.
- Joint-axis plausibility uses a conservative AABB-distance diagnostic; it is a
  screening test, not proof of mechanical correctness.
- Manual review only checks obvious breakage, explosion, or proxy-only geometry.
"""),
    code("""
from pathlib import Path
import json
import pandas as pd

root = Path.cwd()
if root.name == "notebooks":
    root = root.parent
results = root / "results" / "prototype_feasibility"
audit = pd.read_csv(results / "case_audit.csv")
summary = json.loads((results / "summary.json").read_text(encoding="utf-8"))
assert len(audit) == 20 and audit.entity_id.nunique() == 20
summary["decision"]
"""),
    md("""
## Data

The audit grain is one robot entity. All cases have source, URDF, six render paths,
and prompt/evaluator evidence in the case-level table.
"""),
    code("""
pd.DataFrame({
    "measure": ["Frozen denominator", "Manufacturers", "Automated complete",
                "Visual reviews", "Final complete"],
    "value": [summary["denominator"], summary["prototype_manufacturers"],
              summary["automated_complete_cases"], summary["visual_reviews_completed"],
              summary["complete_cases"]],
})
"""),
    md("""
## Results

Every global criterion must pass. Passing 15 cases is necessary but is not used to
hide failures in readability, valid-case URDF/FK, evaluator, or multimodal checks.
"""),
    code("""
pd.DataFrame([
    {"criterion": criterion, "pass": passed}
    for criterion, passed in summary["criterion_results"].items()
])
"""),
    code("""
audit.loc[~audit.complete_case, [
    "prototype_index", "manufacturer", "name", "mesh_quality_pass",
    "mesh_urdf_consistency_pass", "visual_review_pass", "failures"
]].sort_values("prototype_index")
"""),
    code("""
gate_columns = ["mesh_quality_pass", "urdf_quality_pass",
                "mesh_urdf_consistency_pass", "evaluator_pass",
                "multimodal_pass", "visual_review_pass"]
pd.DataFrame({
    "gate": gate_columns,
    "passed_cases": [int(audit[column].fillna(False).sum()) for column in gate_columns],
    "denominator": 20,
})
"""),
    md("""
## Takeaways

1. The final result is **17/20 complete: GO** under the frozen ≥15 rule.
2. Gen3 fails because one end-effector STL is empty and its reference-readability
   rate is 88.9%; PUMA 560 fails the conservative joint-axis plausibility check;
   PhantomX Pincher fails visual review as box-proxy dominated.
3. A resolver defect discovered during review was fixed: ambiguous short package
   URIs now prefer the mesh nearest the current URDF, and Collada scene transforms
   are applied before URDF transforms.
4. Identity evaluator inputs return exact CD/HD95=0 and IoU/F1=1, while synthetic
   corruption is detected for every case.
5. The result supports continuing to evaluator hardening and controlled-set design;
   it is not evidence that licenses, leakage, or baseline execution are complete.
"""),
]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUTPUT)
print(OUTPUT)
