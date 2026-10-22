# Mission Console (dashboard)

A live telemetry dashboard for Etana flights. React + TypeScript, built with Vite.
It polls the ground-segment API and shows a flight updating in real time, in two
views:

- **Flight** — a clean, at-a-glance profile: the balloon climbing and falling
  along a glowing altitude arc, with headline numbers. For anyone.
- **Mission** — a denser ops view: telemetry chart, live numeric readouts, loss
  badges, and the event log. The ground-segment console.

The console theme is deliberate — vanta black, phosphor-cyan live data, monospace
numerics — the look of a real mission-operations screen.

## Running it

The dashboard needs the API running (see `../services/api`). With the API up on
`localhost:8000`:

```
npm install
npm run dev
```

Vite serves the app on `localhost:5173` and proxies `/api` to the Django server,
so there are no cross-origin issues in development. Open the URL, pick a flight,
and watch it update. To generate a live flight, run the simulator and ingestion
(see the ground-segment README) — the dashboard auto-selects the newest flight
and polls it.

## Building for deployment

```
npm run build
```

Produces static files in `dist/` that can be served by any static host. Set
`VITE_API_BASE_URL` at build time to the deployed API's absolute URL (see
`.env.example`); unset, it falls back to `/api` on the same origin.

The app uses client-side routing, so the host must serve `index.html` for every
route (e.g. a direct visit to `/dashboard`). `vercel.json` does this for Vercel.

## How live updates work

The dashboard polls `GET /api/flights/{id}/since/?since=<cursor>` every ~1.5s,
appending only new samples (the cursor is the highest sample id seen). It stops
when the flight's status becomes `complete`. This keeps the view current without
re-fetching the whole series each poll.
