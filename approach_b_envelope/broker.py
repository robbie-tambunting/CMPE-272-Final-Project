"""Approach B broker: untrusted plain-HTTP object store.

The broker performs no authentication and has no knowledge of the encryption.
It stores opaque blobs keyed by arbitrary URL paths and serves them on demand.

API:
  PUT  /<path>   – store a blob
  GET  /<path>   – retrieve a blob (404 if absent)
"""

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


class BrokerHandler(BaseHTTPRequestHandler):
    # `store` is patched onto the class by main() before the server starts.
    store: Path

    # ── PUT ───────────────────────────────────────────────────────────────────

    def do_PUT(self) -> None:
        key = self._resolve_key()
        if key is None:
            return
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len)
        dest = self.store / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        self.send_response(200)
        self.end_headers()

    # ── GET ───────────────────────────────────────────────────────────────────

    def do_GET(self) -> None:
        key = self._resolve_key()
        if key is None:
            return
        path = self.store / key
        if not path.exists() or not path.is_file():
            self.send_response(404)
            self.end_headers()
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _resolve_key(self) -> str | None:
        key = self.path.lstrip("/")
        # Prevent directory traversal
        if any(part == ".." for part in key.split("/")):
            self.send_response(400)
            self.end_headers()
            return None
        return key

    def log_message(self, fmt: str, *args) -> None:
        print(f"[broker] {self.address_string()} {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Approach B untrusted broker")
    parser.add_argument("--bind", default="127.0.0.1:9080",
                        help="host:port to listen on")
    parser.add_argument("--store", default="./broker_store", type=Path,
                        help="directory to persist uploaded objects")
    args = parser.parse_args()

    args.store.mkdir(parents=True, exist_ok=True)
    BrokerHandler.store = args.store

    host, port_str = args.bind.rsplit(":", 1)
    server = HTTPServer((host, int(port_str)), BrokerHandler)
    print(f"Broker listening on {host}:{port_str}  store={args.store}")
    server.serve_forever()


if __name__ == "__main__":
    main()
