"""Tests for the mission database loader."""

from pathlib import Path

import pytest

from ccsds.mission_db import (
    Calibrator,
    MissionDatabase,
    MissionDatabaseError,
    load_mission_db,
    _build,
)

# The real mission database, four directories up from this test file:
# ccsds/tests/ -> ccsds/ -> packages/ -> ground-segment/ -> etana/mdb/etana.yaml
REAL_MDB = Path(__file__).resolve().parents[4] / "mdb" / "etana.yaml"


def minimal_db() -> dict:
    """A small valid database dict, used as a base for validation tests."""
    return {
        "mission": {"name": "Test", "vehicle": "T-1", "byte_order": "big_endian",
                    "ccsds": {"version": 0, "sequence_flags": 3}},
        "parameter_types": {
            "uint16": {"encoding": "unsigned_int", "size_bits": 16},
            "uint32": {"encoding": "unsigned_int", "size_bits": 32},
        },
        "parameters": {
            "value": {"type": "uint16", "description": "a value"},
        },
        "containers": {
            "sample": {
                "apid": 100, "rate_hz": 1.0, "description": "sample",
                "fields": [
                    {"name": "onboard_time", "type": "uint32"},
                    {"parameter": "value"},
                ],
            },
        },
    }


# --- loading the real mission database ---------------------------------------

def test_loads_real_mission_database():
    db = load_mission_db(REAL_MDB)
    assert isinstance(db, MissionDatabase)
    assert db.vehicle == "Eagle-1"
    assert set(db.containers) == {"gps", "payload", "housekeeping", "events"}


def test_real_gps_container_layout():
    db = load_mission_db(REAL_MDB)
    gps = db.container("gps")
    assert gps.apid == 100
    # onboard_time(4) + lat(4) + lon(4) + alt(2) + fix(1) + sats(1) = 16 data bytes
    assert gps.data_length_bytes == 16
    assert [f.name for f in gps.fields] == [
        "onboard_time", "gps_latitude", "gps_longitude",
        "gps_altitude", "gps_fix", "gps_sats",
    ]


def test_lookup_by_apid():
    db = load_mission_db(REAL_MDB)
    assert db.container_for_apid(200).name == "payload"


def test_reference_resolution_carries_type():
    """A parameter field resolves to carry its full type, not just a name."""
    db = load_mission_db(REAL_MDB)
    lat = db.container("gps").fields[1]
    assert lat.name == "gps_latitude"
    assert lat.type.size_bits == 32
    assert lat.type.signed is True
    assert lat.type.calibrator is not None


# --- calibration --------------------------------------------------------------

def test_polynomial_calibrator_linear():
    cal = Calibrator(kind="polynomial", coefficients=(0.0, 1.0e-7))
    assert cal.apply(454200000) == pytest.approx(45.42)


def test_polynomial_calibrator_with_offset():
    cal = Calibrator(kind="polynomial", coefficients=(-12.5, 0.0488))
    assert cal.apply(1000) == pytest.approx(-12.5 + 0.0488 * 1000)


# --- validation: each rule must fire -----------------------------------------

def test_rejects_unknown_byte_order():
    db = minimal_db()
    db["mission"]["byte_order"] = "little_endian"
    with pytest.raises(MissionDatabaseError, match="byte_order"):
        _build(db)


def test_rejects_unknown_encoding():
    db = minimal_db()
    db["parameter_types"]["bad"] = {"encoding": "float", "size_bits": 32}
    with pytest.raises(MissionDatabaseError, match="encoding"):
        _build(db)


def test_rejects_non_byte_aligned_size():
    db = minimal_db()
    db["parameter_types"]["odd"] = {"encoding": "unsigned_int", "size_bits": 12}
    with pytest.raises(MissionDatabaseError, match="multiple of 8"):
        _build(db)


def test_rejects_parameter_with_unknown_type():
    db = minimal_db()
    db["parameters"]["broken"] = {"type": "nonexistent"}
    with pytest.raises(MissionDatabaseError, match="unknown type"):
        _build(db)


def test_rejects_field_with_unknown_parameter():
    db = minimal_db()
    db["containers"]["sample"]["fields"].append({"parameter": "ghost"})
    with pytest.raises(MissionDatabaseError, match="unknown parameter"):
        _build(db)


def test_rejects_duplicate_apid():
    db = minimal_db()
    db["containers"]["other"] = {
        "apid": 100, "fields": [{"name": "t", "type": "uint32"}],
    }
    with pytest.raises(MissionDatabaseError, match="already used"):
        _build(db)


def test_rejects_apid_out_of_range():
    db = minimal_db()
    db["containers"]["sample"]["apid"] = 3000
    with pytest.raises(MissionDatabaseError, match="out of range"):
        _build(db)


def test_rejects_missing_required_key():
    db = minimal_db()
    del db["containers"]["sample"]["apid"]
    with pytest.raises(MissionDatabaseError, match="missing required key"):
        _build(db)


def test_unknown_apid_lookup_raises():
    db = _build(minimal_db())
    with pytest.raises(MissionDatabaseError, match="no container"):
        db.container_for_apid(999)
