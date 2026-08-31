# Operation-plan Pilot Report

Decision: PASS

## Aggregate

- links_total: 6
- schema_valid_links: 6
- links_with_5plus_ops: 6
- links_with_2plus_nonprimitive_ops: 5
- links_with_interface_constraints: 6
- links_with_gt_ack: 6
- pass: True

## Per-link results

| case | link | status | ops | unique ops | nonprimitive ops | executable now | interface constraints |
|---|---|---:|---:|---:|---:|---:|---:|
| `dev_arm-dcc2b0ce1e` | `L2` | SUCCESS | 13 | 10 | 4 | 11 | 2 |
| `dev_arm-dcc2b0ce1e` | `L3` | SUCCESS | 15 | 8 | 2 | 11 | 2 |
| `dev_arm-dcc2b0ce1e` | `L4` | SUCCESS | 10 | 9 | 4 | 7 | 2 |
| `dev_arm-ab15a75247` | `L0` | SUCCESS | 8 | 7 | 3 | 7 | 1 |
| `dev_arm-ab15a75247` | `L2` | SUCCESS | 10 | 9 | 3 | 7 | 2 |
| `dev_arm-ab15a75247` | `L4` | SUCCESS | 9 | 7 | 1 | 7 | 1 |

## Interpretation

This pilot evaluates upstream CAD operation planning only. Passing means the next Try-3 revision should regenerate operation plans and then extend Fusion execution coverage for the operation subset the model actually uses. It does not by itself prove geometry quality against GT mesh.
