# Try-5A.2 Phase 1–3 — corrected D0 evaluation

D0 is an immutable reference to Try-5A.1 C1. No C1 CAD, body parameters or interfaces were regenerated.

## Corrected physical validity

The prior 100% Connected Joint Rate and 0 Floating Link Rate are **logical port-frame metrics**. They do not establish physical body-to-carrier attachment. The strict evaluator finds 20 physical carriers, zero valid attachment paths and BICR = 0%. 18 carriers geometrically overlap their body but remain separate final B-Rep solids without Boolean union, a declared rigid multi-body contact, or connector geometry; these are not valid attachment under the frozen protocol.

Two genuinely separated physical carriers are L01/IF_J01 (3.000 mm) and L08/IF_J07 (2.275 mm). The J10 path is excluded because its peer L11 is a virtual tool-center frame. L11 was nevertheless generated as an independent C1 solid, so historical raw Spurious Virtual Geometry Count is 1; the new filter removes it from physical exports, render and collision populations, yielding 0.

## Collision baseline

After excluding virtual L11, exact D0 evaluation contains 715 pair evaluations, 130 true collision events, 313085.5 mm³ intersection volume and 0% sweep-free pose rate. Narrow-phase errors are 0.

## Stop decision

D0 fails the Interface/Attachment hard gate: BICR is 0%, attachment-qualified body floating rate is 100%, and two physical carriers have a positive gap. The evaluator and virtual filter are now adequate to support Phase 4–8, but D1 must not begin until the required Phase 1–3 review is accepted.
