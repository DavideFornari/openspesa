"""Download ANAC open data files into data/raw and log each download in a manifest.

Usage: uv run python -m pipeline.ingest.anac 2025 1
"""

import argparse
import hashlib
import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

BASE_URL = "https://dati.anticorruzione.it/opendata/download/dataset"
# The portal's firewall rejects non-browser user-agents, so we send a browser one
# and append our name so ANAC can still identify and contact us.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/141.0.0.0 Safari/537.36 OpenSpesa/0.1 (+https://github.com/davidef99/openspesa)"
)
DATA_DIR = Path("data")


def cig_month_url(year: int, month: int) -> str:
    # ponytail: pattern checked for cig-2025 only; the current year lives in the "cig"
    # delta dataset under another name. Switch to CKAN package_show when we need more.
    return f"{BASE_URL}/cig-{year}/filesystem/cig_csv_{year}_{month:02d}.zip"


def download(url: str, data_dir: Path = DATA_DIR) -> Path:
    """Fetch url into data_dir/raw/anac/ unless already there; append a manifest line."""
    dest = data_dir / "raw" / "anac" / url.rsplit("/", 1)[-1]
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    sha = hashlib.sha256()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as resp:
        # The firewall answers a rejected request with HTTP 200 and an HTML page.
        content_type = resp.headers.get("Content-Type", "")
        if content_type.startswith("text/html"):
            raise RuntimeError(f"{url}: got HTML instead of a data file (blocked by firewall?)")
        last_modified = resp.headers.get("Last-Modified")
        with part.open("wb") as f:
            while chunk := resp.read(1 << 20):
                sha.update(chunk)
                f.write(chunk)
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Download one month of ANAC CIG data.")
    parser.add_argument("year", type=int)
    parser.add_argument("month", type=int, choices=range(1, 13))
    args = parser.parse_args()
    print(download(cig_month_url(args.year, args.month)))


if __name__ == "__main__":
    main()
