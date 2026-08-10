"""Phase 0 exit criterion: encode -> decode round-trips against the real
mission database, and engineering conversion / error handling behave.
"""

from pathlib import Path

import pytest

from ccsds import (
    DecodeError,
    EncodeError,
    HEADER_LENGTH,
    decode_packet,
    encode_packet,
    load_mission_db,
)

REAL_MDB = Path(__file__).resolve().parents[4] / "mdb" / "etana.yaml"


@pytest.fixture(scope="module")
def db():
    return load_mission_db(REAL_MDB)


# --- the headline round-trip -------------------------------------------------

def test_gps_roundtrip(db):
    """Raw GPS values encode to bytes and decode back identically."""
    values = {
        "onboard_time": 3600,
        "gps_latitude": 454200000,    # 45.42 deg * 1e7
        "gps_longitude": -738900000,  # -73.89 deg * 1e7
        "gps_altitude": 12000,
        "gps_fix": 2,
        "gps_sats": 9,
    }
    packet = encode_packet(db, "gps", values, sequence_count=42)
    decoded = decode_packet(db, packet)

    assert decoded.raw == values
    assert decoded.apid == 100
    assert decoded.sequence_count == 42


def test_roundtrip_every_container(db):
    """Every container round-trips its raw values exactly."""
    samples = {
        "gps": {"onboard_time": 1, "gps_latitude": -1, "gps_longitude": 1,
                "gps_altitude": 0, "gps_fix": 3, "gps_sats": 12},
        "payload": {"onboard_time": 2, "ozone_raw": 1000, "co2_raw": 40000,
                    "payload_temp": -1500},
        "housekeeping": {"onboard_time": 3, "battery": 3700, "temp_internal": -500,
                         "temp_external": -4000, "uptime_s": 100000, "last_rssi": -90},
        "events": {"onboard_time": 4, "event": 2},
    }
    for name, values in samples.items():
        decoded = decode_packet(db, encode_packet(db, name, values, sequence_count=0))
        assert decoded.raw == values
        assert decoded.container.name == name


def test_packet_size_matches_mission_db(db):
    """Encoded packet length equals header + declared data length."""
    values = {"onboard_time": 0, "event": 1}
    packet = encode_packet(db, "events", values, sequence_count=0)
    assert len(packet) == HEADER_LENGTH + db.container("events").data_length_bytes


def test_signed_field_negative_roundtrip(db):
    """Negative signed values (external temp well below zero) survive."""
    values = {"onboard_time": 0, "battery": 3300, "temp_internal": -1234,
              "temp_external": -5000, "uptime_s": 0, "last_rssi": -128}
    decoded = decode_packet(db, encode_packet(db, "housekeeping", values, 0))
    assert decoded.raw["temp_external"] == -5000
    assert decoded.raw["last_rssi"] == -128


# --- engineering conversion --------------------------------------------------

def test_engineering_applies_calibration(db):
    values = {"onboard_time": 0, "gps_latitude": 454200000, "gps_longitude": 0,
              "gps_altitude": 12000, "gps_fix": 2, "gps_sats": 9}
    eng = decode_packet(db, encode_packet(db, "gps", values, 0)).engineering()
    assert eng["gps_latitude"] == pytest.approx(45.42)
    assert eng["gps_altitude"] == 12000  # no calibrator, passes through


def test_engineering_resolves_enumeration(db):
    values = {"onboard_time": 0, "gps_latitude": 0, "gps_longitude": 0,
              "gps_altitude": 0, "gps_fix": 3, "gps_sats": 0}
    eng = decode_packet(db, encode_packet(db, "gps", values, 0)).engineering()
    assert eng["gps_fix"] == "dgps_fix"


def test_encode_accepts_enum_label(db):
    """An enumerated field can be given by label instead of code."""
    values = {"onboard_time": 0, "gps_latitude": 0, "gps_longitude": 0,
              "gps_altitude": 0, "gps_fix": "3d_fix", "gps_sats": 0}
    decoded = decode_packet(db, encode_packet(db, "gps", values, 0))
    assert decoded.raw["gps_fix"] == 2


# --- error handling ----------------------------------------------------------

def test_encode_rejects_missing_field(db):
    with pytest.raises(EncodeError, match="missing value"):
        encode_packet(db, "events", {"onboard_time": 0}, 0)  # no 'event'


def test_encode_rejects_out_of_range_value(db):
    values = {"onboard_time": 0, "event": 999}  # event is uint8, max 255
    with pytest.raises(EncodeError, match="does not fit"):
        encode_packet(db, "events", values, 0)


def test_encode_rejects_unknown_enum_label(db):
    values = {"onboard_time": 0, "gps_latitude": 0, "gps_longitude": 0,
              "gps_altitude": 0, "gps_fix": "no_such_fix", "gps_sats": 0}
    with pytest.raises(EncodeError, match="unknown enumeration"):
        encode_packet(db, "gps", values, 0)


def test_decode_rejects_truncated_packet(db):
    packet = encode_packet(db, "gps", {
        "onboard_time": 0, "gps_latitude": 0, "gps_longitude": 0,
        "gps_altitude": 0, "gps_fix": 0, "gps_sats": 0}, 0)
    with pytest.raises(DecodeError):
        decode_packet(db, packet[:-3])  # chop 3 data bytes


def test_decode_rejects_unknown_apid(db):
    # Hand-build a header with an APID no container defines.
    from ccsds import PrimaryHeader
    bogus = PrimaryHeader(apid=999, sequence_count=0, data_length=1).pack() + b"\x00"
    with pytest.raises(Exception):  # MissionDatabaseError from lookup
        decode_packet(db, bogus)
