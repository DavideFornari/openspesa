# ADR-001: Storage, processing and hosting

- **Status:** Accepted (2026-10-09).
- **Evidence:** [spikes/anac-runner.md](../spikes/anac-runner.md),
  [spikes/duckdb-wasm.md](../spikes/duckdb-wasm.md), [profiling.md](../profiling.md),
  [operations.md](../operations.md)

## Context

OpenSpesa must cost nothing to run, have no always-on server, and stay portable between
providers. Phase 0 established:

1. **ANAC blocks cloud runners** (HTTP 403 from GitHub Actions). Only a home connection
   can download. A weekly home task already mirrors the raw files to Hugging Face.
2. **ANAC's monthly delta files are upserts.** They contain new CIGs and changes to CIGs
   going back to 2007. Some changes *remove* values (745 awarded outcomes went blank).
3. **Browser queries are limited by latency, not bandwidth.** DuckDB-WASM on Hugging Face
   costs about 0.45 s per HTTP range request, and requests run one after another. An
   unsorted 16.6 MB file needed 24 requests (11 s) for a single-region query.
4. **The volume is modest.** A full year of CIG data is about 250 MB zipped and about
   1.2 GB as CSV. The whole history since 2007 should fit in a few GB of zips. A free
   public-repo runner has 4 CPUs, 16 GB of RAM and 14 GB of SSD.

## Decision

### 1. Where things live

| Layer | Contents | Location | Mutability |
|---|---|---|---|
| raw | ANAC files exactly as downloaded, plus `manifest.jsonl` | HF dataset `openspesa/raw-mirror` | append-only |
| bronze | one typed Parquet file per raw file | runner disk only | rebuilt every run |
| silver | one current row per CIG (and per entity), normalized codes | runner disk only | rebuilt every run |
| gold | tables the website reads | HF dataset `openspesa/procurement` | new version per release |
| site | static pages, no data inside | GitHub Pages | redeployed per release |

Only raw and gold are stored. Bronze and silver are rebuilt from raw on every run.

### 2. Stateless full rebuild, not incremental merges

Each build downloads every raw file listed in the manifest, checks its SHA-256, and
rebuilds bronze → silver → gold from scratch. It processes one raw file at a time
(unzip, convert to Parquet, delete the CSV), so peak disk use stays far below 14 GB.

**Why:**
- No mutable state can drift.
- Any past release can be reproduced from the manifest alone.
- Rules like the merge below can change without migrating stored data.

The cost is build time. We estimate minutes, not hours, but haven't measured it yet.

*Upgrade path:* if a full build gets too slow, cache bronze Parquet keyed by each raw
file's SHA-256 (raw files never change, so a cache entry never goes stale).

### 3. How versions of a CIG are merged into silver

- **Order:** raw files are applied in publication order, using the date of each file
  (yearly monthly files first, then deltas by their `YYYYMM01` prefix).
- **Field-level coalesce:** for each CIG and each field, silver keeps the latest
  *non-null* value. An empty value in a later file never overwrites a filled one.
- **Main CPV only** in the contract table (`flag_prevalente = '1'`). All CPVs go in a
  bridge table.

**Trade-off:** if ANAC deliberately clears a field (for example an outcome that was
withdrawn), we keep showing the old value. This is the safer error for a transparency
tool: it never hides information ANAC once published. Each gold row records the raw
file its latest value came from, so users can check.

### 4. Gold layout for browser queries

Driven by the latency finding:

- **Small summary tables** for page loads: totals per municipality, authority and
  company by year and procedure. They should be small enough to load in one request (a
  few MB at most), sorted by entity ID.
- **The large contract table split into one file per region** (for example
  `contracts/region=VEN.parquet`), plus one file for bodies with no region. A town page
  reads one regional file; it never scans the country.
- **Inside each file, rows are sorted by authority, then date**, so Parquet row-group
  statistics let DuckDB skip what a page doesn't need. Row groups are large (on the order
  of 100,000 rows) to keep the request count low. We'll tune this on real gold data.
- **No file per entity.** Hundreds of thousands of companies would exceed the file
  counts Hugging Face recommends per repository and per folder.
- **The search index is a few static JSON files split by name prefix**, built at release
  time.
- **Every browser query** sets `auto_fallback_to_full_download = false`.

### 5. Releases and versioning

- Each gold build is a Hugging Face dataset commit, tagged with a semantic version (for
  example `v0.1.0`). Each release includes a changelog and a data-quality report.
- **The site pins a tag** and reads `…/resolve/v0.1.0/…`, not `main`. Data and pages
  can't drift apart, and the URLs are immutable and cacheable.
- **Builds run** after the weekly home sync, from a scheduled GitHub Actions workflow.
  It does nothing if `manifest.jsonl` hasn't changed since the last release.

### 6. Hosting the site: GitHub Pages

Deployed from Actions in the same repository: no extra account, free for public
repositories.

- The data isn't part of the site, so GitHub Pages' 1 GB site limit doesn't apply to it.
- `noindex` for person data is set with a `<meta name="robots">` tag. GitHub Pages
  doesn't support custom HTTP headers, so we can't use `X-Robots-Tag`.
- We move to **Cloudflare Pages** if we need custom headers, more bandwidth or edge
  caching. The site is plain static files, so the move is a deploy change, not a rewrite.

### 7. Portability

Everything is plain files: zip, CSV, Parquet, JSON, plus a manifest with hashes. The site
reads data from one configurable base URL. To change provider, copy the two datasets to
any static host that supports CORS and range requests (for example Cloudflare R2 or S3),
then change that URL.

## Alternatives considered

| Option | Why not |
|---|---|
| Incremental merge into a stored silver table | Faster, but mutable state can drift, and changing a merge rule needs a migration. Our volume doesn't need it yet. |
| "Latest row wins" merge | Simpler, but it would blank 745 known outcomes in one delta alone ([profiling.md](../profiling.md)). |
| One national contract file | One file per page view means many range requests over unrelated regions: 11 s for a simple query in the spike. |
| Per-entity JSON files | Fastest page loads, but far too many files for Hugging Face, and costly to rebuild. |
| A database server (Postgres, a hosted DuckDB service) | Breaks the zero-cost and nothing-always-on constraints. |
| Downloading in GitHub Actions | ANAC blocks runners (403). |
| Cloudflare Pages from day one | Better headers and CDN, but one more account. Kept as the fallback. |

## Consequences

- The home PC stays in the loop for downloads only (see [operations.md](../operations.md)).
  Every transformation runs in public CI.
- **Phase 1 needs a one-time backfill:** the home PC downloads all yearly CIG datasets
  (2007 to 2025) once and mirrors them to `openspesa/raw-mirror`.
- Build time and peak disk use must be measured in the first Phase 1 build. The bronze
  cache is the fix if either gets close to the limits.
- Showing older values (the coalesce rule) is explained on the methodology page.

## Open questions

1. ~~Gold dataset name?~~ **Resolved:** `openspesa/procurement`.
2. ~~Missing early 2026?~~ **Resolved:** the first delta, `20260401`, contains all of
   January to March 2026 (102,538, 126,344 and 136,703 CIGs), plus updates to 2025.
   The yearly files and deltas together leave no gap.
3. **Deltas vs yearly files (still open):** does a later yearly dataset (for example `cig-2026`,
   published in 2027) replace the deltas for that year? The apply order above assumes
   the most recent file wins, field by field, either way.
