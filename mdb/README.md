# Mission Database

`etana.yaml` defines the structure of every telemetry packet. The flight software
reads it to encode telemetry; the ground segment reads it to decode telemetry.
It is the sole definition of packet structure — this README describes the file;
the file is authoritative.

## XTCE mapping

The format follows [XTCE](https://public.ccsds.org/) concepts to allow migration
to XTCE without restructuring:

| This file | XTCE | Purpose |
|-----------|------|---------|
| `parameter_types` | ParameterTypeSet | value encoding and calibration |
| `parameters` | ParameterSet | named telemetry points |
| `containers` | SequenceContainer | packet layout per APID |
| `calibrator` | Calibrator | raw counts to engineering units |

## Structure

- `parameter_types` — encoding definitions (bit width, sign, unit, calibration
  curve), defined once and referenced by parameters.
- `parameters` — named telemetry points, each referencing a type.
- `containers` — one per APID; an ordered field list defining the packet's byte
  layout. Each container carries an `onboard_time` field. Earth-receive time is
  recorded ground-side at ingestion.

The codec prepends a 6-byte CCSDS primary header to each packet, built from the
container's `apid` and the mission-level `ccsds` settings.

## Parameters

Sizes are on-wire encoded bytes, excluding the 6-byte header. "Cal" indicates a
ground-side calibration curve.

### GPS — APID 100, 1.0 Hz

| Parameter | Bytes | Unit | Cal | Description |
|-----------|-------|------|-----|-------------|
| `gps_latitude` | 4 | deg | yes | WGS84 latitude |
| `gps_longitude` | 4 | deg | yes | WGS84 longitude |
| `gps_altitude` | 2 | m | — | GPS altitude MSL |
| `gps_fix` | 1 | enum | — | Fix quality (no fix / 2D / 3D / DGPS) |
| `gps_sats` | 1 | — | — | Satellites in view |

### Payload — APID 200, 0.2 Hz

Raw ADC counts; engineering units applied ground-side.

| Parameter | Bytes | Unit | Cal | Description |
|-----------|-------|------|-----|-------------|
| `ozone_raw` | 2 | ppb | yes | Ozone cell ADC counts |
| `co2_raw` | 2 | ppm | yes | CO2 sensor ADC counts |
| `payload_temp` | 2 | degC | yes | Payload internal temp |

### Housekeeping — APID 300, 0.1 Hz

| Parameter | Bytes | Unit | Cal | Description |
|-----------|-------|------|-----|-------------|
| `battery` | 2 | V | yes | Main battery voltage |
| `temp_internal` | 2 | degC | yes | Avionics bay temp |
| `temp_external` | 2 | degC | yes | Outside air temp |
| `uptime_s` | 4 | — | — | Seconds since boot |
| `last_rssi` | 2 | — | — | Last uplink RSSI (requires commanding) |

### Events — APID 400, event-driven

| Parameter | Bytes | Unit | Cal | Description |
|-----------|-------|------|-----|-------------|
| `event` | 1 | enum | — | launch / burst / descent / landing / cutdown / mode change |

## Notes

- `ppb`/`ppm` are target units; the payload transmits raw ADC counts converted by
  the calibration curves. Coefficients are placeholders pending sensor calibration.
- `last_rssi` is meaningful only with an uplink; it may be removed for a
  downlink-only flight.
- The largest packet is 22 bytes including the header, within LoRa payload limits
  at SF7–9.
