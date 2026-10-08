# Spike: can GitHub Actions download from ANAC? (Gate A)

**Result (2026-10-09): no. Gate A fails, so Phase 1 uses the local-download fallback.**

## What we ran

[`probe-anac.yml`](../../.github/workflows/probe-anac.yml) runs the same ingester that works
from a home connection (`uv run python -m pipeline.ingest.anac month 2025 1`), with the same
browser user-agent.

| Where | Network | Result |
|---|---|---|
| Home PC, Italy | residential ISP | 200, 21 MB zip in 8 s, hash verified |
| GitHub-hosted runner, `ubuntu-24.04` | Azure, Virginia, US (AS8075 Microsoft) | **403 Forbidden** |

From home, a bad user-agent gets `200` plus an HTML rejection page. The runner got a hard
`403` with a good user-agent, so the firewall is blocking on IP (datacenter reputation or
geography), not on headers. Changing headers will not fix it.

Run: https://github.com/DavideFornari/openspesa/actions/runs/37854475117

## Fallback design

ANAC publishes monthly, so the fallback only needs **one local step per month**.

```
Home PC (monthly, ~5 min)                 GitHub Actions (public, scheduled)
─────────────────────────                 ──────────────────────────────────
pipeline.ingest.anac  → data/raw/*.zip
                        manifest.jsonl
upload raw/ to HF dataset "openspesa/raw-mirror" ─▶ download raw/ from HF
                                            bronze → silver → gold (dbt-duckdb)
                                            publish Parquet to "openspesa/..."
```

- **Only the download runs at home.** Everything after raw still runs in public CI, so
  builds stay reproducible and anyone can audit them.
- **The raw mirror on Hugging Face doubles as provenance.** The original ANAC zips plus
  the manifest (URL, SHA-256, Last-Modified) are published under CC BY-SA 4.0 with
  attribution. CI checks hashes against the manifest before building.
- **Size is small.** 2025 CIG CSV zips are about 21 MB per month (about 250 MB per year).
  The full history is a few GB, which fits HF's free public storage.
- **Trigger:** run it by hand, with a monthly reminder in `TODO.md`. Automate it with
  Windows Task Scheduler only if forgetting becomes a problem.

### Rejected alternatives

- **Self-hosted GitHub runner on the home PC.** It's free, but GitHub warns against
  self-hosted runners on public repositories: a pull request from a fork could run code
  on your machine. It also only works while the PC is on.
- **A free cloud VM or proxy in Italy.** It would break the zero-cost, nothing-always-on
  constraint, and its IP could be blocked just like Azure's.
- **GitHub Releases as raw storage.** It works, but Hugging Face is already our data
  store, and one provider is easier to move.

## Re-test

The probe workflow stays in the repo. Re-run it occasionally
(`gh workflow run probe-anac.yml`). If ANAC ever unblocks runners, the home step can
move into Actions with no other changes.
