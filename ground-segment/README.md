# Ground Segment

The software that receives, decodes, archives, and visualizes Etana's telemetry.
Python core, Django/DRF web layer, React/TypeScript dashboard, Postgres archive.

> **Status:** in development. Building from the mission database and CCSDS codec
> outward, simulator-driven, before any radio hardware exists.

## Planned structure

Populated incrementally as each phase lands (see [`../docs/DESIGN.md`](../docs/DESIGN.md)):

```
ground-segment/
├── packages/
│   └── ccsds/          # the codec: mission-database-driven encode/decode (Phase 0)
├── services/
│   ├── simulator/      # emits CCSDS packets over TCP with a real flight profile (Phase 1)
│   ├── ingestion/      # IPacketSource → decode → raw archive → decom → params (Phase 1–2)
│   └── api/            # Django + DRF, read-only REST over the archive (Phase 3)
└── frontend/           # React + TypeScript dashboard: map, plots, loss badges (Phase 3)
```

## Current work

**Phase 0 — the CCSDS codec.** Load and validate `mdb/etana.yaml`, pack/unpack
the CCSDS primary header, and drive field encode/decode from the mission
database. Exit criterion: a round-trip test (encode → decode → assert equal).

Nothing here depends on hardware or on the flight software — only on the shared
mission database at [`../mdb/etana.yaml`](../mdb/etana.yaml).
