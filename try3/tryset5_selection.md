# TrySet-5-v1 selection

This set was selected before any Try-3 V1/V2 output is generated. It is a
development-only method set sampled from the frozen 15-case Try-1/Try-2
development corpus, with no result-driven replacement permitted.

| Tier | Case | Why it is included |
|---|---|---|
| Easy | `dev_arm-ab15a75247` | Compact four-DOF serial arm; exercises all pipeline and Fusion save/rebuild gates with a small component count. |
| Medium | `dev_arm-4c7b408826` | Industrial serial arm with long links and visible elbow/wrist transitions. |
| Medium | `dev_arm-dcc2b0ce1e` | Distinct industrial geometry style and link arrangement; tests generalization beyond the Fanuc-style case. |
| Hard | `dev_arm-43fa322555` | Seventeen-link system with compact curved housings and fixed-link detail around the wrist. |
| Hard | `dev_arm-551a9c392e` | Twenty-one-link chain that stresses multi-component integration, interface preservation and high-detail embodiment. |

The five cases cover five manufacturers, 5/10/10/17/21 links, and different
housing styles. Model identity remains absent from Try-3 inputs.
