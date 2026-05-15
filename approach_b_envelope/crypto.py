"""Cryptographic helpers for Approach B (encrypted-envelope broker).

Key exchange:  X25519 ECDH (ephemeral sender key, static receiver key)
Key derivation: HKDF-SHA256  salt=file_id  info="cmpe272-fk"
Encryption:    AES-256-GCM  nonce=chunk_index.to_bytes(12,"big")
               AAD = "{file_id}:{chunk_index}".encode()
Signing:       Ed25519 over canonical (sorted-key) JSON of the manifest
"""

import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from shared.hashing import sha256_bytes

CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB


# ── key derivation ────────────────────────────────────────────────────────────

def derive_file_key(
    sender_eph_priv: X25519PrivateKey,
    receiver_static_pub: X25519PublicKey,
    file_id: str,
) -> bytes:
    shared = sender_eph_priv.exchange(receiver_static_pub)
    return _hkdf(shared, file_id)


def recover_file_key(
    receiver_static_priv: X25519PrivateKey,
    sender_eph_pub: X25519PublicKey,
    file_id: str,
) -> bytes:
    shared = receiver_static_priv.exchange(sender_eph_pub)
    return _hkdf(shared, file_id)


def _hkdf(shared_secret: bytes, file_id: str) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=file_id.encode(),
        info=b"cmpe272-fk",
    ).derive(shared_secret)


# ── chunk encryption / decryption ─────────────────────────────────────────────

def encrypt_chunk(
    file_key: bytes,
    chunk_index: int,
    plaintext: bytes,
    file_id: str,
) -> bytes:
    nonce = chunk_index.to_bytes(12, "big")
    aad = f"{file_id}:{chunk_index}".encode()
    return AESGCM(file_key).encrypt(nonce, plaintext, aad)


def decrypt_chunk(
    file_key: bytes,
    chunk_index: int,
    ciphertext: bytes,
    file_id: str,
) -> bytes:
    nonce = chunk_index.to_bytes(12, "big")
    aad = f"{file_id}:{chunk_index}".encode()
    return AESGCM(file_key).decrypt(nonce, ciphertext, aad)


# ── manifest signing / verification ───────────────────────────────────────────

def sign_manifest(priv: Ed25519PrivateKey, manifest: dict) -> bytes:
    return priv.sign(_canonical(manifest))


def verify_manifest_sig(
    pub: Ed25519PublicKey, manifest: dict, sig: bytes
) -> None:
    """Raises cryptography.exceptions.InvalidSignature on failure."""
    pub.verify(sig, _canonical(manifest))


def _canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


# ── fingerprints ──────────────────────────────────────────────────────────────

def key_fingerprint(pub_key) -> str:
    """SHA-256 of the raw 32-byte public key."""
    raw = pub_key.public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return sha256_bytes(raw)


# ── serialization helpers ─────────────────────────────────────────────────────

def pub_to_b64(pub_key) -> str:
    raw = pub_key.public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return base64.b64encode(raw).decode()


def b64_to_x25519_pub(b64: str) -> X25519PublicKey:
    return X25519PublicKey.from_public_bytes(base64.b64decode(b64))


def load_ed25519_priv(path: Path) -> Ed25519PrivateKey:
    return serialization.load_pem_private_key(
        path.read_bytes(), password=None
    )


def load_ed25519_pub(path: Path) -> Ed25519PublicKey:
    return serialization.load_pem_public_key(path.read_bytes())


def load_x25519_priv(path: Path) -> X25519PrivateKey:
    return serialization.load_pem_private_key(
        path.read_bytes(), password=None
    )


def load_x25519_pub(path: Path) -> X25519PublicKey:
    return serialization.load_pem_public_key(path.read_bytes())
