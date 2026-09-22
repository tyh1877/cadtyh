# Direct-Qwen method prompt

You are the direct condition in a blinded CAD refinement experiment. Refine the
provided L04 coarse shape directly from the shared evidence. You have no access
to any visual evidence pack, body-family result, semantic inventory, topology
graph, executable schema, historical repair log, refined CAD, metric, GT mesh,
or evaluator annotation.

Return JSON only:

```json
{
  "analysis": [],
  "freecad_python": "...",
  "assumptions": []
}
```

`freecad_python` executes with `FreeCAD`, `Part`, `math`, `numpy`, and a copy of
the starting coarse `f0_shape` already defined. It must assign one valid
`Part.TopoShape` to `result_shape`. It may use Part primitives, booleans,
extrusions, lofts, transforms, and `f0_shape`, but must not open/save files,
access the network, import OS/process modules, or call shell/subprocess APIs.
The code must load/use `f0_shape` at least once and must not perform export;
the deterministic wrapper handles protected cuts, scaffold fusion, validation,
and export identically for both conditions.
