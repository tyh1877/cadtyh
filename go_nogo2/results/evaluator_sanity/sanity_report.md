# Evaluator sanity report

## PASS

- GT-vs-GT is exact on all 10 cases.
- axis perturbations are monotonic in median axis_error_degrees_median: [0.0, 5.000000000092464, 10.000000001987418].
- origin perturbations are monotonic in median origin_error_normalized_median: [0.0, 0.004298737405496949, 0.008597474810993898].
- local scale perturbations are monotonic in median chamfer: [3.077756509038812e-05, 4.7553148477499525e-05].
- visual translation perturbations are monotonic in median chamfer: [3.135218755560254e-08, 7.625510289784598e-07].
- All large structural corruptions are invalid or fail simultaneous success.
- A 20% local-link scale perturbation degrades geometry metrics but can remain below the pilot's whole-robot pass thresholds; this is expected because thresholds evaluate the complete robot rather than a local manufacturing tolerance.

## Scope

All perturbations are deterministic copies of the frozen GT URDFs. `INVALID` is retained for corruptions that deliberately violate the rooted-tree contract.
