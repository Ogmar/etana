"""Encode raw field values into a full CCSDS Space Packet.

The encoder operates on raw (on-wire) integer values, not engineering units.
The flight software produces raw sensor counts; the ground applies calibration
after decoding. Sequence counting is stateful across packets and is therefore
the caller's responsibility, passed in per call.
"""

from __future__ import annotations

from .mission_db import Container, Field, MissionDatabase
from .primary_header import PrimaryHeader


class EncodeError(ValueError):
    """Raised when field values cannot be encoded for a container."""


def encode_packet(
    db: MissionDatabase,
    container_name: str,
    values: dict,
    sequence_count: int,
) -> bytes:
    """Build a complete packet (6-byte header + data) for one container.

    values maps field name -> raw value. Enumerated fields accept either the
    integer code or the label string. Every field the container defines must be
    present; extra keys are ignored.
    """
    container = db.container(container_name)
    data = _encode_fields(container, values)
    header = PrimaryHeader(
        apid=container.apid,
        sequence_count=sequence_count,
        data_length=len(data),
        version=db.ccsds_version,
        sequence_flags=db.sequence_flags,
    )
    return header.pack() + data


def _encode_fields(container: Container, values: dict) -> bytes:
    out = bytearray()
    for field in container.fields:
        if field.name not in values:
            raise EncodeError(
                f"container {container.name!r}: missing value for field {field.name!r}"
            )
        raw = _resolve_raw(field, values[field.name])
        out += _pack_int(field, raw)
    return bytes(out)


def _resolve_raw(field: Field, value) -> int:
    """Turn a caller-supplied value into a raw integer.

    Enumerated fields accept the label string as well as the integer code.
    """
    enum = field.type.enumeration
    if enum is not None and isinstance(value, str):
        label_to_code = {label: code for code, label in enum.items()}
        if value not in label_to_code:
            raise EncodeError(
                f"field {field.name!r}: unknown enumeration label {value!r}"
            )
        return label_to_code[value]

    if not isinstance(value, int):
        raise EncodeError(
            f"field {field.name!r}: expected int (or enum label), got {type(value).__name__}"
        )
    return value


def _pack_int(field: Field, raw: int) -> bytes:
    try:
        return raw.to_bytes(
            field.type.size_bytes, "big", signed=field.type.signed
        )
    except OverflowError:
        kind = "signed" if field.type.signed else "unsigned"
        raise EncodeError(
            f"field {field.name!r}: value {raw} does not fit in "
            f"{field.type.size_bits}-bit {kind} integer"
        )
