"""Convert flight state into the raw on-wire values each container expects.

The flight model produces true physical state (degrees, metres, m/s). The
mission database expects raw integers (latitude scaled by 1e7, temperature in
centi-degrees, sensor ADC counts). This module is that mapping: state in, raw
value dicts out, ready for encode_packet. It is pure and independent of the
socket loop so the physics-to-telemetry conversion can be tested on its own.

Sensor values (ozone, CO2, temperature) are modelled as simple functions of
altitude to give plausible, altitude-dependent readings. They are raw counts,
not engineering units — the ground applies calibration.
"""

from __future__ import annotations

import math

from .flight_profile import FlightState, Phase

# Scaling to match the mission database encodings.
_DEG_SCALE = 1e7          # degrees -> signed int32 (latlon_deg)
_CDEG_SCALE = 100.0       # deg C -> signed centi-degrees (temp_cdeg)
_MV_PER_V = 1000.0        # volts -> millivolts (battery_mv)

# Inverse calibration coefficients, to turn a target engineering value back into
# raw counts (the mission DB calibrators go raw -> engineering; the simulator
# goes the other way). These mirror the placeholder curves in etana.yaml.
_OZONE_C0, _OZONE_C1 = -12.5, 0.0488   # ppb = c0 + c1*raw  ->  raw = (ppb-c0)/c1
_CO2_C1 = 0.61                          # ppm = c1*raw       ->  raw = ppm/c1


def gps_values(state: FlightState, onboard_time: int) -> dict:
    return {
        "onboard_time": onboard_time,
        "gps_latitude": round(state.latitude_deg * _DEG_SCALE),
        "gps_longitude": round(state.longitude_deg * _DEG_SCALE),
        "gps_altitude": max(0, round(state.altitude_m)),
        "gps_fix": 3 if state.phase != Phase.LANDED else 2,  # dgps aloft
        "gps_sats": 11,
    }


def payload_values(state: FlightState, onboard_time: int) -> dict:
    ozone_ppb = _ozone_ppb(state.altitude_m)
    co2_ppm = _co2_ppm(state.altitude_m)
    return {
        "onboard_time": onboard_time,
        "ozone_raw": _clamp_u16(round((ozone_ppb - _OZONE_C0) / _OZONE_C1)),
        "co2_raw": _clamp_u16(round(co2_ppm / _CO2_C1)),
        "payload_temp": _clamp_i16(round(_air_temp_c(state.altitude_m) * _CDEG_SCALE)),
    }


def housekeeping_values(state: FlightState, onboard_time: int,
                        battery_v: float) -> dict:
    return {
        "onboard_time": onboard_time,
        "battery": _clamp_u16(round(battery_v * _MV_PER_V)),
        "temp_internal": _clamp_i16(round(_internal_temp_c(state.altitude_m) * _CDEG_SCALE)),
        "temp_external": _clamp_i16(round(_air_temp_c(state.altitude_m) * _CDEG_SCALE)),
        "uptime_s": onboard_time,
        "last_rssi": 0,  # downlink-only; no uplink RSSI
    }


def event_values(onboard_time: int, event_code: int) -> dict:
    return {"onboard_time": onboard_time, "event": event_code}


# --- sensor models (altitude-dependent, deliberately simple) -----------------

def _air_temp_c(alt_m: float) -> float:
    """Rough atmospheric temperature: ~15 C at ground, coldest at the
    tropopause (~-56 C near 11 km), warming slightly in the stratosphere."""
    if alt_m < 11000:
        return 15.0 - 6.5 * (alt_m / 1000.0)          # lapse rate 6.5 C/km
    if alt_m < 20000:
        return -56.5                                   # isothermal tropopause
    return -56.5 + 1.0 * ((alt_m - 20000) / 1000.0)    # slow stratospheric warming


def _internal_temp_c(alt_m: float) -> float:
    """Avionics bay: warmer than outside air (electronics + insulation)."""
    return _air_temp_c(alt_m) + 20.0


def _ozone_ppb(alt_m: float) -> float:
    """Ozone peaks in the stratosphere (~25 km) — a Gaussian bump."""
    peak_alt, peak_ppb, width = 25000.0, 180.0, 8000.0
    ground_ppb = 30.0
    bump = peak_ppb * math.exp(-((alt_m - peak_alt) ** 2) / (2 * width ** 2))
    return ground_ppb + bump


def _co2_ppm(alt_m: float) -> float:
    """CO2 is well-mixed: roughly constant with a slight decrease at altitude."""
    return 420.0 - 10.0 * (alt_m / 30000.0)


def _clamp_u16(v: int) -> int:
    return max(0, min(65535, v))


def _clamp_i16(v: int) -> int:
    return max(-32768, min(32767, v))
