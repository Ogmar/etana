"""Archive writer: the interface ingestion uses to store telemetry.

Ingestion hands this layer a decoded packet and the raw bytes; this layer knows
how to persist them (raw packet + parameter samples). Ingestion never touches the
models directly, so a schema change is contained here.

This module assumes Django has been initialised (django.setup()) by the caller.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .models import LossEvent, ParameterSample, RawPacket


def store_packet(decoded, raw_bytes: bytes, received_at: datetime | None = None,
                 source: str = "tcp", rssi: int | None = None,
                 snr: float | None = None) -> RawPacket:
    """Persist one decoded packet: the raw bytes plus every decoded parameter.

    `decoded` is a ccsds DecodedPacket. Returns the created RawPacket.
    Raw and parameter writes happen together so the archive is never left with a
    raw packet whose samples are missing.
    """
    if received_at is None:
        received_at = datetime.now(timezone.utc)

    onboard_time = decoded.raw.get("onboard_time")

    raw = RawPacket.objects.create(
        apid=decoded.apid,
        sequence_count=decoded.sequence_count,
        raw_bytes=raw_bytes,
        received_at=received_at,
        onboard_time=onboard_time,
        source=source,
        rssi=rssi,
        snr=snr,
    )

    engineering = decoded.engineering()
    samples = []
    for field in decoded.container.fields:
        name = field.name
        raw_value = decoded.raw[name]
        eng = engineering[name]
        # Enumerated fields yield a label string; numeric fields yield a number.
        if isinstance(eng, str):
            eng_value, eng_label = None, eng
        else:
            eng_value, eng_label = float(eng), None
        samples.append(ParameterSample(
            raw_packet=raw,
            apid=decoded.apid,
            parameter_name=name,
            raw_value=raw_value,
            engineering_value=eng_value,
            engineering_label=eng_label,
            received_at=received_at,
            onboard_time=onboard_time,
        ))
    ParameterSample.objects.bulk_create(samples)
    return raw


def record_loss(apid: int, expected_sequence: int, received_sequence: int,
                lost_count: int, detected_at: datetime | None = None) -> LossEvent:
    """Persist a detected sequence gap."""
    if detected_at is None:
        detected_at = datetime.now(timezone.utc)
    return LossEvent.objects.create(
        apid=apid,
        expected_sequence=expected_sequence,
        received_sequence=received_sequence,
        lost_count=lost_count,
        detected_at=detected_at,
    )
