"""Tests for the packet source seam.

The important property is that framing reassembles whole packets no matter how
the underlying byte stream is chunked, since TCP and serial links deliver bytes
in arbitrary pieces.
"""

import socket
import threading
from pathlib import Path

import pytest

from ccsds import encode_packet, load_mission_db
from ingestion.sources.base import PacketSource, PacketSourceError
from ingestion.sources.tcp import TcpPacketSource

REAL_MDB = Path(__file__).resolve().parents[4] / "mdb" / "etana.yaml"


@pytest.fixture(scope="module")
def db():
    return load_mission_db(REAL_MDB)


@pytest.fixture(scope="module")
def sample_packets(db):
    """Three real packets of differing lengths."""
    return [
        encode_packet(db, "gps", {
            "onboard_time": 1, "gps_latitude": 454200000, "gps_longitude": -738900000,
            "gps_altitude": 12000, "gps_fix": 3, "gps_sats": 9}, 0),
        encode_packet(db, "events", {"onboard_time": 2, "event": 1}, 0),
        encode_packet(db, "payload", {
            "onboard_time": 3, "ozone_raw": 1000, "co2_raw": 40000,
            "payload_temp": -1500}, 0),
    ]


class ChunkedSource(PacketSource):
    """A PacketSource fed from a fixed byte buffer, handing out at most
    `chunk_size` bytes per read — to simulate stream fragmentation."""

    def __init__(self, data: bytes, chunk_size: int):
        self._data = data
        self._pos = 0
        self._chunk_size = chunk_size

    def _read_exact(self, count: int) -> bytes:
        out = bytearray()
        while len(out) < count:
            if self._pos >= len(self._data):
                raise PacketSourceError("buffer exhausted")
            take = min(self._chunk_size, count - len(out), len(self._data) - self._pos)
            out += self._data[self._pos:self._pos + take]
            self._pos += take
        return bytes(out)

    def close(self) -> None:
        pass


@pytest.mark.parametrize("chunk_size", [1, 3, 6, 7, 100])
def test_framing_survives_any_chunking(sample_packets, chunk_size):
    """Whole packets are recovered regardless of how the stream is split,
    including one byte at a time and chunks that straddle packet boundaries."""
    stream = b"".join(sample_packets)
    source = ChunkedSource(stream, chunk_size=chunk_size)
    recovered = list(source.packets())
    assert recovered == sample_packets


def test_packets_iterator_stops_cleanly_at_end(sample_packets):
    stream = b"".join(sample_packets)
    source = ChunkedSource(stream, chunk_size=5)
    assert len(list(source.packets())) == len(sample_packets)


def test_truncated_final_packet_raises_then_stops(sample_packets):
    """A stream ending mid-packet yields the whole packets, then stops."""
    stream = b"".join(sample_packets)[:-2]  # drop 2 bytes of the last packet
    source = ChunkedSource(stream, chunk_size=4)
    recovered = list(source.packets())
    assert recovered == sample_packets[:-1]


# --- real TCP round-trip -----------------------------------------------------

def test_tcp_end_to_end(sample_packets):
    """A real socket server sends packets; TcpPacketSource frames them back."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))  # OS-assigned free port
    server.listen(1)
    port = server.getsockname()[1]

    def serve():
        conn, _ = server.accept()
        with conn:
            # Send all packets as one blob; the client must reframe them.
            conn.sendall(b"".join(sample_packets))
        server.close()

    thread = threading.Thread(target=serve)
    thread.start()

    with TcpPacketSource("127.0.0.1", port, timeout=5).connect() as source:
        recovered = list(source.packets())

    thread.join()
    assert recovered == sample_packets


def test_tcp_connect_failure_raises():
    # Port 1 is privileged and almost certainly not listening.
    with pytest.raises(PacketSourceError, match="cannot connect"):
        TcpPacketSource("127.0.0.1", 1, timeout=1).connect()
