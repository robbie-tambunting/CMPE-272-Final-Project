"""Unit tests for Approach A binary framing protocol (no network required)."""

import io
import json
import struct

import pytest

from approach_a_mtls.protocol import (
    CHUNK_SIZE,
    MsgType,
    _recvall,
    parse_chunk_payload,
    recv_frame,
    send_chunk_frame,
    send_json_frame,
)


# ── fake socket helpers ───────────────────────────────────────────────────────

class FakeSocket:
    """In-memory socket backed by a BytesIO buffer."""

    def __init__(self, data: bytes = b""):
        self._buf = io.BytesIO(data)
        self._out = io.BytesIO()

    def recv(self, n: int) -> bytes:
        return self._buf.read(n)

    def sendall(self, data: bytes) -> None:
        self._out.write(data)

    @property
    def sent(self) -> bytes:
        return self._out.getvalue()


def _make_json_frame(msg_type: int, data: dict) -> bytes:
    payload = json.dumps(data).encode()
    return struct.pack(">BI", msg_type, len(payload)) + payload


def _make_chunk_frame(seq_no: int, offset: int, data: bytes) -> bytes:
    meta = struct.pack(">IQI", seq_no, offset, len(data))
    payload = meta + data
    return struct.pack(">BI", MsgType.CHUNK, len(payload)) + payload


# ── recv_frame ────────────────────────────────────────────────────────────────

def test_recv_frame_json():
    raw = _make_json_frame(MsgType.HELLO, {"file_id": "abc"})
    sock = FakeSocket(raw)
    msg_type, payload = recv_frame(sock)
    assert msg_type == MsgType.HELLO
    assert json.loads(payload) == {"file_id": "abc"}


def test_recv_frame_chunk():
    data = b"hello world"
    raw = _make_chunk_frame(7, 1024, data)
    sock = FakeSocket(raw)
    msg_type, payload = recv_frame(sock)
    assert msg_type == MsgType.CHUNK
    seq_no, offset, body = parse_chunk_payload(payload)
    assert seq_no == 7
    assert offset == 1024
    assert body == data


def test_recv_frame_connection_closed():
    sock = FakeSocket(b"")
    with pytest.raises(ConnectionError):
        recv_frame(sock)


def test_recv_frame_closed_mid_frame():
    # Only the 5-byte header, no payload
    sock = FakeSocket(struct.pack(">BI", MsgType.HELLO, 10))
    with pytest.raises(ConnectionError):
        recv_frame(sock)


# ── send_json_frame ───────────────────────────────────────────────────────────

def test_send_json_frame_roundtrip():
    sock = FakeSocket()
    send_json_frame(sock, MsgType.ACK_HELLO, {"resume_offset": 0})
    readback = FakeSocket(sock.sent)
    msg_type, payload = recv_frame(readback)
    assert msg_type == MsgType.ACK_HELLO
    assert json.loads(payload) == {"resume_offset": 0}


# ── send_chunk_frame ──────────────────────────────────────────────────────────

def test_send_chunk_frame_roundtrip():
    chunk_data = b"x" * 1024
    sock = FakeSocket()
    send_chunk_frame(sock, seq_no=3, offset=8192, data=chunk_data)
    readback = FakeSocket(sock.sent)
    msg_type, payload = recv_frame(readback)
    assert msg_type == MsgType.CHUNK
    seq_no, offset, body = parse_chunk_payload(payload)
    assert seq_no == 3
    assert offset == 8192
    assert body == chunk_data


def test_send_chunk_frame_empty_data():
    sock = FakeSocket()
    send_chunk_frame(sock, seq_no=0, offset=0, data=b"")
    readback = FakeSocket(sock.sent)
    msg_type, payload = recv_frame(readback)
    assert msg_type == MsgType.CHUNK
    _, _, body = parse_chunk_payload(payload)
    assert body == b""


# ── parse_chunk_payload ───────────────────────────────────────────────────────

def test_parse_chunk_payload_large_offset():
    # Offset > 4 GB to verify 8-byte field is used correctly
    large_offset = 5 * 1024 ** 3  # 5 GB
    data = b"data"
    meta = struct.pack(">IQI", 0, large_offset, len(data))
    seq_no, offset, body = parse_chunk_payload(meta + data)
    assert offset == large_offset
    assert body == data


# ── constants ─────────────────────────────────────────────────────────────────

def test_chunk_size_is_4mb():
    assert CHUNK_SIZE == 4 * 1024 * 1024
