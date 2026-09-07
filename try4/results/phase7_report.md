# Try-4 Phase 7 report — selective repair and progressive freezing

Phase 7 implemented the T2 materializer, native FreeCAD round executor, frozen
evaluator wrapper, blackboard transition logic, selective scheduler, stagnation
handling, regression rollback and three-round stop. Every built candidate has an
independent FCStd/STEP/STL, four renders, Feature Graph, CAD IR, feature tree,
metrics, repair log, post-review and PartState.

The two-part pilot passed its development gate. R02_P02 LOCAL_REPAIR improved IoU
from 0.3114 to 0.4176 and passed the numeric gate while preserving its declared
pivot subgraph. R02_P05 REPLAN improved IoU from 0.0924 to 0.2681 and greatly
reduced distance errors, though it did not pass. Pilot geometry was archived and
was not substituted for formal outputs.

The formal scheduler executed 32 of 36 contracts; four were rejected by protected
subgraph checks. Fifteen of 32 candidates triggered frozen regression rules and
were rolled back. Every successfully declared protected subgraph remained
unchanged, yielding 100% preservation for the checks that were expressible. This
is CAD-IR subgraph preservation, not independent proof that a visible surface
region remained perceptually identical.

The largest limitation is the repair vocabulary. It can alter parameters and
recompile the existing shared recipe families, but it cannot introduce the curved
plates, irregular webs, integrated housings and linkage topology required by the
hardest parts. Repeated parameter changes therefore converge numerically without
meeting LOD or visible-feature requirements.
