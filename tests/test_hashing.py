import hashlib
import tempfile
from pathlib import Path

import pytest

from shared.hashing import sha256_bytes, sha256_file


def test_sha256_bytes_known_value():
    assert sha256_bytes(b"") == hashlib.sha256(b"").hexdigest()
    assert sha256_bytes(b"hello world") == hashlib.sha256(b"hello world").hexdigest()


def test_sha256_bytes_returns_lowercase_hex():
    result = sha256_bytes(b"test")
    assert result == result.lower()
    assert len(result) == 64


def test_sha256_file_small(tmp_path):
    data = b"cmpe272 test data"
    f = tmp_path / "small.bin"
    f.write_bytes(data)
    assert sha256_file(f) == hashlib.sha256(data).hexdigest()


def test_sha256_file_multi_chunk(tmp_path):
    # Write a file larger than a single chunk to exercise the streaming loop.
    data = b"x" * (3 * 1024 * 1024)  # 3 MB — three 1 MB chunks
    f = tmp_path / "multi.bin"
    f.write_bytes(data)
    assert sha256_file(f) == hashlib.sha256(data).hexdigest()


def test_sha256_file_accepts_string_path(tmp_path):
    f = tmp_path / "str_path.bin"
    f.write_bytes(b"abc")
    assert sha256_file(str(f)) == hashlib.sha256(b"abc").hexdigest()


def test_sha256_file_empty(tmp_path):
    f = tmp_path / "empty.bin"
    f.write_bytes(b"")
    assert sha256_file(f) == hashlib.sha256(b"").hexdigest()


def test_sha256_bytes_and_file_agree(tmp_path):
    data = b"consistency check"
    f = tmp_path / "check.bin"
    f.write_bytes(data)
    assert sha256_file(f) == sha256_bytes(data)
