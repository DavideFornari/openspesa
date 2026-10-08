# TODO

## Phase 0: Foundations (12 to 25 October 2026)

- [x] Scaffold repo: LICENSE, README, CONTRIBUTING, CI, pre-commit
- [x] Inspect the ANAC open data portal → `docs/sources/anac.md`
- [x] Ingestion module for one month of ANAC CIG data, with manifest (URL, timestamp, hash)
- [x] Dataset license: CC BY-SA 4.0 (ANAC is ShareAlike); to confirm in the Gate B review
- [x] Spike: ANAC download from a GitHub Actions runner → **blocked (403)**, see
      `docs/spikes/anac-runner.md`
- [ ] **Decide:** fallback design (home download → HF raw mirror → CI builds)
- [ ] Spike: DuckDB-WASM querying Parquet on Hugging Face from a static page
- [ ] Profile three months of CIG data → `docs/profiling.md`
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
