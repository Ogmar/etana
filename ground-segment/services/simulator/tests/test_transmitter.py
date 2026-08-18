"""Tests for the telemetry mapping and the simulator's scheduling logic."""

from pathlib import Path

import pytest

from ccsds import decode_packet, load_mission_db
from simulator import telemetry
from simulator.flight_profile import Flight, FlightConfig, Phase
from simulator.main import Simulator

REAL_MDB = Path(__file__).resolve().parents[4] / "mdb" / "etana.yaml"


@pytest.fixture(scope="module")
def db():
    return load_mission_db(REAL_MDB)


@pytest.fixture
def flight():
    return Flight()


# --- telemetry mapping -------------------------------------------------------

def test_gps_values_scale_degrees(flight):
    """Latitude is scaled to the 1e7 integer encoding."""
    state = flight.state_at(0)
    values = telemetry.gps_values(state, onboard_time=0)
    assert values["gps_latitude"] == round(flight.cfg.launch_lat * 1e7)
    assert values["gps_altitude"] == pytest.approx(flight.cfg.ground_alt_m, abs=1)


def test_telemetry_values_encode_and_decode_back(db, flight):
    """Every generated value dict is encodable and round-trips through the codec."""
    from ccsds import encode_packet
    state = flight.state_at(1800)  # mid-ascent

    cases = {
        "gps": telemetry.gps_values(state, 1800),
        "payload": telemetry.payload_values(state, 1800),
        "housekeeping": telemetry.housekeeping_values(state, 1800, battery_v=7.5),
        "events": telemetry.event_values(1800, 2),
    }
    for container, values in cases.items():
        decoded = decode_packet(db, encode_packet(db, container, values, 0))
        assert decoded.raw == values


def test_sensor_values_stay_in_range(db, flight):
    """Across the whole flight, generated raw values never overflow their fields."""
    from ccsds import encode_packet
    for t in range(0, int(flight._landing_time_estimate()) + 60, 30):
        state = flight.state_at(t)
        # If any value overflowed its field, encode_packet would raise.
        encode_packet(db, "payload", telemetry.payload_values(state, t), 0)
        encode_packet(db, "housekeeping",
                      telemetry.housekeeping_values(state, t, 7.0), 0)


def test_ozone_peaks_in_stratosphere():
    """Ozone reading is higher near 25 km than at ground or at burst."""
    ground = telemetry._ozone_ppb(30)
    strat = telemetry._ozone_ppb(25000)
    high = telemetry._ozone_ppb(30000)
    assert strat > ground
    assert strat > high


def test_air_temp_coldest_at_tropopause():
    """Temperature drops from ground to the tropopause."""
    assert telemetry._air_temp_c(0) > telemetry._air_temp_c(11000)
    assert telemetry._air_temp_c(11000) == pytest.approx(-56.5, abs=1)


# --- scheduling --------------------------------------------------------------

def test_scheduler_produces_mission_db_rates(db):
    """Over a fixed sim-window, each stream fires at its configured rate."""
    sim = Simulator(db, Flight(), speed=1.0, tick_s=0.1)
    counts = {}
    sim_t = 0.0
    for _ in range(1000):  # 100 sim-seconds
        for s in sim._streams:
            if sim_t + 1e-9 >= s.next_due_s:
                counts[s.container] = counts.get(s.container, 0) + 1
                s.next_due_s += s.period_s
        sim_t += 0.1

    assert counts["gps"] == pytest.approx(100, abs=1)       # 1 Hz
    assert counts["payload"] == pytest.approx(20, abs=1)    # 0.2 Hz
    assert counts["housekeeping"] == pytest.approx(10, abs=1)  # 0.1 Hz


def test_only_periodic_streams_scheduled(db):
    """Events (rate 0) are not in the periodic scheduler."""
    sim = Simulator(db, Flight(), speed=1.0)
    scheduled = {s.container for s in sim._streams}
    assert "events" not in scheduled
    assert scheduled == {"gps", "payload", "housekeeping"}


def test_sequence_count_wraps_at_14_bits(db):
    from simulator.main import _Stream
    stream = _Stream(container="gps", period_s=1.0, seq=16383)
    assert stream.take_seq() == 16383
    assert stream.take_seq() == 0  # wrapped


def test_default_mdb_path_resolves():
    """The default --mdb path in main.py points at the real mission database.
    Guards against parents[] off-by-one errors if the tree is restructured."""
    from pathlib import Path
    import simulator.main as main_mod
    default = Path(main_mod.__file__).resolve().parents[4] / "mdb" / "etana.yaml"
    assert default.exists(), f"default mdb path does not exist: {default}"
