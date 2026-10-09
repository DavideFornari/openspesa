# TODO

## Phase 0: Foundations (12 to 25 October 2026)

- [x] Scaffold repo: LICENSE, README, CONTRIBUTING, CI, pre-commit
- [x] Inspect the ANAC open data portal → `docs/sources/anac.md`
- [x] Ingestion module for one month of ANAC CIG data, with manifest (URL, timestamp, hash)
- [x] Dataset license: CC BY-SA 4.0 (ANAC is ShareAlike); to confirm in the Gate B review
- [x] Spike: ANAC download from a GitHub Actions runner → **blocked (403)**, see
      `docs/spikes/anac-runner.md`
- [x] Fallback: weekly home sync (Task Scheduler) → HF `openspesa/raw-mirror`, staleness
      alert in CI → `docs/operations.md`
- [ ] Phase 1: CI build reads raw files from `openspesa/raw-mirror` and checks the hashes
      in `manifest.jsonl`
- [ ] Track snapshot datasets (`aggiudicatari`, `stazioni-appaltanti`): their files keep
      the same name when republished, so `download` must compare `Last-Modified` first
- [x] Spike: DuckDB-WASM querying Parquet on Hugging Face → works with
      `auto_fallback_to_full_download=false`; latency per request is the limit, see
      `docs/spikes/duckdb-wasm.md`
- [x] Profile Q1 2025 + one delta → `docs/profiling.md` (deltas are upserts; ESITO can
      vanish; 3 authorities with personal tax codes; a few lots dominate totals)
- [ ] Profile `aggiudicatari` (winners' tax codes) before finalizing ADR-002
- [ ] ADR-001 storage and hosting
- [ ] ADR-002 entity keys and natural-person detection
- [ ] Check the name OpenSpesa on GitHub, PyPI and domain registries
- [ ] Open a Discussion on DoveVannoINostriSoldi

## Not now

- dbt project, Astro site, Dockerfile, Makefile: added when a step needs them.

## Session log

- 2026-10-09: scaffold, ANAC ingester (one month, manifest), portal notes, Gate A spike
  (runners get 403). Dataset license set to CC BY-SA 4.0. Next: decide fallback, then
  profiling (3 months) and the DuckDB-WASM spike.
- 2026-10-09 (cont.): HF org `openspesa` and dataset `openspesa/spike` set up; DuckDB-WASM
  spike done. Next: decide fallback, profiling, ADR-001 and ADR-002.
- 2026-10-09 (cont.): fallback built. `sync cig` mirrored 7 monthly delta files (669 MB) to
  `openspesa/raw-mirror`, hashes verified; weekly task "OpenSpesa ANAC sync" registered
  (Mondays 19:00). Found that the ANAC API also needs an `Accept` header. Next: profiling,
  ADR-001, ADR-002.
- 2026-10-09 (cont.): profiling done (`docs/profiling.md`, `scripts/profile_cig.py`),
  partita IVA check-digit validator in `pipeline/normalize`. Next: ADR-001, then profile
  `aggiudicatari` and write ADR-002.
