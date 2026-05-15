"""Binary framing protocol for Approach A (mTLS streaming).

Frame layout:
  [type: 1B][payload_len: 4B big-endian][payload: N bytes]

CHUNK payload layout:
  [seq_no: 4B][offset: 8B][data_len: 4B][data: data_len bytes]

All other frame payloads are UTF-8 JSON.
"""

import json
import struct
from enum import IntEnum

CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB per chunk


class MsgType(IntEnum):
    HELLO = 1
    ACK_HELLO = 2
    CHUNK = 3
    CHUNK_ACK = 4
    DONE = 5
    FIN = 6


# ── frame I/O ────────────────────────────────────────────────────────────────

def send_json_frame(sock, msg_type: int, data: dict) -> None:
    payload = json.dumps(data).encode()
    sock.sendall(struct.pack(">BI", msg_type, len(payload)) + payload)


def send_chunk_frame(sock, seq_no: int, offset: int, data: bytes) -> None:
    meta = struct.pack(">IQI", seq_no, offset, len(data))
    payload = meta + data
    sock.sendall(struct.pack(">BI", MsgType.CHUNK, len(payload)) + payload)


def recv_frame(sock) -> tuple[int, bytes]:
    header = _recvall(sock, 5)
    if header is None:
        raise ConnectionError("connection closed")
    msg_type, payload_len = struct.unpack(">BI", header)
    payload = _recvall(sock, payload_len)
    if payload is None:
        raise ConnectionError("connection closed mid-frame")
    return msg_type, payload


def parse_chunk_payload(payload: bytes) -> tuple[int, int, bytes]:
    seq_no, offset, data_len = struct.unpack(">IQI", payload[:16])
    return seq_no, offset, payload[16: 16 + data_len]


# ── helpers ───────────────────────────────────────────────────────────────────

def _recvall(sock, n: int) -> bytes | None:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)
