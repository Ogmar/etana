# Etana — Project Context

High-altitude balloon (HAB) telemetry ground segment. This file orients AI
assistants and contributors: architecture, conventions, commands, and the
gotchas that have actually bitten us. Read it before making changes.

## What this project is

A ground-segment system that receives, decodes, archives, and visualizes
telemetry from a high-altitude balloon (vehicle "Eagle-1"). It is modeled on real
satellite ground-software practice: CCSDS space packets, a mission database as
the single source of truth, a raw-first archive, and a live dashboard.

It is NOT a satellite system and should not be described as one. It is a HAB
ground segment; the techniques (CCSDS, mission DB, decom, archive) are the same
discipline.

## Architecture (the big picture)

```
radio/sim → packet source → CCSDS codec → ingestion pipeline → Postgres archive → REST API → dashboard
                                 ▲                                    (raw + parameters)
                          mission database (mdb/etana.yaml)
```

Core principles — do not violate these without discussion:

- **The mission database (`mdb/etana.yaml`) is the SINGLE SOURCE OF TRUTH** for
  packet structure. Both encoding (flight side) and decoding (ground side) derive
  from it. Adding a sensor is a YAML edit, not a code or schema change.
- **Config-driven everything.** The parameter archive stores one row per
  parameter (generic), not a column per sensor. New parameters need no migration.
- **Raw is immutable; parameters are derived.** `RawPacket` stores bit-exact
  bytes and is never modified. `ParameterSample` is decoded from raw and is
  regenerable. Recalibration = re-decode raw with new coefficients (no re-flight).
- **The transport is behind a seam (`PacketSource`).** Everything downstream
  receives bytes and cannot tell TCP vs replay vs (future) LoRa apart. Never
  couple the pipeline to a specific transport.
- **Earth-receive time (`received_at`) is distinct from onboard time
  (`onboard_time`).** Keep them separate; they are different facts.
- The simulator is dev scaffolding, not the product. TCP is a stand-in the real
  LoRa link will replace at the seam.

## Repository layout (monorepo)

```
etana/
├── mdb/etana.yaml              # mission database — SINGLE SOURCE OF TRUTH
├── ground-segment/
│   ├── docker-compose.yml      # Postgres only (the DB runs in Docker; Python runs on the host)
│   ├── packages/ccsds/         # CCSDS codec (pure library, pytest)
│   ├── services/
│   │   ├── simulator/          # flight model, telemetry, link pathology, TCP server (pytest)
│   │   ├── ingestion/          # packet sources (tcp, replay), gap detection, runner (pytest)
│   │   └── api/                # Django + DRF: models, archive, reprocess, REST API (manage.py test)
│   └── frontend/               # React + TypeScript + Vite dashboard
├── flight-software/            # embedded firmware (planned; docs/ has hardware decisions)
├── tools/
│   ├── flight-explorer/        # Streamlit flight-profile explorer (hosted)
│   └── byte-reference/         # generates the packet byte-layout HTML from etana.yaml
├── website/                    # mission site (planned; will merge with the dashboard)
└── docs/                       # SPECIFICATION.md, DESIGN.md
```

## Tech stack

Python 3.10–3.12, Django + Django REST Framework, PostgreSQL, React + TypeScript,
Vite, Docker, CCSDS Space Packet Protocol, YAML mission database, pytest, GitHub
Actions CI. Streamlit for the flight explorer.

## Commands and conventions

### Testing — IMPORTANT, the packages differ
- `packages/ccsds`, `services/ingestion`, `services/simulator` → **pytest**
- `services/api` → **`python manage.py test`**, NOT pytest. Django needs settings
  configured; pytest gives `ImproperlyConfigured`/`settings not configured`. Set
  `ETANA_DB=sqlite` to run without Postgres.

### Each package is installed separately (editable)
```
pip install -e packages/ccsds
pip install -e "services/simulator[dev]"
pip install -e "services/ingestion[dev]"
pip install -e "services/api[dev]"
```

### Database (Postgres in Docker)
```
cd ground-segment
docker compose up -d          # start Postgres; wait for 'healthy' in `docker compose ps`
cd services/api && python manage.py migrate   # apply migrations (targets Postgres unless ETANA_DB=sqlite)
```
- Connection comes from env vars, loaded from `ground-segment/.env` (never
  committed; `.env.example` is the template). Django loads `.env` via
  python-dotenv; Docker Compose loads it automatically.
- The DB is env-var-configured so the SAME code runs on Postgres (normal) or
  SQLite (tests/CI, via `ETANA_DB=sqlite`).

### Running a flight
```
# simulator (TCP server): from services/simulator
python -m simulator.main --speed 60            # --loss 0.05, --no-pathology, --seed N
# ingestion (TCP client): from services/ingestion
python -m ingestion.main --name "flight name"  # archives by default; --no-archive to display only
# or both at once: from ground-segment
python run_demo.py --speed 60
```

### Dashboard: from ground-segment/frontend
```
npm install && npm run dev     # needs Node 18+ (Vite 5); proxies /api to localhost:8000
```

### API: from services/api
```
python manage.py runserver     # browsable API + JSON at /api/...
```

## Git conventions

- Trunk-based: protected `main`, short-lived `type/description` branches, PRs,
  delete after merge.
- Branch prefixes: `feat/`, `fix/`, `chore/`, `docs/`.
- Commit migrations (they are source, not artifacts). Never commit `.env`,
  `node_modules/`, `dist/`, or `*.sqlite3`.
- `.gitattributes` normalizes line endings (LF) — the repo was set up on Windows.

## Documentation conventions

- Decision documents (hardware trade studies, design choices) → **Markdown** in
  the relevant `docs/` folder, so they diff and render on GitHub. Reserve PDF for
  fixed reference artifacts (datasheets).
- Diagrams are **Mermaid** (GitHub-native, text-editable).
- Doc tone is neutral engineering/spec, not journal ("the system does X", not
  "we chose X"). Honest build-vs-planned status markers; no overselling.

## Gotchas that have actually bitten us

- **Sandbox/dev filesystem note:** each package needs its own `pip install -e`;
  forgetting the api install causes `No module named 'psycopg2'`-style errors
  (the dependency is declared but not installed until you install the package).
- **Postgres port:** if 5432 is taken (native Postgres on the machine), set
  `POSTGRES_PORT=5433` in `.env`. The docker-compose mapping must be
  `${POSTGRES_PORT}:5432` — host port configurable, CONTAINER port stays 5432
  (Postgres always listens on 5432 inside the container). `5433:5433` is wrong.
- **Postgres bakes credentials on first init.** Changing `.env` credentials after
  the volume exists has no effect; `docker compose down -v` (wipes data) then
  `up` to re-init. Plain `down`/`up` preserves data.
- **Migrations must target the same DB the app uses.** Running `migrate` with
  `ETANA_DB=sqlite` set creates SQLite tables while the app hits Postgres →
  "relation does not exist". Keep `ETANA_DB` consistent.
- **14-bit sequence counter wraps at 16384.** Gap detection must treat 16383→0 as
  a normal wrap (zero lost), not 16383 lost.
- **Sequence is consumed even on a dropped packet** in the simulator — that is
  what makes loss detectable as a gap. Don't "fix" this.
- **Seeded RNG is stateful:** reconstructing a `Pathology`/`random.Random` resets
  it. Sample one instance repeatedly; don't recreate it per iteration.
- **Dense sampling of the flight model:** use `Flight.sample(n)` (one pass, O(n)),
  NOT repeated `state_at` calls (O(n²) — was 41s for 400 points).
- **Node 18+ required** for the frontend (Vite 5). Older Node gives
  `crypto.getRandomValues is not a function`.

## Working discipline for AI assistance

- Understand generated code before accepting it; this project is learned by
  understanding every decision, and that must not erode.
- Match existing patterns and conventions rather than introducing new ones.
- Do not weaken the core principles above (immutable raw, config-driven, mission
  DB as source of truth, transport seam) without explicit discussion.
- Prefer editing in place and small, reviewable diffs.
