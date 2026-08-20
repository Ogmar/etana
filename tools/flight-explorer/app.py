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

import altair as alt
import pandas as pd

states = flight.sample(400)  # one-pass sampling; fast enough for live sliders

df = pd.DataFrame({
    "time_min": [s.t / 60 for s in states],
    "altitude_km": [s.altitude_m / 1000 for s in states],
    "fall_speed": [-s.vertical_speed_ms for s in states],
    "phase": [s.phase.value for s in states],
    "lat": [s.latitude_deg for s in states],
    "lon": [s.longitude_deg for s in states],
})

# Ground track in kilometres from launch. Degrees make a poor axis here: the
# drift is a fraction of a degree but tens of km on the ground, so a lat/lon
# plot collapses to a dot. Converting to km from the launch point fixes the scale.
lat0, lon0 = df["lat"].iloc[0], df["lon"].iloc[0]
m_per_deg_lat = 111_320.0
m_per_deg_lon = m_per_deg_lat * math.cos(math.radians(lat0))
df["east_km"] = (df["lon"] - lon0) * m_per_deg_lon / 1000
df["north_km"] = (df["lat"] - lat0) * m_per_deg_lat / 1000

# --- summary metrics ----------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)
col1.metric("Burst altitude", f"{cfg.burst_alt_m/1000:.1f} km")
col2.metric("Time to burst", f"{flight.burst_time/60:.0f} min")
col3.metric("Total flight time", f"{states[-1].t/60:.0f} min")
peak_descent = df["fall_speed"].max()
col4.metric("Peak descent rate", f"{peak_descent:.0f} m/s")

# --- plots --------------------------------------------------------------------

left, right = st.columns(2)

with left:
    st.subheader("Altitude profile")
    alt_chart = (
        alt.Chart(df)
        .mark_line(color="#2a78d6")
        .encode(
            x=alt.X("time_min", title="Time since launch (min)"),
            y=alt.Y("altitude_km", title="Altitude (km)"),
            tooltip=[alt.Tooltip("time_min", title="Time (min)", format=".0f"),
                     alt.Tooltip("altitude_km", title="Altitude (km)", format=".1f")],
        )
        .properties(height=300)
    )
    st.altair_chart(alt_chart, width="stretch")
    st.caption("Linear ascent, burst, then fast-then-slowing descent, over time.")

    st.subheader("Descent rate vs altitude")
    descent = df[df["phase"] == "descent"]
    if not descent.empty:
        desc_chart = (
            alt.Chart(descent)
            .mark_line(color="#c0562e")
            .encode(
                x=alt.X("altitude_km", title="Altitude (km)",
                        scale=alt.Scale(reverse=True)),  # high -> low as it falls
                y=alt.Y("fall_speed", title="Fall speed (m/s)"),
                tooltip=[alt.Tooltip("altitude_km", title="Altitude (km)", format=".1f"),
                         alt.Tooltip("fall_speed", title="Fall speed (m/s)", format=".1f")],
            )
            .properties(height=260)
        )
        st.altair_chart(desc_chart, width="stretch")
        st.caption("Fast in thin air just after burst, slowing as the air thickens.")

with right:
    st.subheader("Ground track")
    # km axes and altitude-coloured path so the drift reads as a real shape.
    track = (
        alt.Chart(df)
        .mark_circle(size=22)
        .encode(
            x=alt.X("east_km", title="East of launch (km)"),
            y=alt.Y("north_km", title="North of launch (km)"),
            color=alt.Color("altitude_km", title="Altitude (km)",
                            scale=alt.Scale(scheme="viridis")),
            order="time_min",
            tooltip=[alt.Tooltip("east_km", title="East (km)", format=".1f"),
                     alt.Tooltip("north_km", title="North (km)", format=".1f"),
                     alt.Tooltip("altitude_km", title="Altitude (km)", format=".1f")],
        )
        .properties(height=360)
    )
    st.altair_chart(track, width="stretch")
    drift_km = _haversine_km(df["lat"].iloc[0], df["lon"].iloc[0],
                             df["lat"].iloc[-1], df["lon"].iloc[-1])
    st.caption(
        f"Path from launch (0, 0); lands about {drift_km:.0f} km away, downwind. "
        f"Colour shows altitude along the path — ascent and descent legs are distinct."
    )

st.divider()
st.caption(
    "Physics: constant-rate ascent; descent as terminal velocity in an "
    "exponential atmosphere (fast up high, slowing as air thickens); wind drift "
    "scaled by altitude. Model: ground-segment/services/simulator/flight_profile.py"
)
