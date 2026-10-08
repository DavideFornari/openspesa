import hashlib
import io
import json
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from pipeline.ingest import anac

buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as z:
    z.writestr("cig.csv", "cig;importo_lotto\n")
PAYLOAD = buf.getvalue()
DOWNLOAD = "/opendata/download/dataset"


class Handler(BaseHTTPRequestHandler):
    """Fake ANAC portal: CKAN API, zip downloads and the firewall's HTML rejection page."""

    def do_GET(self):
        if "/blocked/" in self.path:  # the firewall: 200 and HTML, labelled text/plain
            body, ctype = b"<html>Request Rejected</html>", "text/plain"
        elif self.path.startswith("/api/package_show"):
            base = f"http://{self.headers['Host']}{DOWNLOAD}/cig/filesystem"
            resources = [
                {"format": "CSV", "url": f"{base}/20260901-cig_csv.zip"},
                {"format": "CSV", "url": f"{base}/20261001-cig_csv.zip"},
                {"format": "CSV", "url": f"{base}/cig_csv_logCsv.csv"},
                {"format": "JSON", "url": f"{base}/20261001-cig_json.zip"},
            ]
            body = json.dumps({"success": True, "result": {"resources": resources}}).encode()
            ctype = "application/json;charset=utf-8"
        elif self.path.endswith(".zip"):
            body, ctype = PAYLOAD, "application/zip"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Last-Modified", "Fri, 16 Jan 2026 16:02:30 GMT")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def read_manifest(data_dir):
    lines = (data_dir / "raw" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def test_download_writes_file_and_manifest(server, tmp_path):
    url = f"{server}{DOWNLOAD}/cig-2025/filesystem/cig_csv_2025_01.zip"

    path = anac.download(url, tmp_path)

    assert path.read_bytes() == PAYLOAD
    [entry] = read_manifest(tmp_path)
    assert entry["url"] == url
    assert entry["path"] == "raw/anac/cig-2025/cig_csv_2025_01.zip"
    assert entry["sha256"] == hashlib.sha256(PAYLOAD).hexdigest()
    assert entry["bytes"] == len(PAYLOAD)
    assert entry["last_modified"] == "Fri, 16 Jan 2026 16:02:30 GMT"


def test_download_skips_existing_file(server, tmp_path):
    url = f"{server}{DOWNLOAD}/cig-2025/filesystem/cig_csv_2025_01.zip"
    anac.download(url, tmp_path)
    anac.download(url, tmp_path)
    assert len(read_manifest(tmp_path)) == 1


def test_html_rejection_page_is_an_error(server, tmp_path):
    with pytest.raises(RuntimeError, match="blocked by firewall"):
        anac.download(f"{server}{DOWNLOAD}/blocked/filesystem/x.zip", tmp_path)
    assert list((tmp_path / "raw" / "anac" / "blocked").iterdir()) == []
    assert not (tmp_path / "raw" / "manifest.jsonl").exists()


def test_sync_downloads_only_csv_zips(server, tmp_path):
    paths = anac.sync("cig", tmp_path, api=f"{server}/api")

    assert [p.name for p in paths] == ["20260901-cig_csv.zip", "20261001-cig_csv.zip"]
    assert len(read_manifest(tmp_path)) == 2
    anac.sync("cig", tmp_path, api=f"{server}/api")  # second run: nothing new
    assert len(read_manifest(tmp_path)) == 2


def test_sync_fails_when_api_is_blocked(server, tmp_path):
    with pytest.raises(RuntimeError, match="blocked by firewall"):
        anac.sync("cig", tmp_path, api=f"{server}/blocked")


def test_cig_month_url():
    assert anac.cig_month_url(2025, 1) == (
        "https://dati.anticorruzione.it/opendata/download/dataset/cig-2025/filesystem/cig_csv_2025_01.zip"
    )
