# TODO

## Phase 0: Foundations (12 to 25 October 2026)

- [x] Scaffold repo: LICENSE, README, CONTRIBUTING, CI, pre-commit
- [x] Inspect the ANAC open data portal → `docs/sources/anac.md`
- [x] Ingestion module for one month of ANAC CIG data, with manifest (URL, timestamp, hash)
- [x] Dataset license: CC BY-SA 4.0 (ANAC is ShareAlike); to confirm in the Gate B review
- [ ] Spike: ANAC download from a GitHub Actions runner (Gate A); fallback if blocked
- [ ] Spike: DuckDB-WASM querying Parquet on Hugging Face from a static page
- [ ] Profile three months of CIG data → `docs/profiling.md`
- [ ] ADR-001 storage and hosting
- [ ] ADR-002 entity keys and natural-person detection
- [ ] Check the name OpenSpesa on GitHub, PyPI and domain registries
- [ ] Open a Discussion on DoveVannoINostriSoldi

## Not now

- dbt project, Astro site, Dockerfile, Makefile: added when a step needs them.

## Session log

- 2026-10-09: scaffold.
