"""Approach A sender: mTLS 1.3 client that streams a file to the receiver."""

import argparse
import hashlib
import json
import socket
import ssl
from pathlib import Path

from shared.hashing import sha256_file
from .protocol import (
    CHUNK_SIZE, MsgType,
    recv_frame, send_chunk_frame, send_json_frame,
)

CERTS_DIR = Path("certs")
# Must match CN in receiver.crt so TLS hostname verification passes.
SERVER_HOSTNAME = "cmpe272-receiver"


def _make_file_id(filename: str, total_size: int) -> str:
    """Deterministic file ID used to resume across reconnections."""
    raw = f"{filename}:{total_size}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def main() -> None:
    parser = argparse.ArgumentParser(description="Approach A sender (mTLS)")
    parser.add_argument("--connect", default="127.0.0.1:9443",
                        help="host:port of the receiver")
    parser.add_argument("--file", required=True, type=Path,
                        help="file to transfer")
    parser.add_argument(
        "--certs", default=str(CERTS_DIR),
        help="directory containing ca.crt, sender.crt, sender.key",
    )
    args = parser.parse_args()

    certs = Path(args.certs)
    host, port_str = args.connect.rsplit(":", 1)
    filepath: Path = args.file

    if not filepath.exists():
        raise FileNotFoundError(filepath)

    total_size = filepath.stat().st_size
    filename = filepath.name
    file_id = _make_file_id(filename, total_size)

    print(f"File: {filepath}  ({total_size:,} bytes)")
    print("Computing SHA-256…")
    plaintext_hash = sha256_file(filepath)
    print(f"SHA-256: {plaintext_hash}")

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.load_cert_chain(certs / "sender.crt", certs / "sender.key")
    ctx.load_verify_locations(certs / "ca.crt")
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED

    with socket.create_connection((host, int(port_str))) as raw_sock:
        with ctx.wrap_socket(
            raw_sock, server_hostname=SERVER_HOSTNAME
        ) as conn:
            peer_cn = _cert_cn(conn.getpeercert())
            print(
                f"Connected  TLS={conn.version()}  peer-CN={peer_cn!r}"
            )

            # ── HELLO ──────────────────────────────────────────────────────
            send_json_frame(conn, MsgType.HELLO, {
                "version": 1,
                "file_id": file_id,
                "total_size": total_size,
                "filename": filename,
                "sha256": plaintext_hash,
            })

            # ── ACK_HELLO ──────────────────────────────────────────────────
            msg_type, payload = recv_frame(conn)
            if msg_type != MsgType.ACK_HELLO:
                raise ValueError(
                    f"expected ACK_HELLO, got {msg_type}"
                )
            resume_offset = json.loads(payload)["resume_offset"]
            if resume_offset:
                print(f"Resuming from offset {resume_offset:,}")

            # ── stream CHUNKs ──────────────────────────────────────────────
            seq_no = 0
            with open(filepath, "rb") as f:
                f.seek(resume_offset)
                offset = resume_offset
                while True:
                    data = f.read(CHUNK_SIZE)
                    if not data:
                        break
                    send_chunk_frame(conn, seq_no, offset, data)
                    offset += len(data)
                    seq_no += 1
                    if seq_no % 10 == 0:
                        pct = offset / total_size * 100 if total_size else 0
                        print(
                            f"  [{pct:5.1f}%] seq={seq_no - 1}"
                            f" offset={offset:,}",
                            flush=True,
                        )

            # ── DONE ───────────────────────────────────────────────────────
            send_json_frame(conn, MsgType.DONE, {
                "chunk_count": seq_no,
                "sha256": plaintext_hash,
            })
            print(f"Sent {seq_no} chunk(s), waiting for verification…")

            # ── FIN (drain any CHUNK_ACKs sent mid-stream) ─────────────────
            while True:
                msg_type, payload = recv_frame(conn)
                if msg_type == MsgType.FIN:
                    break
                if msg_type != MsgType.CHUNK_ACK:
                    raise ValueError(
                        f"unexpected frame {msg_type} while waiting for FIN"
                    )
            fin = json.loads(payload)
            status = fin["status"]
            print(f"Result: {status}")
            if status != "OK":
                raise RuntimeError(f"Transfer failed: {fin}")


def _cert_cn(cert: dict) -> str:
    for rdn in cert.get("subject", ()):
        for key, val in rdn:
            if key == "commonName":
                return val
    return "unknown"


if __name__ == "__main__":
    main()
