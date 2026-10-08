import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from pipeline.ingest import anac

PAYLOAD = b"PK\x03\x04 fake zip bytes"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.endswith(".zip"):
            body, ctype = PAYLOAD, "application/zip"
        else:  # mimics the ANAC firewall: 200 with an HTML rejection page
            body, ctype = b"<html>Request Rejected</html>", "text/html; charset=UTF-8"
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
    url = f"{server}/cig_csv_2025_01.zip"

    path = anac.download(url, tmp_path)

    assert path.read_bytes() == PAYLOAD
    [entry] = read_manifest(tmp_path)
    assert entry["url"] == url
    assert entry["path"] == "raw/anac/cig_csv_2025_01.zip"
    assert entry["sha256"] == hashlib.sha256(PAYLOAD).hexdigest()
    assert entry["bytes"] == len(PAYLOAD)
    assert entry["last_modified"] == "Fri, 16 Jan 2026 16:02:30 GMT"


def test_download_skips_existing_file(server, tmp_path):
    url = f"{server}/cig_csv_2025_01.zip"
    anac.download(url, tmp_path)
    anac.download(url, tmp_path)
    assert len(read_manifest(tmp_path)) == 1


def test_html_rejection_page_is_an_error(server, tmp_path):
    with pytest.raises(RuntimeError, match="HTML"):
        anac.download(f"{server}/blocked.csv", tmp_path)
    assert not (tmp_path / "raw" / "anac" / "blocked.csv").exists()
    assert not (tmp_path / "raw" / "manifest.jsonl").exists()


def test_cig_month_url():
    assert anac.cig_month_url(2025, 1) == (
        "https://dati.anticorruzione.it/opendata/download/dataset/cig-2025/filesystem/cig_csv_2025_01.zip"
    )
