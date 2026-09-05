# Archive provenance

`codex_agent_v1_reclassification/` contains superseded descriptions and status
records. Their claims are withdrawn; current interpretation is in
`../results/codex_agent_v1_try3_report.md`.

The archive manifest records byte hashes at reclassification. The only subsequent
intentional change to its preserved-file list is `scripts/finalize_codex_try3.py`:
a read-only early-return guard prevents historical finalization from overwriting
the corrected report/status. The other 3,677 preserved files and all 22 frozen
method-file hashes were verified unchanged. All five archived originals match
their recorded hashes. Archive line endings are preserved by `.gitattributes`.

Raw CAD and images remain in their existing ignored run paths. The archive is
an in-place research record, not a separate backup of heavy geometry. The original
commit `8ae7fa059a99f35c4ff85238e3efe285d89ebf6a` remains in Git history.
