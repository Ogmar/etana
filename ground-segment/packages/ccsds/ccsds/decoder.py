"""Decode a CCSDS Space Packet into its field values.

Decoding is the inverse of encoding: read the primary header to identify the
container by APID, then walk the container's fields unpacking raw integers. The
result carries the raw values; engineering units (calibration, enumeration) are
produced on demand, keeping decode itself an exact inverse of encode.
"""

from __future__ import annotations

from dataclasses import dataclass

from .mission_db import Container, MissionDatabase
from .primary_header import HEADER_LENGTH, PrimaryHeader


class DecodeError(ValueError):
    """Raised when a byte stream cannot be decoded against the mission database."""


@dataclass
class DecodedPacket:
    """The result of decoding: the container, the header, and raw field values."""

    container: Container
    header: PrimaryHeader
    raw: dict[str, int]

    @property
    def apid(self) -> int:
        return self.header.apid

    @property
    def sequence_count(self) -> int:
        return self.header.sequence_count

    def engineering(self) -> dict:
        """Raw values converted to engineering units.

        Enumerated fields become their label; calibrated fields have their curve
        applied; all others pass through unchanged.
        """
        out: dict = {}
        for field in self.container.fields:
            value = self.raw[field.name]
            enum = field.type.enumeration
            cal = field.type.calibrator
            if enum is not None:
                out[field.name] = enum.get(value, value)
            elif cal is not None:
                out[field.name] = cal.apply(value)
            else:
                out[field.name] = value
        return out


def decode_packet(db: MissionDatabase, packet: bytes) -> DecodedPacket:
    """Decode one complete packet (header + data) into a DecodedPacket."""
    header = PrimaryHeader.unpack(packet)
    container = db.container_for_apid(header.apid)

    expected = container.data_length_bytes
    if header.data_length != expected:
        raise DecodeError(
            f"APID {header.apid} ({container.name!r}): header declares "
            f"{header.data_length} data bytes, mission database expects {expected}"
        )

    data = packet[HEADER_LENGTH:HEADER_LENGTH + expected]
    if len(data) < expected:
        raise DecodeError(
            f"APID {header.apid} ({container.name!r}): need {expected} data bytes, "
            f"got {len(data)}"
        )

    raw: dict[str, int] = {}
    offset = 0
    for field in container.fields:
        size = field.type.size_bytes
        raw[field.name] = int.from_bytes(
            data[offset:offset + size], "big", signed=field.type.signed
        )
        offset += size

    return DecodedPacket(container=container, header=header, raw=raw)
