# Copilot Instructions — Etana

High-altitude balloon telemetry ground segment. Python + Django REST + PostgreSQL
backend, React + TypeScript frontend, CCSDS space packets, a YAML mission database
as the single source of truth. Full context is in `/CLAUDE.md`.

## Conventions to follow

- **Mission database (`mdb/etana.yaml`) is the source of truth** for packet
  structure. Do not hardcode packet layouts, parameter lists, or calibration in
  code — derive from the mission DB.
- **Raw packets are immutable; parameter samples are derived** from them. Never
  write code that mutates stored raw bytes.
- **Config-driven archive:** parameters are rows (generic table), not columns.
  Don't add a column per sensor.
- **Transport is behind the `PacketSource` interface.** Downstream code works on
  bytes and must not depend on TCP vs replay vs LoRa.
- Keep **`received_at` (Earth-receive)** and **`onboard_time`** distinct.

## Python

- Python 3.10+. Type hints, dataclasses where used already. Match existing style.
- Tests: pytest for `ccsds`, `ingestion`, `simulator`. The `api` package uses
  Django's runner (`python manage.py test`), NOT pytest.
- Django models live in `services/api/telemetry`; the archive writer is
  `telemetry/archive.py`; the API is DRF function views in `telemetry/views.py`.

## Frontend

- React + TypeScript, Vite, functional components with hooks.
- The dashboard polls the REST API (`/api/flights/{id}/since/?since=<cursor>`) for
  live updates; append only new samples by cursor.
- Recharts for charts. The theme is a dark "mission console" (see
  `src/index.css` tokens); use the CSS variables, don't hardcode colors.

## General

- Small, reviewable changes that match existing patterns.
- Never introduce browser localStorage/sessionStorage in artifacts or committed
  frontend without reason.
- Don't invent new dependencies when an existing one fits.
