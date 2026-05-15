"""Approach B receiver: download from broker, verify signature, decrypt."""

import argparse
import base64
import json
import urllib.request
import urllib.error
from pathlib import Path

from cryptography.exceptions import InvalidSignature

from shared.hashing import sha256_bytes, sha256_file
from .crypto import (
    b64_to_x25519_pub,
    decrypt_chunk,
    key_fingerprint,
    load_ed25519_pub,
    load_x25519_priv,
    recover_file_key,
    verify_manifest_sig,
)

KEYS_DIR = Path("keys")


def _get(broker: str, path: str) -> bytes:
    url = f"{broker.rstrip('/')}/{path}"
    try:
        with urllib.request.urlopen(url) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GET {url} → HTTP {e.code}") from e


def main() -> None:
    parser = argparse.ArgumentParser(description="Approach B receiver")
    parser.add_argument("--broker", default="http://127.0.0.1:9080",
                        help="base URL of the broker")
    parser.add_argument("--out", required=True, type=Path,
                        help="output file path")
    parser.add_argument("--file-id", default=None,
                        help="transfer ID (default: read 'latest' from broker)")
    parser.add_argument("--keys", default=str(KEYS_DIR),
                        help="directory containing receiver/sender key files")
    args = parser.parse_args()

    keys = Path(args.keys)
    recv_priv = load_x25519_priv(keys / "receiver_x25519_priv.pem")
    recv_pub = recv_priv.public_key()
    sign_pub = load_ed25519_pub(keys / "sender_sign_pub.pem")

    # ── resolve transfer ID ────────────────────────────────────────────────────
    file_id = args.file_id or _get(args.broker, "latest").decode().strip()
    print(f"Transfer ID: {file_id}")

    # ── fetch and verify manifest ──────────────────────────────────────────────
    manifest = json.loads(_get(args.broker, f"{file_id}/manifest.json"))
    sig = base64.b64decode(_get(args.broker, f"{file_id}/manifest.sig"))

    try:
        verify_manifest_sig(sign_pub, manifest, sig)
    except InvalidSignature:
        raise RuntimeError("Manifest signature verification FAILED — aborting")
    print("Manifest signature: OK")

    # ── check receiver key fingerprint matches ─────────────────────────────────
    expected_fp = manifest["receiver_key_fingerprint"]
    actual_fp = key_fingerprint(recv_pub)
    if expected_fp != actual_fp:
        raise RuntimeError(
            f"Receiver key fingerprint mismatch: "
            f"manifest={expected_fp}  local={actual_fp}"
        )

    # ── recover file key ───────────────────────────────────────────────────────
    eph_pub = b64_to_x25519_pub(manifest["sender_ephemeral_pub"])
    file_key = recover_file_key(recv_priv, eph_pub, file_id)

    chunk_count: int = manifest["chunk_count"]
    chunk_hashes: list[str] = manifest["chunk_hashes"]
    total_size: int = manifest["total_size"]
    total_sha256: str = manifest["total_sha256"]

    print(
        f"File: {manifest['filename']!r}  "
        f"({total_size:,} bytes)  {chunk_count} chunks"
    )

    # ── download, decrypt, write ───────────────────────────────────────────────
    out_path: Path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "wb") as out_f:
        for i in range(chunk_count):
            ciphertext = _get(args.broker, f"{file_id}/chunk_{i:06d}")
            plaintext = decrypt_chunk(file_key, i, ciphertext, file_id)

            # Per-chunk integrity: verify plaintext hash from signed manifest
            actual_chunk_hash = sha256_bytes(plaintext)
            if actual_chunk_hash != chunk_hashes[i]:
                raise RuntimeError(
                    f"Chunk {i} hash mismatch: "
                    f"expected={chunk_hashes[i]} got={actual_chunk_hash}"
                )

            out_f.write(plaintext)
            pct = (i + 1) / chunk_count * 100
            print(
                f"  [{pct:5.1f}%] chunk {i}"
                f" ({len(plaintext):,} bytes plaintext)",
                flush=True,
            )

    # ── whole-file integrity ───────────────────────────────────────────────────
    print("Verifying whole-file SHA-256…")
    actual_total = sha256_file(out_path)
    if actual_total != total_sha256:
        raise RuntimeError(
            f"Whole-file hash mismatch: "
            f"expected={total_sha256} got={actual_total}"
        )

    print(f"OK  →  {out_path}")


if __name__ == "__main__":
    main()
