"""Pure flight model for a high-altitude balloon.

State is a function of elapsed flight time only: no clock, no I/O, no packets.
This makes the physics independently testable and keeps it decoupled from the
transmitter that samples it. It also keeps the flight model independent of the
future landing predictor, so the predictor can be validated against flights this
produces without testing a model against itself.

The profile has three regimes:
    ascent   - constant climb rate to burst altitude
    descent  - fall rate set by terminal velocity in an exponential atmosphere,
               so the payload falls fast in thin air and slows in thicker air
    landed   - stationary at ground level

Horizontal motion is wind drift that varies with altitude, giving a curved
ground track rather than a straight line.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class Phase(str, Enum):
    ASCENT = "ascent"
    DESCENT = "descent"
    LANDED = "landed"


@dataclass(frozen=True)
class FlightConfig:
    """Parameters defining one flight. Defaults model a typical HAB flight."""

    launch_lat: float = 45.42      # degrees
    launch_lon: float = -73.89     # degrees
    ground_alt_m: float = 30.0     # launch/landing ground level
    burst_alt_m: float = 30000.0   # ~30 km
    ascent_rate_ms: float = 5.0    # constant climb, m/s
    descent_terminal_ms: float = 5.5   # descent speed once in dense air (near ground)
    scale_height_m: float = 7500.0     # atmospheric density e-folding height
    wind_east_base_ms: float = 8.0     # eastward drift, scaled by altitude
    wind_north_base_ms: float = 2.5    # northward drift, scaled by altitude


@dataclass(frozen=True)
class FlightState:
    """The vehicle's true state at one instant."""

    t: float               # seconds since launch
    phase: Phase
    altitude_m: float
    latitude_deg: float
    longitude_deg: float
    vertical_speed_ms: float   # +up, -down


# Metres per degree of latitude (approx, constant). Longitude is scaled by
# cos(latitude) since meridians converge toward the poles.
_M_PER_DEG_LAT = 111_320.0


class Flight:
    """A flight instance. `state_at(t)` returns the vehicle state at sim-time t."""

    def __init__(self, config: FlightConfig | None = None):
        self.cfg = config or FlightConfig()
        self._burst_time = (
            (self.cfg.burst_alt_m - self.cfg.ground_alt_m) / self.cfg.ascent_rate_ms
        )

    @property
    def burst_time(self) -> float:
        """Seconds from launch to burst."""
        return self._burst_time

    def state_at(self, t: float) -> FlightState:
        if t < 0:
            t = 0.0

        if t <= self._burst_time:
            return self._ascent_state(t)
        return self._descent_state(t)

    # --- ascent --------------------------------------------------------------

    def _ascent_state(self, t: float) -> FlightState:
        alt = self.cfg.ground_alt_m + self.cfg.ascent_rate_ms * t
        lat, lon = self._position(t)
        return FlightState(
            t=t,
            phase=Phase.ASCENT,
            altitude_m=alt,
            latitude_deg=lat,
            longitude_deg=lon,
            vertical_speed_ms=self.cfg.ascent_rate_ms,
        )

    # --- descent -------------------------------------------------------------

    def _descent_state(self, t: float) -> FlightState:
        """Integrate the fall from burst.

        Terminal velocity scales as 1/sqrt(density); with an exponential
        atmosphere density = exp(-alt/H), so v(alt) = v_terminal * exp(alt/2H).
        The payload therefore falls fast at altitude and slows near the ground.
        Altitude is stepped forward from burst in small increments.
        """
        alt = self.cfg.burst_alt_m
        step_t = self._burst_time
        dt = 0.5  # integration step (sim-seconds)

        while step_t < t and alt > self.cfg.ground_alt_m:
            v = self._descent_speed(alt)
            alt -= v * dt
            step_t += dt

        if alt <= self.cfg.ground_alt_m:
            lat, lon = self._position(self._landing_time_estimate())
            return FlightState(
                t=t,
                phase=Phase.LANDED,
                altitude_m=self.cfg.ground_alt_m,
                latitude_deg=lat,
                longitude_deg=lon,
                vertical_speed_ms=0.0,
            )

        lat, lon = self._position(step_t)
        return FlightState(
            t=t,
            phase=Phase.DESCENT,
            altitude_m=alt,
            latitude_deg=lat,
            longitude_deg=lon,
            vertical_speed_ms=-self._descent_speed(alt),
        )

    def _descent_speed(self, alt: float) -> float:
        exponent = (alt - self.cfg.ground_alt_m) / (2 * self.cfg.scale_height_m)
        return self.cfg.descent_terminal_ms * math.exp(exponent)

    def _landing_time_estimate(self) -> float:
        """Approximate total flight time, for freezing the landing position."""
        alt = self.cfg.burst_alt_m
        step_t = self._burst_time
        dt = 0.5
        while alt > self.cfg.ground_alt_m:
            alt -= self._descent_speed(alt) * dt
            step_t += dt
        return step_t

    # --- horizontal drift ----------------------------------------------------

    def _position(self, t: float) -> tuple[float, float]:
        """Integrate wind drift up to time t. Wind grows with altitude, so the
        track curves as the balloon climbs and straightens as it descends."""
        east_m = 0.0
        north_m = 0.0
        dt = 1.0
        elapsed = 0.0
        while elapsed < t:
            step = min(dt, t - elapsed)
            alt = self._altitude_only(elapsed)
            scale = alt / self.cfg.burst_alt_m  # 0 at ground, 1 at burst
            east_m += self.cfg.wind_east_base_ms * scale * step
            north_m += self.cfg.wind_north_base_ms * scale * step
            elapsed += step

        lat = self.cfg.launch_lat + north_m / _M_PER_DEG_LAT
        lon = self.cfg.launch_lon + east_m / (
            _M_PER_DEG_LAT * math.cos(math.radians(self.cfg.launch_lat))
        )
        return lat, lon

    def _altitude_only(self, t: float) -> float:
        """Altitude at time t, without building a full state (used by drift)."""
        if t <= self._burst_time:
            return self.cfg.ground_alt_m + self.cfg.ascent_rate_ms * t
        alt = self.cfg.burst_alt_m
        step_t = self._burst_time
        dt = 0.5
        while step_t < t and alt > self.cfg.ground_alt_m:
            alt -= self._descent_speed(alt) * dt
            step_t += dt
        return max(alt, self.cfg.ground_alt_m)
