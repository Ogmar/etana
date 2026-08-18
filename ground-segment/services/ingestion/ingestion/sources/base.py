"""The transport seam: a packet source yields complete CCSDS packets as bytes.

Everything downstream of this interface receives whole packets and is
independent of the transport. A concrete source implements only how to read a
fixed number of raw bytes; the framing that turns a byte stream into discrete
packets is defined once here, driven by the CCSDS primary header's length field.

Concrete sources:
    TcpPacketSource   - reads from a TCP socket (development)
    LoRaPacketSource  - reads from a radio serial link (flight, later)
    ReplayPacketSource - re-reads stored raw packets (later)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from ccsds.primary_header import HEADER_LENGTH, PrimaryHeader


class PacketSourceError(Exception):
    """Raised when the underlying transport fails or the stream ends mid-packet."""


class PacketSource(ABC):
    """Yields complete CCSDS Space Packets as bytes, one at a time.

    Subclasses implement `_read_exact` (block until N bytes are available) and
    `close`. Framing is handled here: read the 6-byte primary header, decode the
    data length, then read exactly that many data bytes.
    """

    @abstractmethod
    def _read_exact(self, count: int) -> bytes:
        """Return exactly `count` bytes, or raise PacketSourceError if the
        stream ends before `count` bytes are available."""

    @abstractmethod
    def close(self) -> None:
        """Release the underlying transport."""

    def read_packet(self) -> bytes:
        """Read and return one complete packet (header + data)."""
        header_bytes = self._read_exact(HEADER_LENGTH)
        header = PrimaryHeader.unpack(header_bytes)
        data_bytes = self._read_exact(header.data_length)
        return header_bytes + data_bytes

    def packets(self) -> Iterator[bytes]:
        """Yield packets until the source is exhausted or closed."""
        while True:
            try:
                yield self.read_packet()
            except PacketSourceError:
                return

    def __enter__(self) -> "PacketSource":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
