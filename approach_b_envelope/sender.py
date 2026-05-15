"""Approach B sender: encrypt file locally, sign manifest, upload to broker."""

import argparse
import base64
import hashlib
import json
import urllib.request
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from shared.hashing import sha256_bytes, sha256_file
from .crypto import (
    CHUNK_SIZE,
    derive_file_key,
    encrypt_chunk,
    key_fingerprint,
    load_ed25519_priv,
    load_x25519_pub,
    pub_to_b64,
    sign_manifest,
)

KEYS_DIR = Path("keys")


def _make_file_id(filename: str, total_size: int) -> str:
    raw = f"{filename}:{total_size}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def _put(broker: str, path: str, data: bytes) -> None:
    url = f"{broker.rstrip('/')}/{path}"
    req = urllib.request.Request(url, data=data, method="PUT")
    with urllib.request.urlopen(req) as resp:
        if resp.status != 200:
            raise RuntimeError(f"PUT {url} → HTTP {resp.status}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Approach B sender")
    parser.add_argument("--broker", default="http://127.0.0.1:9080",
                        help="base URL of the untrusted broker")
    parser.add_argument("--file", required=True, type=Path,
                        help="plaintext file to encrypt and upload")
    parser.add_argument("--keys", default=str(KEYS_DIR),
                        help="directory containing sender/receiver key files")
    args = parser.parse_args()

    keys = Path(args.keys)
    sign_priv = load_ed25519_priv(keys / "sender_sign_priv.pem")
    sign_pub = sign_priv.public_key()
    recv_pub = load_x25519_pub(keys / "receiver_x25519_pub.pem")

    filepath: Path = args.file
    if not filepath.exists():
        raise FileNotFoundError(filepath)

    total_size = filepath.stat().st_size
    filename = filepath.name
    file_id = _make_file_id(filename, total_size)

    print(f"File: {filepath}  ({total_size:,} bytes)  file_id={file_id}")
    print("Computing whole-file SHA-256…")
    total_sha256 = sha256_file(filepath)
    print(f"SHA-256: {total_sha256}")

    # ── ephemeral key exchange ─────────────────────────────────────────────────
    eph_priv = X25519PrivateKey.generate()
    eph_pub = eph_priv.public_key()
    file_key = derive_file_key(eph_priv, recv_pub, file_id)

    chunk_hashes: list[str] = []

    # ── encrypt and upload chunks ──────────────────────────────────────────────
    print("Encrypting and uploading chunks…")
    with open(filepath, "rb") as f:
        chunk_index = 0
        while True:
            plaintext = f.read(CHUNK_SIZE)
            if not plaintext:
                break
            chunk_hash = sha256_bytes(plaintext)
            chunk_hashes.append(chunk_hash)
            ciphertext = encrypt_chunk(file_key, chunk_index, plaintext, file_id)
            _put(args.broker, f"{file_id}/chunk_{chunk_index:06d}", ciphertext)
            chunk_index += 1
            pct = min((chunk_index * CHUNK_SIZE) / total_size * 100, 100)
            print(
                f"  [{pct:5.1f}%] chunk {chunk_index - 1}"
                f" ({len(ciphertext):,} bytes ciphertext)",
                flush=True,
            )

    chunk_count = chunk_index

    # ── build and sign manifest ────────────────────────────────────────────────
    manifest = {
        "file_id": file_id,
        "filename": filename,
        "total_size": total_size,
        "chunk_size": CHUNK_SIZE,
        "chunk_count": chunk_count,
        "chunk_hashes": chunk_hashes,
        "total_sha256": total_sha256,
        "suite": {
            "kem": "X25519",
            "kdf": "HKDF-SHA256",
            "enc": "AES-256-GCM",
        },
        "sender_ephemeral_pub": pub_to_b64(eph_pub),
        "receiver_key_fingerprint": key_fingerprint(recv_pub),
        "sender_signing_fingerprint": key_fingerprint(sign_pub),
    }
    sig = sign_manifest(sign_priv, manifest)

    # ── upload manifest + signature ────────────────────────────────────────────
    manifest_bytes = json.dumps(manifest, indent=2).encode()
    _put(args.broker, f"{file_id}/manifest.json", manifest_bytes)
    _put(args.broker, f"{file_id}/manifest.sig",
         base64.b64encode(sig))
    # Mark this transfer as the most recently uploaded
    _put(args.broker, "latest", file_id.encode())

    print(f"Upload complete  ({chunk_count} chunks)")
    print(f"Transfer ID: {file_id}")


if __name__ == "__main__":
    main()
