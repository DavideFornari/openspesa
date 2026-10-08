# Spike: DuckDB-WASM querying Parquet on Hugging Face

**Result (2026-10-09): works, with one required setting. Request latency, not bandwidth,
is the constraint to design around.**

Test page: [`duckdb-wasm.html`](duckdb-wasm.html). Serve it with
`uv run python -m http.server 8765 --directory docs/spikes` and open
`http://localhost:8765/duckdb-wasm.html`.

Data: [`openspesa/spike`](https://huggingface.co/datasets/openspesa/spike),
`cig_2025_01.parquet` (112,879 rows, 61 string columns, 16.6 MB, zstd, 6 row groups of
20,000 rows). DuckDB-WASM `1.33.1-dev57.0` (DuckDB v1.5.4) from jsDelivr, Chrome.

## CORS and range requests: OK

- `huggingface.co/.../resolve/main/<file>` answers `302` to a CDN (`*.cdn.hf.co`). Both
  hops send `Access-Control-Allow-Origin` and allow the `Range` header.
- The CDN answers `Range` requests with `206` and exposes all headers
  (`Access-Control-Expose-Headers: *`), so the browser can read `Content-Range`.
- No account or token is needed to read a public dataset.

## Required: `set auto_fallback_to_full_download = false`

DuckDB-WASM loads the `httpfs` extension for `https://` URLs. With its default settings it
sends a HEAD request and then **downloads the whole file**, even though ranges work.
Turning the fallback off makes it fetch only the byte ranges it needs:

```sql
load httpfs;
set auto_fallback_to_full_download = false;
```

The `filesystem` options of `db.open()` (`reliableHeadRequests`, `allowFullHttpReads`)
have no effect here: they apply to DuckDB-WASM's JavaScript file system, which `httpfs`
bypasses.

## Measurements

Home connection in Italy, CDN location `aws-eu-west-3` (Paris), new DuckDB instance per run.

| Query | Default (full download) | With the setting |
|---|---|---|
| `count(*)` | 1 GET, 16.6 MB, ~7.5 s | 2 range GETs, 89 KB, 1.3 s |
| Group by one column | (already cached) | 6 range GETs, 23 KB, 2.9 s |
| Veneto filter, 3 columns, top 10 | (already cached) | 24 range GETs, 1.3 MB, **11 s** |

Each range request takes about 0.45 s and they run **one after another**: every request
goes through the Hugging Face redirect, then the CDN. Bytes barely matter; the number of
requests does.

## Consequences for the design (input for ADR-001)

1. **Always set `auto_fallback_to_full_download = false`.**
2. **Sort big tables by the columns pages filter on** (region, then authority) so Parquet
   row-group statistics let DuckDB skip most of the file. The spike file is unsorted, so
   the Veneto query had to read every row group.
3. **Keep the request count low**: a few large row groups rather than many small ones,
   and only the columns a page needs.
4. **Small precomputed files for page loads.** Totals per town, authority and company
   should be small aggregate files that load in one request. Use range reads only for
   drill-downs into the large contract table.
5. **For small files, a full download can be faster than many range requests.** Here, 7 s
   for the whole 16.6 MB file vs 11 s for the Veneto query with ranges.

## Not checked

- Firefox and Safari (only Chrome was tested).
- Serving from a GitHub Pages origin. CORS answered `localhost` and a GitHub Pages
  origin the same way in the curl preflight, so no difference is expected.
- Whether the Hugging Face redirect can be avoided. The CDN URL is signed and expires,
  so it can't be hard-coded.
