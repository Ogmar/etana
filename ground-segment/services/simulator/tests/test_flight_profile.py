"""Tests for the pure flight model.

These verify the *shape* of the flight — the properties that make it realistic —
rather than exact numbers, so tuning constants doesn't break the suite.
"""

import pytest

from simulator.flight_profile import Flight, FlightConfig, Phase


@pytest.fixture
def flight():
    return Flight()


def test_starts_at_ground(flight):
    s = flight.state_at(0)
    assert s.phase == Phase.ASCENT
    assert s.altitude_m == pytest.approx(flight.cfg.ground_alt_m, abs=1)
    assert s.latitude_deg == pytest.approx(flight.cfg.launch_lat, abs=1e-6)
    assert s.longitude_deg == pytest.approx(flight.cfg.launch_lon, abs=1e-6)


def test_ascends_at_constant_rate(flight):
    """Altitude increases linearly during ascent."""
    a = flight.state_at(60)
    b = flight.state_at(120)
    climb_per_second = (b.altitude_m - a.altitude_m) / 60
    assert climb_per_second == pytest.approx(flight.cfg.ascent_rate_ms, rel=0.01)
    assert a.vertical_speed_ms > 0  # going up


def test_burst_turns_the_flight_around(flight):
    """Just before burst it's still climbing; just after, it's falling."""
    before = flight.state_at(flight.burst_time - 5)
    after = flight.state_at(flight.burst_time + 30)
    assert before.phase == Phase.ASCENT
    assert before.vertical_speed_ms > 0
    assert after.phase == Phase.DESCENT
    assert after.vertical_speed_ms < 0


def test_reaches_burst_altitude(flight):
    """Peak altitude is close to the configured burst altitude."""
    s = flight.state_at(flight.burst_time)
    assert s.altitude_m == pytest.approx(flight.cfg.burst_alt_m, rel=0.01)


def test_descent_is_fast_then_slow(flight):
    """Fall speed high in thin air just after burst, lower near the ground —
    the terminal-velocity-in-an-exponential-atmosphere signature."""
    high = flight.state_at(flight.burst_time + 20)     # still near 30 km
    low = flight.state_at(flight.burst_time + 60 * 30)  # much lower
    fall_high = -high.vertical_speed_ms
    fall_low = -low.vertical_speed_ms
    assert fall_high > fall_low
    assert fall_high > 20    # tens of m/s up high
    assert 0 < fall_low < 15  # single digits near ground


def test_eventually_lands(flight):
    """Well after the flight, it is on the ground and stationary."""
    s = flight.state_at(60 * 60 * 4)  # 4 hours, long past landing
    assert s.phase == Phase.LANDED
    assert s.altitude_m == pytest.approx(flight.cfg.ground_alt_m, abs=1)
    assert s.vertical_speed_ms == 0.0


def test_landing_position_is_stable(flight):
    """Once landed, the position doesn't drift with further time."""
    a = flight.state_at(60 * 60 * 3)
    b = flight.state_at(60 * 60 * 5)
    assert a.latitude_deg == pytest.approx(b.latitude_deg)
    assert b.longitude_deg == pytest.approx(b.longitude_deg)


def test_drifts_downwind(flight):
    """The vehicle moves away from the launch point (wind drift)."""
    launch = flight.state_at(0)
    aloft = flight.state_at(flight.burst_time)
    moved = abs(aloft.latitude_deg - launch.latitude_deg) + \
            abs(aloft.longitude_deg - launch.longitude_deg)
    assert moved > 0.01  # meaningfully displaced


def test_negative_time_clamps_to_launch(flight):
    assert flight.state_at(-100).altitude_m == pytest.approx(
        flight.cfg.ground_alt_m, abs=1)


def test_custom_config_changes_burst_time():
    """A lower burst altitude bursts sooner."""
    low = Flight(FlightConfig(burst_alt_m=15000))
    high = Flight(FlightConfig(burst_alt_m=30000))
    assert low.burst_time < high.burst_time
