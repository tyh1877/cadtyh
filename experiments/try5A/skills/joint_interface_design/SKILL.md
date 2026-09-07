---
name: joint-interface-design
description: Create one authoritative shared interface contract per URDF joint, consumed by both parent and child link plans in later interface-first CAD.
---

# Joint Interface Design

Create exactly one contract per joint. Copy joint type, origin, axis, limits and
shared frame from L0 without visual modification. Derive parent and child port
envelopes from both adjacent L1 link envelopes. Record coaxiality/connectivity,
gap, clearance and protected regions.

Every contract must include hashes and exact values consumed from L0 and L1.
Uncertain visual structure may select a simpler general interface family, but must
not invent bearings, reducers, motors or hidden shafts.
