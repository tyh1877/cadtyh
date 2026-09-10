# Try-5B0 Fast Mechanical Evaluator Report

## Outcome

PASS. One evaluator provides FAST_REPAIR_MODE and FINAL_AUDIT_MODE. No Robot A shape or frozen definition changed. Mechanical success gates passed, but the aspirational 3x full / 10x dirty targets were not met; selective Exact remains the bottleneck.

## Required answers

1. Exact 128-config evaluation: 184.243564 s.

2. FAST cold-cache: 127.790401 s.

3. FAST warm-cache: 127.566780 s.

4. Warm full speedup: 1.44x.

5. L03 dirty-set speedup: 6.82x.

6. Yes; each link is tessellated once per CAD revision.

7. Warm cache hit rate: 0.999587.

8. L0/L1 removed 4653 pair-poses.

9. Mesh/BVH produced 1887 suspicious pair-poses.

10. FAST requested 1887 selective Exact checks.

11. Exact-call reduction: 23.35%.

12. False-negative rate: 0.000000.

13. Pre-Exact suspicious false-positive rate: 0.263226; after selective Exact: 0.000000.

14. Missed Exact collisions: 0.

15. JR3 matches frozen Exact: True.

16. GCFR matches frozen Exact: True (0.914062).

17. Collision-free pose classification matches: True.

18. Repair target recall: 1.000000.

19. Repair target precision: 1.000000.

20. Interface/BICR retain the frozen deterministic definitions.

21. Dirty-set recomputed 1280 and reused 5760 pair-poses.

22. Cache invalidated only L03.

23. Suitable for refinement loop: True.

24. FINAL_AUDIT reproduces frozen conclusions: True.

25. Remaining cost is transformed BVH traversal and selective FreeCAD Exact verification.
