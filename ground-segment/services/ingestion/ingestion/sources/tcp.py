"""TCP implementation of the packet source (development transport)."""

from __future__ import annotations

import socket

from .base import PacketSource, PacketSourceError


class TcpPacketSource(PacketSource):
    """Reads a CCSDS packet stream from a TCP connection.

    Connects to a simulator (or any server) that emits framed packets. Only
    `_read_exact` and `close` are transport-specific; framing is inherited.
    """

    def __init__(self, host: str, port: int, timeout: float | None = None):
        self._host = host
        self._port = port
        self._timeout = timeout
        self._sock: socket.socket | None = None

    def connect(self) -> "TcpPacketSource":
        """Open the connection. Returns self so it can be chained."""
        try:
            self._sock = socket.create_connection(
                (self._host, self._port), timeout=self._timeout
            )
        except OSError as exc:
            raise PacketSourceError(
                f"cannot connect to {self._host}:{self._port}: {exc}"
            ) from exc
        return self

    def _read_exact(self, count: int) -> bytes:
        if self._sock is None:
            raise PacketSourceError("source is not connected")

        chunks: list[bytes] = []
        remaining = count
        while remaining > 0:
            try:
                chunk = self._sock.recv(remaining)
            except OSError as exc:
                raise PacketSourceError(f"socket read failed: {exc}") from exc
            if not chunk:
                # Peer closed. A clean close between packets is normal; a close
                # mid-packet means the stream was truncated.
                raise PacketSourceError("connection closed by peer")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None
