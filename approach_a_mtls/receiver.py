"""Approach A receiver: mTLS 1.3 server that accepts a streamed file."""

import argparse
import json
import socket
import ssl
from pathlib import Path

from shared.hashing import sha256_file
from .protocol import MsgType, recv_frame, send_json_frame, parse_chunk_payload

CERTS_DIR = Path("certs")


def handle_client(conn: ssl.SSLSocket, out_dir: Path) -> None:
    # ── HELLO ─────────────────────────────────────────────────────────────────
    msg_type, payload = recv_frame(conn)
    if msg_type != MsgType.HELLO:
        raise ValueError(f"expected HELLO, got {msg_type}")

    hello = json.loads(payload)
    file_id = hello["file_id"]
    total_size = hello["total_size"]
    filename = hello["filename"]
    expected_hash = hello["sha256"]
    print(f"Incoming: {filename!r} ({total_size:,} bytes)  file_id={file_id}")

    partial_path = out_dir / f"{file_id}.partial"
    state_path = out_dir / f"{file_id}.state"

    # Resume: read last contiguous offset from state file
    resume_offset = 0
    if state_path.exists() and partial_path.exists():
        try:
            resume_offset = json.loads(state_path.read_text()).get("offset", 0)
            print(f"Resuming from offset {resume_offset:,}")
        except Exception:
            resume_offset = 0

    # ── ACK_HELLO ─────────────────────────────────────────────────────────────
    send_json_frame(conn, MsgType.ACK_HELLO, {"resume_offset": resume_offset})

    # ── receive CHUNKs ────────────────────────────────────────────────────────
    mode = "r+b" if resume_offset > 0 and partial_path.exists() else "wb"
    with open(partial_path, mode) as f:
        if resume_offset > 0:
            f.seek(resume_offset)
            f.truncate()

        last_seq = -1
        while True:
            msg_type, payload = recv_frame(conn)

            if msg_type == MsgType.DONE:
                break

            if msg_type != MsgType.CHUNK:
                raise ValueError(f"unexpected frame {msg_type}")

            seq_no, offset, data = parse_chunk_payload(payload)
            f.write(data)
            f.flush()
            last_seq = seq_no
            current_offset = offset + len(data)
            state_path.write_text(json.dumps({"offset": current_offset}))

            if seq_no % 100 == 0:
                pct = current_offset / total_size * 100 if total_size else 0
                print(f"  [{pct:5.1f}%] seq={seq_no} offset={current_offset:,}", flush=True)
                send_json_frame(conn, MsgType.CHUNK_ACK, {"last_seq": last_seq})

    # ── verify and FIN ────────────────────────────────────────────────────────
    print("Verifying SHA-256…")
    actual_hash = sha256_file(partial_path)

    if actual_hash == expected_hash:
        final_path = out_dir / filename
        partial_path.rename(final_path)
        state_path.unlink(missing_ok=True)
        send_json_frame(conn, MsgType.FIN, {"status": "OK"})
        print(f"OK  →  {final_path}")
    else:
        send_json_frame(conn, MsgType.FIN, {
            "status": "HASH_MISMATCH",
            "expected": expected_hash,
            "actual": actual_hash,
        })
        print(f"HASH_MISMATCH  expected={expected_hash}  actual={actual_hash}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Approach A receiver (mTLS)")
    parser.add_argument("--bind", default="127.0.0.1:9443",
                        help="host:port to listen on")
    parser.add_argument("--out", default="./recv_a", type=Path,
                        help="output directory")
    parser.add_argument("--certs", default=str(CERTS_DIR),
                        help="directory containing ca.crt, receiver.crt, receiver.key")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    certs = Path(args.certs)
    host, port_str = args.bind.rsplit(":", 1)

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.load_cert_chain(certs / "receiver.crt", certs / "receiver.key")
    ctx.load_verify_locations(certs / "ca.crt")
    ctx.verify_mode = ssl.CERT_REQUIRED  # enforce mTLS

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as raw_sock:
        raw_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        raw_sock.bind((host, int(port_str)))
        raw_sock.listen(1)
        print(f"Listening on {host}:{port_str}  (mTLS, TLS 1.3 minimum)")

        conn_sock, addr = raw_sock.accept()
        with ctx.wrap_socket(conn_sock, server_side=True) as tls_conn:
            peer_cn = _cert_cn(tls_conn.getpeercert())
            print(f"Connection from {addr}  TLS={tls_conn.version()}  peer-CN={peer_cn!r}")
            handle_client(tls_conn, args.out)


def _cert_cn(cert: dict) -> str:
    for rdn in cert.get("subject", ()):
        for key, val in rdn:
            if key == "commonName":
                return val
    return "unknown"


if __name__ == "__main__":
    main()
