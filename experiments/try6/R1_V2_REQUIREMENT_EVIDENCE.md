# Try-6.0-R1-v2 requirement-to-evidence checklist

R1-v2 is a new, isolated infrastructure reliability version. C1-v1, R0 and
R1-v1 remain frozen. No GT, formal holdout cases, C1-v2, C2 or KFDE.

- [ ] Hash-audit the three frozen prior results and record starting commit.
- [ ] Generate API schema deterministically from the canonical VFP schema; record every removed keyword/path, API evidence and local replacement.
- [ ] Pass projection, local uniqueness, signature, authority, assembly, no-repair and holdout-lock tests.
- [ ] Run exactly one full API-transport-schema compatibility preflight, retaining exact request and response/error. Stop if rejected.
- [ ] Only after preflight PASS, freeze prompt/schema/projection/model/backbone/registry/assembler/input hashes in a tracked reliability manifest.
- [ ] Run five fresh production-shaped L04 calls without retries, repair, manual selection or parameter changes; retain all attempts.
- [ ] Independently compute TSR, VSR, GAR and all semantic violation counts, plus proposal consistency with denominator 5.
- [ ] Only if representation gate is 5/5, run one 2–5-candidate non-GT E2E smoke including anchor→objective→theta→CAD sensitivity.
- [ ] Independently validate final decision, failure accounting, prior-result immutability, GT=0 and holdout lock; stop before C1-v2.
