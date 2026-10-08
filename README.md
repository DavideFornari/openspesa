# OpenSpesa

A free, open source explorer of Italian public procurement. For any town, contracting
authority or company it shows who received public money, for what, and through which
procedure, with links to the original sources and a few explainable statistical indicators.

It links ANAC contract data (CIG) to projects and funds (CUP, OpenCoesione, PNRR) through
their shared keys.

> **Status:** Phase 0 (foundations). Nothing is published yet. See [TODO.md](TODO.md).

## How it works

Nothing runs between updates, so it costs nothing to host:

- A scheduled GitHub Actions job downloads source files and rebuilds the data.
- The data is published as Parquet files on Hugging Face Datasets.
- A static website queries those files directly in your browser with DuckDB-WASM.

Data moves through four layers: **raw** (files as downloaded, never edited) → **bronze**
(typed) → **silver** (cleaned, normalized identifiers) → **gold** (entities, facts, indicators).

## Principles

- **Explainable links.** Records are joined only on validated codes (CIG, CUP, tax codes),
  never on names.
- **Privacy by design.** Natural persons (16-character tax codes) are detected; their tax
  codes are never published and they have no standalone pages.
- **Neutral language.** Indicators are statistical signals that deserve a closer look, never
  accusations.

## Repository layout

```
pipeline/     Python package: ingest, normalize, resolve, publish
tests/        offline unit tests and small fixtures
docs/         ADRs, methodology, profiling
.github/      CI workflows
```

`transform/` (dbt-duckdb) and `web/` (Astro) are added when Phase 1 needs them.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pre-commit install
uv run pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Related projects

[DoveVannoINostriSoldi](https://github.com/Italian-Builders-Org) covers Italian public
spending broadly. OpenSpesa aims to be a compatible, deep procurement layer alongside it.

## License

- Code: [AGPL-3.0](LICENSE).
- Published dataset: CC BY 4.0, with attribution to each original source (ANAC,
  OpenCoesione, and others) kept in the dataset metadata.
