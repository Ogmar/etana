"""Etana flight profile explorer.

An interactive tool for the team to explore how flight parameters affect the
mission — burst altitude, ascent rate, payload descent, wind — and see the
resulting altitude profile, ground track, and descent-rate curve.

It runs the *real* flight model from the ground segment (flight_profile.py), so
what you see here is exactly what the simulator flies. There is no second physics
implementation to drift out of sync.

Run locally:   streamlit run app.py
Hosted:        Streamlit Community Cloud, pointed at this file in the repo.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import streamlit as st


def _haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points, in km."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))

# Import the real flight model from the ground segment. The path insert lets this
# tool reuse flight_profile.py directly rather than reimplementing the physics.
_SIM = Path(__file__).resolve().parents[2] / "ground-segment" / "services" / "simulator"
sys.path.insert(0, str(_SIM))
from simulator.flight_profile import Flight, FlightConfig, Phase  # noqa: E402


st.set_page_config(page_title="Etana Flight Explorer", layout="wide")
st.title("Etana Flight Profile Explorer")
st.caption(
    "Explore how flight parameters shape the mission. This runs the same flight "
    "model the simulator flies — the physics here is the real physics."
)

# --- controls ----------------------------------------------------------------

with st.sidebar:
    st.header("Flight parameters")
    burst_alt = st.slider("Burst altitude (km)", 15.0, 40.0, 30.0, 0.5,
                          help="Altitude at which the balloon bursts.") * 1000
    ascent_rate = st.slider("Ascent rate (m/s)", 2.0, 8.0, 5.0, 0.1,
                            help="Constant climb rate during ascent.")
    descent_terminal = st.slider("Landing descent rate (m/s)", 3.0, 10.0, 5.5, 0.1,
                                 help="Descent speed once in dense air near the ground.")
    st.markdown("**Wind**")
    wind_east = st.slider("Eastward wind (m/s)", 0.0, 20.0, 8.0, 0.5)
    wind_north = st.slider("Northward wind (m/s)", -10.0, 10.0, 2.5, 0.5)

cfg = FlightConfig(
    burst_alt_m=burst_alt,
    ascent_rate_ms=ascent_rate,
    descent_terminal_ms=descent_terminal,
    wind_east_base_ms=wind_east,
    wind_north_base_ms=wind_north,
)
flight = Flight(cfg)

# --- sample the flight --------------------------------------------------------

states = flight.sample(400)  # one-pass sampling; fast enough for live sliders

alt_km = [s.altitude_m / 1000 for s in states]
descent_rate = [-s.vertical_speed_ms for s in states if s.phase == Phase.DESCENT]
descent_alt_km = [s.altitude_m / 1000 for s in states if s.phase == Phase.DESCENT]
lats = [s.latitude_deg for s in states]
lons = [s.longitude_deg for s in states]

# --- summary metrics ----------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)
col1.metric("Burst altitude", f"{cfg.burst_alt_m/1000:.1f} km")
col2.metric("Time to burst", f"{flight.burst_time/60:.0f} min")
col3.metric("Total flight time", f"{states[-1].t/60:.0f} min")
peak_descent = max(descent_rate) if descent_rate else 0
col4.metric("Peak descent rate", f"{peak_descent:.0f} m/s")

# --- plots --------------------------------------------------------------------

left, right = st.columns(2)

with left:
    st.subheader("Altitude profile")
    st.line_chart({"altitude (km)": alt_km}, x_label="sample", y_label="km")
    st.caption("Linear ascent, burst, then fast-then-slowing descent.")

    st.subheader("Descent rate vs altitude")
    if descent_rate:
        # Show fall speed decaying as it enters denser air.
        st.line_chart(
            {"fall speed (m/s)": descent_rate},
            x_label="descent sample (high to low altitude)", y_label="m/s",
        )
        st.caption("Fast in thin air just after burst, slowing toward landing.")

with right:
    st.subheader("Ground track")
    # A path of (lon, lat) points — lighter and more robust than a tile map,
    # and it shows the drift path rather than scattered dots.
    import pandas as pd
    track = pd.DataFrame({"longitude": lons, "latitude": lats})
    st.scatter_chart(track, x="longitude", y="latitude", size=8)
    drift_km = _haversine_km(lats[0], lons[0], lats[-1], lons[-1])
    st.caption(
        f"Launch at ({lats[0]:.3f}, {lons[0]:.3f}); "
        f"lands about {drift_km:.0f} km away, downwind."
    )

st.divider()
st.caption(
    "Physics: constant-rate ascent; descent as terminal velocity in an "
    "exponential atmosphere (fast up high, slowing as air thickens); wind drift "
    "scaled by altitude. Model: ground-segment/services/simulator/flight_profile.py"
)
