# Flight Profile Explorer

An interactive tool for exploring how flight parameters shape the Etana mission:
burst altitude, ascent rate, descent, and wind. Drag the sliders and see the
altitude profile, descent-rate curve, and ground track update live.

It runs the **real** flight model from the ground segment
(`ground-segment/services/simulator/simulator/flight_profile.py`), so the physics
shown here is exactly what the simulator flies — there is no separate model to
drift out of sync.

## For the team

This helps answer hardware questions without touching code:

- **Mechanical (recovery):** vary payload descent rate and burst altitude to see
  landing speed and descent time — inputs to parachute sizing.
- **Electrical (avionics):** see how long the flight lasts (time to burst, total
  time) to bound battery and logging requirements.
- **Everyone:** see how far downwind the payload drifts, for recovery planning.

## Using it

If it is deployed, just open the link — no install. Live at
**https://etana-flight-explorer.streamlit.app/**

To run locally:

```
pip install -r requirements.txt
streamlit run app.py
```

