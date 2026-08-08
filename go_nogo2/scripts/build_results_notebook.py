"""Build and execute the reproducible Go/No-Go 2 baseline-results notebook."""

from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "go_nogo2" / "notebooks" / "02_executable_baseline_results.ipynb"


def md(body: str):
    return nbf.v4.new_markdown_cell(body.strip())


def code(body: str):
    return nbf.v4.new_code_cell(body.strip())


nb = nbf.v4.new_notebook()
nb["metadata"]["kernelspec"] = {
    "display_name": "PaperTest (.venv)", "language": "python", "name": "papertest"
}
nb["metadata"]["language_info"] = {"name": "python", "version": "3.12"}
nb["cells"] = [
    md("""
# Go/No-Go 2 executable-baseline results

## tl;dr

- Direct LLM generated valid outputs for **6/10** cases; the CADIR/SimpleCADAPI
  SDK-conditioned baseline generated **9/10**.
- Neither method passed geometry, assembly, and kinematics simultaneously on
  any case (**0/10** for both).
- The frozen four-method decision remains **INCONCLUSIVE**, because ArtiCAD and
  AssemCAD are `NOT_RUN` rather than measured failures.
"""),
    md("""
## Context & Methods

Both executable methods use the same fixed 10-case dataset, six views, text
prompt, `qwen3.7-plus`, and deterministic evaluation. Direct LLM receives one
call per case. The SDK-conditioned method may make at most three calls and gets
only schema/CAD-execution errors for repair.

This is not a full reproduction of the CADIR paper: its public repository
provides SimpleCADAPI and agent-facing documentation, but not the reported
five-agent orchestrator or learned retrieval components. Metric medians below
are calculated only over successfully generated outputs; failed generations
remain explicit and are never imputed as numeric zeroes.
"""),
    code("""
from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt

root = Path.cwd()
if root.name == "notebooks":
    root = root.parents[1]
results_dir = root / "go_nogo2" / "results"
aggregate = pd.read_csv(results_dir / "aggregate_results.csv")
status = pd.read_csv(results_dir / "run_status.csv")
failures = pd.read_csv(results_dir / "failure_breakdown.csv")
summary = json.loads((results_dir / "summary.json").read_text(encoding="utf-8"))
"""),
    md("""
## Data validation

The assertions enforce the frozen denominator and make the distinction between
terminal results and `NOT_RUN` records explicit.
"""),
    code("""
expected_methods = {
    "direct_frontier_mllm", "cadir_simplecad", "articad", "assemcad"
}
assert len(status) == 40 and set(status.method) == expected_methods
assert status.groupby("method").size().eq(10).all()
assert summary["decision"] == "INCONCLUSIVE"
assert summary["terminal_case_counts"]["direct_frontier_mllm"] == 10
assert summary["terminal_case_counts"]["cadir_simplecad"] == 10
assert summary["not_run_counts"]["articad"] == 10
assert summary["not_run_counts"]["assemcad"] == 10

executed = aggregate.set_index("method").loc[
    ["direct_frontier_mllm", "cadir_simplecad"]
]
assert executed.generation_success_cases.astype(int).tolist() == [6, 9]
assert executed.attempts_total.astype(int).tolist() == [10, 16]
assert executed.simultaneous_success_cases.astype(int).eq(0).all()
executed[["terminal_cases", "generation_success_cases",
          "generation_failure_cases", "attempts_total",
          "simultaneous_success_cases"]]
"""),
    md("""
## Results

### Generation success does not imply benchmark success
"""),
    code("""
plot_data = executed[["generation_success_cases", "simultaneous_success_cases"]].copy()
plot_data.index = ["Direct LLM", "CADIR/SimpleCAD SDK"]
ax = plot_data.plot.bar(
    color=["#4C78A8", "#E45756"], edgecolor="#263238", figsize=(8, 4)
)
ax.set_title("Go/No-Go 2 results on the fixed 10-case pilot")
ax.set_xlabel("")
ax.set_ylabel("Cases")
ax.set_ylim(0, 10)
ax.tick_params(axis="x", rotation=0)
ax.legend(["Valid generated output", "All dimensions pass"], frameon=False)
plt.tight_layout()
plt.show()
plot_data
"""),
    md("""
### Successful-output metric medians

These conditional medians characterize fidelity only after generation succeeds;
they must be interpreted together with the 6/10 versus 9/10 coverage above.
Lower is better for distance/error columns; higher is better for IoU, F1, and
accuracy columns.
"""),
    code("""
metric_columns = [
    "chamfer_median_successful_outputs",
    "hd95_median_successful_outputs",
    "voxel_iou_median_successful_outputs",
    "part_f1_median_successful_outputs",
    "assembly_graph_f1_median_successful_outputs",
    "joint_type_accuracy_median_successful_outputs",
    "axis_error_degrees_median_median_successful_outputs",
    "joint_origin_error_normalized_median_median_successful_outputs",
    "link_translation_error_normalized_median_median_successful_outputs",
    "link_rotation_error_degrees_median_median_successful_outputs",
]
executed[metric_columns].T.round(4)
"""),
    md("""
### Failure patterns
"""),
    code("""
failure_view = failures[
    failures.method.isin(["direct_frontier_mllm", "cadir_simplecad"])
].pivot(index="failure_pattern", columns="method", values="case_count").fillna(0)
failure_view.astype(int).sort_index()
"""),
    md("""
## Takeaways

1. SDK conditioning plus bounded repair improves valid generation from 6/10 to
   9/10 (30 percentage points), but does not solve output fidelity.
2. The central scientific gap remains visible: neither executable baseline
   succeeds simultaneously on geometry, assembly, and kinematics.
3. The fidelity medians do not show a consistent CADIR advantage over Direct;
   the strongest observed effect is execution robustness.
4. Under frozen protocol v1, no final GO/NO-GO label is permitted until ArtiCAD
   and AssemCAD have comparable terminal runs, or the protocol is prospectively
   amended and re-frozen.
"""),
]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
client = NotebookClient(nb, timeout=300, kernel_name="papertest")
client.execute(cwd=ROOT)
nbf.write(nb, OUTPUT)
print(OUTPUT)
