# Etana

**Etana is an end-to-end high-altitude balloon mission: embedded flight software, a CCSDS telemetry ground segment, and a mission site — developed together as one system.**

The balloon (vehicle **SV-1**) flies a payload to ~30 km carrying atmospheric
sensors (ozone, CO₂), GPS, and housekeeping instrumentation. It downlinks
telemetry as CCSDS Space Packets over a LoRa link. The ground segment receives,
decodes, archives, and visualizes that telemetry in real time.

> **Status:** ground segment in active development. Flight software and mission
> site are planned and currently placeholders. This README describes the target
> system; see each folder's README for what actually exists today.

---

## Architecture at a glance

```
  balloon (SV-1)                        ground
  ┌────────────────┐   CCSDS packets    ┌──────────────────────────────────────┐
  │ flight software│ ─── over LoRa ───▶ │ ingestion → archive → API → dashboard │
  │  (C++, on MCU) │                    │        (Python · Django · React)      │
  └────────────────┘                    └──────────────────────────────────────┘
           │                                              │
           └──────────── both read ─────────────┬─────────┘
                                                 ▼
                                        mdb/etana.yaml
                              (the mission database — the shared
                               definition of every packet's structure)
```

The **mission database** (`mdb/etana.yaml`) is the single source of truth for
packet structure. The flight software reads it to *encode* telemetry; the ground
segment reads it to *decode* telemetry. It is deliberately placed at the top
level, above both, because it belongs to neither — it is the contract between
them.

Development happens against a **simulator** first: it emits the exact CCSDS bytes
the radio will one day produce, over a swappable transport (TCP now, LoRa later),
so the entire ground segment is built and tested before any hardware exists.

For the full design — phases, component architecture, and rationale — see
[`docs/DESIGN.md`](docs/DESIGN.md).

---

## Repository layout

```
etana/
├── mdb/etana.yaml        # the mission database — shared contract (EXISTS)
├── ground-segment/       # telemetry receive/decode/archive/dashboard (in progress)
├── flight-software/      # embedded C++ on the payload (planned)
├── website/              # blog-style mission site + flight replay (planned)
└── docs/DESIGN.md        # full design & build plan (EXISTS)
```

Each component folder has its own README describing its status and structure.

---

## Getting started

_Run instructions will land here once the ground-segment services and their
`docker-compose.yml` exist (Phase 3 in the design doc). Until then, see
[`docs/DESIGN.md`](docs/DESIGN.md) for the build plan and
[`ground-segment/README.md`](ground-segment/README.md) for current progress._

---

## License

_TODO: choose a license (MIT is the common default for a project like this)._
