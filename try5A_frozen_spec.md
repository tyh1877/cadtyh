# Try-5A frozen coarse-stage specification

Try-5A.5 is the final coarse reconstruction baseline. The freeze preserves the
mechanical authority needed by later geometry refinement without freezing visual
shape quality.

## Frozen

The sanitized URDF remains the frame/topology authority. FK, physical/virtual
classification, Robot Plan semantics, the generic Robot Interface KB and selected
interface families, Motion-Aware Interface Contracts, rigid-group ownership,
BICR/attachment, forbidden-fusion rules, swept-clearance specifications, exact
mechanical validation, the Global Collision Graph, R0-R4 arbitration, Progressive
Freezing, the Meaningfulness Gate, and virtual filtering are immutable.

The authoritative Try-5A.5 Robot Plan, interface contracts, rigid-group states,
coarse Link CAD evidence, mechanical metrics, GCFR/JR3/BICR results, collision
graph, source hashes, and CAD artifact hashes are indexed by
`experiments/try5A/results/try5a_frozen_coarse_stage/manifest.json`. Heavy CAD is
not copied; its existing files are identified and checked by hash.

## Allowed in Try-5B

Try-5B may refine body geometry realization, body-family-to-CAD logic, link-local
topology/feature graphs, visual grounding, profiles/sections/lofts/shells, and
geometry-detail repair. It must do so in the existing Try5 pipeline.

## Non-regression contract

After refinement, URDF frames and interface contracts must be unchanged; BICR and
the corresponding per-joint JR3 must remain 100%; floating bodies, forbidden
fusion, virtual solids, and meaningless patches must remain zero; swept clearance
must remain intact; and GCFR must stay at least 90% with no absolute drop greater
than two percentage points from the 91.40625% baseline. Any mechanical hard-gate
failure means `ROLLBACK`, not acceptance of the candidate.

Revalidate the frozen baseline with:

```powershell
.venv/Scripts/python.exe experiments/try5A/scripts/validate_frozen_coarse_stage.py
```

Gate a later refinement by adding
`--candidate-results <path-to-result-directory>`. Heavy CAD files are intentionally
ignored by Git: when they are present the command verifies every file hash; when
they are absent it reports `MANIFEST_ONLY` and validates the committed CAD manifest
plus all semantic evidence. Add `--require-artifacts` when physical CAD retention
is mandatory for that checkout.
