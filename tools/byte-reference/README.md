# Packet Byte Reference

Generates a human-readable HTML reference showing the byte layout of every
telemetry packet — the CCSDS header, a visual byte map, and a field table with
offsets, sizes, encoding, units, calibration, and enumerations.

It is **generated from the mission database** (`mdb/etana.yaml`) through the same
loader the codec uses, so it always matches what the flight software encodes and
the ground segment decodes. It cannot drift from the real packet format.

## Regenerating

Whenever `etana.yaml` changes (a field added, resized, renamed), regenerate:

```
pip install -e ../../ground-segment/packages/ccsds   # if not already installed
python generate.py -o packet-reference.html
```

Open `packet-reference.html` in any browser. It is self-contained (no server,
no assets) so it can be emailed, committed, or hosted as-is.

## For flight controllers

Each packet shows a coloured byte grid (header in slate, each field a distinct
colour) above a table giving, per field: its byte offset, size, encoding
(e.g. `int32`, `uint16`), unit, and notes — including calibration coefficients
and enumerated values. Multi-byte fields are big-endian.
