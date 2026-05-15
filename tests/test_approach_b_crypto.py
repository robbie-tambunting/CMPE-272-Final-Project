"""Unit tests for Approach B cryptographic helpers."""

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from approach_b_envelope.crypto import (
    b64_to_x25519_pub,
    decrypt_chunk,
    derive_file_key,
    encrypt_chunk,
    key_fingerprint,
    pub_to_b64,
    recover_file_key,
    sign_manifest,
    verify_manifest_sig,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def x25519_pair():
    priv = X25519PrivateKey.generate()
    return priv, priv.public_key()


@pytest.fixture()
def ed25519_pair():
    priv = Ed25519PrivateKey.generate()
    return priv, priv.public_key()


@pytest.fixture()
def file_id():
    return "deadbeef01234567"


# ── key derivation ────────────────────────────────────────────────────────────

def test_derive_and_recover_file_key_agree(x25519_pair, file_id):
    recv_priv, recv_pub = x25519_pair
    eph_priv = X25519PrivateKey.generate()
    eph_pub = eph_priv.public_key()

    key_send = derive_file_key(eph_priv, recv_pub, file_id)
    key_recv = recover_file_key(recv_priv, eph_pub, file_id)
    assert key_send == key_recv


def test_derive_file_key_different_file_ids_differ(x25519_pair):
    recv_priv, recv_pub = x25519_pair
    eph_priv = X25519PrivateKey.generate()

    key_a = derive_file_key(eph_priv, recv_pub, "id_aaaa")
    key_b = derive_file_key(eph_priv, recv_pub, "id_bbbb")
    assert key_a != key_b


def test_derive_file_key_different_ephemeral_keys_differ(x25519_pair, file_id):
    _, recv_pub = x25519_pair

    key_a = derive_file_key(X25519PrivateKey.generate(), recv_pub, file_id)
    key_b = derive_file_key(X25519PrivateKey.generate(), recv_pub, file_id)
    assert key_a != key_b


# ── chunk encryption ──────────────────────────────────────────────────────────

def test_encrypt_decrypt_roundtrip(x25519_pair, file_id):
    recv_priv, recv_pub = x25519_pair
    eph_priv = X25519PrivateKey.generate()
    eph_pub = eph_priv.public_key()
    key = derive_file_key(eph_priv, recv_pub, file_id)
    recv_key = recover_file_key(recv_priv, eph_pub, file_id)

    plaintext = b"hello encrypted world" * 100
    ct = encrypt_chunk(key, 0, plaintext, file_id)
    assert decrypt_chunk(recv_key, 0, ct, file_id) == plaintext


def test_wrong_chunk_index_fails(x25519_pair, file_id):
    _, recv_pub = x25519_pair
    eph_priv = X25519PrivateKey.generate()
    key = derive_file_key(eph_priv, recv_pub, file_id)

    plaintext = b"data"
    ct = encrypt_chunk(key, 0, plaintext, file_id)
    with pytest.raises(Exception):  # cryptography raises InvalidTag
        decrypt_chunk(key, 1, ct, file_id)


def test_wrong_file_id_in_aad_fails(x25519_pair, file_id):
    _, recv_pub = x25519_pair
    eph_priv = X25519PrivateKey.generate()
    key = derive_file_key(eph_priv, recv_pub, file_id)

    ct = encrypt_chunk(key, 0, b"secret", file_id)
    with pytest.raises(Exception):
        decrypt_chunk(key, 0, ct, "wrongfileid00000")


def test_ciphertext_differs_from_plaintext(x25519_pair, file_id):
    _, recv_pub = x25519_pair
    eph_priv = X25519PrivateKey.generate()
    key = derive_file_key(eph_priv, recv_pub, file_id)

    plaintext = b"x" * 64
    ct = encrypt_chunk(key, 0, plaintext, file_id)
    assert ct != plaintext


# ── manifest signing ──────────────────────────────────────────────────────────

def test_sign_and_verify_manifest(ed25519_pair):
    priv, pub = ed25519_pair
    manifest = {"file_id": "abc", "chunk_count": 3, "total_sha256": "ff" * 32}
    sig = sign_manifest(priv, manifest)
    verify_manifest_sig(pub, manifest, sig)  # should not raise


def test_tampered_manifest_fails_verification(ed25519_pair):
    priv, pub = ed25519_pair
    manifest = {"file_id": "abc", "chunk_count": 3}
    sig = sign_manifest(priv, manifest)
    tampered = dict(manifest, chunk_count=99)
    with pytest.raises(InvalidSignature):
        verify_manifest_sig(pub, tampered, sig)


def test_wrong_key_fails_verification(ed25519_pair):
    priv, _ = ed25519_pair
    _, wrong_pub = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate().public_key()
    manifest = {"file_id": "abc"}
    sig = sign_manifest(priv, manifest)
    with pytest.raises(InvalidSignature):
        verify_manifest_sig(wrong_pub, manifest, sig)


# ── key fingerprint + serialization ──────────────────────────────────────────

def test_key_fingerprint_stable(x25519_pair):
    _, pub = x25519_pair
    assert key_fingerprint(pub) == key_fingerprint(pub)


def test_key_fingerprint_unique_per_key():
    pub_a = X25519PrivateKey.generate().public_key()
    pub_b = X25519PrivateKey.generate().public_key()
    assert key_fingerprint(pub_a) != key_fingerprint(pub_b)


def test_pub_to_b64_roundtrip(x25519_pair):
    _, pub = x25519_pair
    b64 = pub_to_b64(pub)
    recovered = b64_to_x25519_pub(b64)
    assert pub_to_b64(recovered) == b64
