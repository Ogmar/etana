"""Replay stored raw packets back through the pipeline.

A ReplayPacketSource reads RawPacket rows from the archive and yields their
bytes, satisfying the same PacketSource interface as the TCP source. Because the
interface is identical, the entire ingestion pipeline (decode -> archive ->
gap-check) works unchanged when fed from the database instead of a radio.

This exists because raw packets are the immutable source of truth: re-decoding
them regenerates the derived parameter samples. That enables recalibration
(re-decode with updated coefficients, no re-flight) and comparison (derive any
calibration's output from the same raw bytes on demand).

Django must be initialised (django.setup()) before iterating.
"""

from __future__ import annotations

from .base import PacketSource, PacketSourceError


class ReplayPacketSource(PacketSource):
    """Yields the bytes of stored RawPacket rows, in receipt order.

    Optionally filtered by APID or received-time range. The rows are streamed
    from the database lazily so a large archive is not loaded into memory at once.
    """

    def __init__(self, apid: int | None = None,
                 after=None, before=None, batch_size: int = 500):
        self._apid = apid
        self._after = after
        self._before = before
        self._batch_size = batch_size
        self._iter = None

    def _queryset(self):
        # Imported here so the module can be loaded before django.setup().
        from telemetry.models import RawPacket

        qs = RawPacket.objects.all().order_by("received_at", "id")
        if self._apid is not None:
            qs = qs.filter(apid=self._apid)
        if self._after is not None:
            qs = qs.filter(received_at__gte=self._after)
        if self._before is not None:
            qs = qs.filter(received_at__lte=self._before)
        return qs

    def _read_exact(self, count: int) -> bytes:
        # Replay yields whole packets directly (see read_packet), so the byte-level
        # framing path is never used. Implemented to satisfy the interface.
        raise PacketSourceError("ReplayPacketSource yields whole packets, not a byte stream")

    def read_packet(self) -> bytes:
        if self._iter is None:
            self._iter = self._queryset().iterator(chunk_size=self._batch_size)
        try:
            row = next(self._iter)
        except StopIteration:
            raise PacketSourceError("no more stored packets")
        return bytes(row.raw_bytes)

    def count(self) -> int:
        """How many packets this replay will yield."""
        return self._queryset().count()

    def close(self) -> None:
        self._iter = None
