"""Download ANAC open data files into data/raw and log each download in a manifest.

Usage:
  uv run python -m pipeline.ingest.anac month 2025 1   # one month of a yearly CIG dataset
  uv run python -m pipeline.ingest.anac sync cig       # every CSV zip listed in a dataset
"""

import argparse
import hashlib
import json
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

BASE_URL = "https://dati.anticorruzione.it/opendata/download/dataset"
CKAN_API = "https://dati.anticorruzione.it/opendata/api/3/action"
# The portal's firewall rejects non-browser user-agents, so we send a browser one
# and append our name so ANAC can still identify and contact us.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/141.0.0.0 Safari/537.36 OpenSpesa/0.1 (+https://github.com/DavideFornari/openspesa)"
)
DATA_DIR = Path("data")


def _open(url: str):
    # The firewall also rejects requests without an Accept header. A rejection is HTTP 200
    # with a small HTML page (sometimes labelled text/plain), so callers validate the body.
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60)


def cig_month_url(year: int, month: int) -> str:
    return f"{BASE_URL}/cig-{year}/filesystem/cig_csv_{year}_{month:02d}.zip"


def csv_zip_urls(dataset: str, api: str = CKAN_API) -> list[str]:
    """URLs of the zipped CSV resources of a dataset, from the portal's CKAN API."""
    with _open(f"{api}/package_show?id={dataset}") as resp:
        body = resp.read()
    try:
        resources = json.loads(body)["result"]["resources"]
    except (ValueError, KeyError) as e:
        msg = f"{dataset}: not a CKAN reply (blocked by firewall?): {body[:80]!r}"
        raise RuntimeError(msg) from e
    return [r["url"] for r in resources if r["format"] == "CSV" and r["url"].endswith(".zip")]


def download(url: str, data_dir: Path = DATA_DIR) -> Path:
    """Fetch url into data_dir/raw/anac/<dataset>/ unless already there; log it in the manifest."""
    # ANAC URLs end in .../dataset/<dataset>/filesystem/<file>
    _, dataset, _, name = url.rsplit("/", 3)
    dest = data_dir / "raw" / "anac" / dataset / name
    # ponytail: an existing file is never re-fetched, which is right for monthly files.
    # Snapshot files republished under the same name (e.g. aggiudicatari_csv.zip) need a
    # Last-Modified check before we track them.
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    sha = hashlib.sha256()
    with _open(url) as resp, part.open("wb") as f:
        last_modified = resp.headers.get("Last-Modified")
        while chunk := resp.read(1 << 20):
            sha.update(chunk)
            f.write(chunk)
    if not zipfile.is_zipfile(part):
        part.unlink()
        raise RuntimeError(f"{url}: not a zip file (blocked by firewall?)")
    part.replace(dest)  # atomic: dest exists only when the download completed

    entry = {
        "url": url,
        "path": dest.relative_to(data_dir).as_posix(),
        "sha256": sha.hexdigest(),
        "bytes": dest.stat().st_size,
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "last_modified": last_modified,
    }
    with (data_dir / "raw" / "manifest.jsonl").open("a", encoding="utf-8") as m:
        m.write(json.dumps(entry) + "\n")
    return dest


def sync(dataset: str, data_dir: Path = DATA_DIR, api: str = CKAN_API) -> list[Path]:
    """Download every zipped CSV of a dataset that is not on disk yet."""
    return [download(url, data_dir) for url in csv_zip_urls(dataset, api)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Download ANAC open data files.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    month = sub.add_parser("month", help="one month of a yearly CIG dataset")
    month.add_argument("year", type=int)
    month.add_argument("month", type=int, choices=range(1, 13))
    sub.add_parser("sync", help="every CSV zip of a dataset").add_argument("dataset")
    args = parser.parse_args()

    if args.cmd == "month":
        print(download(cig_month_url(args.year, args.month)))
    else:
        for path in sync(args.dataset):
            print(path)


if __name__ == "__main__":
    main()
