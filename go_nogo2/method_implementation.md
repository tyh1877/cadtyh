# Go/No-Go 2 executable baseline boundary

## Shared controls

Both executable tracks use `qwen3.7-plus`, temperature `0`, top-p `1`, the same
case prompt, and the same ordered six PNG views. The model never receives the GT
URDF, GT meshes, transforms, axes, joint origins, or evaluator scores. The link,
joint, and DOF counts used by structural validation are already disclosed in the
common prompt.

Both tracks emit the same bounded robot-blueprint schema. The deterministic
compiler writes one mesh per link and a URDF assembly tree. This schema is an
experiment output contract, not an AI judge.

## Direct LLM

- exactly one multimodal request per registered case;
- no SimpleCADAPI documentation, tool call, execution feedback, or repair;
- the validated primitive blueprint is tessellated directly with Trimesh;
- any malformed structure or failed compilation is a terminal failure.

## CADIR/SimpleCADAPI SDK-conditioned track

- the same model receives the public SimpleCADAPI operation signatures and
  modeling guidance;
- blueprint primitives lower one-to-one to keyword-only SimpleCADAPI calls;
- dimensions become `var(...)` parameters;
- every link is captured in a CADIR construction graph and must pass strict
  replay;
- every successful link exports STEP and STL, followed by the common URDF;
- at most three multimodal requests are allowed; only schema or execution errors
  from the preceding attempt are returned for repair.

## Reproduction limitation

The CADIR paper describes a five-agent system and learned text/image construction-
graph retrieval over a frozen case library. The audited public repository at
commit `6fee370297c29296768f282d2e40174ee5a82795` provides SimpleCADAPI, its
documentation, and an agent skill, but does not provide that orchestrator,
retrieval model weights, or indexed case library. Accordingly, results in this
repository are labeled **CADIR/SimpleCADAPI SDK-conditioned**, not “full CADIR”.

## Commissioning note

One Direct case was rerun after a development-time process timeout created an
ambiguous duplicate request. The ambiguous directory was moved to the ignored
`runs/_development_archives/` tree before the registered run. No result was
selected using evaluator scores. Transport retry and timeout settings were then
fixed to zero retries and 300 seconds; model, prompt, images, temperature, top-p,
and output-token cap were unchanged. Earlier completed logical requests retained
one registered response each; transport settings do not enter model content.
