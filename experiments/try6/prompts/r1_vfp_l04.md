You are proposing *visible* structural features for the L04 link only. This is a visual feature proposal, not a CAD program or complete engineering graph.

Use the supplied engineering description, six raw robot views, and six neutral F0 renders. Identify whether the following three executable, externally supported feature classes are visible: `main_housing`, `pocket`, `profile_transition`. Propose each class once only if supported by those views. Do not invent bearings, hidden cavities, motors, fasteners, bolt patterns, threads, or manufacturing completion. If a required class is not visually supportable, omit it rather than hallucinating; the system will record a failed semantic gate.

For each proposed feature, choose a local_name based on appearance, cite evidence_views, and emit the semantic roles below. A pocket's axial extent is called `length`; its transverse width is derived by the current CAD infrastructure and is not a separate R1 parameter. Do not output dimensions.

- `main_housing`: roles `width`, `height`, `depth`; no relation.
- `pocket`: roles `length`, `depth`; relation `cuts_into` → `main_housing`.
- `profile_transition`: roles `length`, `distal_width`, `distal_height`; relation `transitions_from` → `main_housing`.

Do not output system-owned parameter IDs, canonical feature IDs, joint IDs, joint axes/origins, interface geometry, KFDG parameter_refs, FreeCAD commands, or GT data. Those are authoritative system responsibilities. Return exactly one JSON object conforming to the VFP schema; no wrapper, markdown, or commentary.
