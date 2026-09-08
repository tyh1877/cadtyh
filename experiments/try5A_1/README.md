# Try-5A.1 — Collision-Aware Coarse Body Planning

C0 is the frozen Try-5A A2 baseline. C1 applies collision-aware body envelopes to
C0 collision sources while holding every joint interface fixed. C2 adds one bounded
visual coarse-morphology pass. Phase 1–10 are complete.

The result is partial success: C1 reduced exact B-Rep collision events and volume
with no interface regression, but C2's visual recovery caused a collision-volume
rebound and did not make any sampled sweep collision free. Generated CAD and raw
collision caches are intentionally untracked; use the scripts to regenerate them.
