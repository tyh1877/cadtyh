# Try-3 FreeCAD Full Workflow Protocol

## Objective

Validate whether the complete Try-3 architecture can improve robot CAD
reconstruction when the backend is FreeCAD instead of Fusion.

The formal input condition remains fixed:

```text
Multi-view Images + Engineering Text + Sanitized Kinematic-only URDF
```

The formal output target is editable FreeCAD CAD:

```text
per-link FCStd/STEP/STL + full assembly FCStd/STEP/STL + deterministic metrics
```

## Architecture

The workflow must not be simplified into isolated link reconstruction.

```text
Multi-view Images
+ Engineering Text
+ Sanitized Kinematic-only URDF
        ↓
Global-to-Local Visual Evidence Agent
        ↓
Mechanical Embodiment Architect
        ↓
Interface Engineer
        ↓
Per-link Mechanical CAD Engineer Agents
        ↓
RobotCAD Skill Layer
        ↓
FreeCAD Backend Executor
        ↓
Assembly Integration
        ↓
Deterministic Evaluation
```

## Backend amendment

The original Try-3 protocol used Fusion MCP/API. This FreeCAD version changes
only the backend executor:

```text
Fusion MCP/API -> FreeCADCmd + FreeCAD Python API
```

The upstream IR, skills, agent roles, interface-first planning, and evaluation
requirements remain in scope.

MCP is not part of the formal acceptance for this experiment. A future FreeCAD
MCP adapter may replace the backend adapter only if it preserves the same
schemas and execution logs.

## Method versions

### V0: Try-2-style baseline on FreeCAD

V0 establishes the FreeCAD baseline. It uses the same input condition but does
not add full mechanical embodiment or interface-first planning.

### V1: Global-to-local + per-link planning

V1 adds visual evidence packets and per-link CAD planning, but not the full
Mechanical Embodiment Plan or Interface Graph.

### V2: Full Try-3 core method

V2 uses the full workflow:

```text
Visual Evidence -> MEP -> Interface Graph -> Per-link CAD Engineers -> Skills -> FreeCAD -> Assembly
```

## Hard prohibitions

- Do not use GT mesh, STEP, CAD, collision mesh, visual mesh, segmentation, or
  product identity as planner input.
- Do not use unsanitized URDF.
- Do not use GT part segmentation to generate crops.
- Do not replace TrySet cases based on results.
- Do not silently reuse stale downstream artifacts after an upstream failure.
- Do not use AI Judge as a formal score.
- Do not add an automatic targeted repair loop in Try-3. Verification records
  failures; Try-4 may study repair.

## Stale artifact rule

Every stage output must include:

- `stage`
- `status`
- `input_hashes`
- `schema_version`
- `created_at`
- `producer`

If a stage fails, downstream artifacts for that case/version must be marked
`STALE_UPSTREAM_FAILURE` or removed from the current run index. They must not be
executed or evaluated as current artifacts.

## Completion gate

The experiment is not complete until the requirement evidence checklist is
fully audited and the final report answers all Try-3 research questions:

- RQ1: Does global-to-local visual grounding improve fine-grained robot geometry?
- RQ2: Does explicit mechanical embodiment and interface-first planning reduce
  primitive simplification and assembly disconnection?
- RQ3: Can robot-specific CAD skills translate mechanical plans into reliable
  editable FreeCAD features?

