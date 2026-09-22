# Shared L04 evidence block

Both A2a conditions receive this block verbatim plus the same attached images.

- Target: physical link L04 in the supplied sanitized URDF.
- Starting artifact: the supplied frozen F0 L04 FreeCAD shape and its six
  neutral renders. The variable `f0_shape` will be available during CAD
  execution.
- Preserve the supplied J03 and J04 numerical frames, axes, limits, and
  clearances. Do not change URDF semantics.
- The deterministic execution wrapper applies the same protected cuts and the
  same frozen scaffold safeguard after the generated body is built.
- Use millimetres in FreeCAD local link coordinates.
- Hidden actuators, bearings, small fasteners, tiny holes, fillets, and
  manufacturing tolerances are outside scope.
- Produce one final answer. There is no evaluator feedback, repair call, or
  human edit.

The request also includes, verbatim, the engineering text, sanitized URDF, and
neutral numerical interface JSON. Six raw robot views and six neutral F0-link
renders are attached in the same order to both conditions.
