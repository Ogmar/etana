# Flight Software

Embedded software for the Eagle-1 payload. Reads sensors, builds CCSDS Space
Packets per the mission database, logs every packet to onboard storage, and
transmits over the LoRa link.

> **Status.** Planned. Not started. This README describes the intended design so
> the work can begin in parallel with the ground segment.

## Where it fits

The flight software is the mirror image of the ground segment's receive path.
The ground segment *decodes* CCSDS bytes; the flight software *encodes* them.
Both derive packet structure from the same mission database — that shared file is
the contract that lets the two sides be built independently.

```mermaid
flowchart LR
    subgraph flight["Flight software (Eagle-1 flight MCU)"]
        direction TB
        SENSE["Read sensors<br/>GPS, ozone, CO2, housekeeping"]
        BUILD["Build packets<br/>encode raw values as CCSDS"]
        LOG["Log to SD card<br/>every packet, bit-exact"]
        TX["Transmit<br/>via onboard LoRa radio"]
        SENSE --> BUILD --> LOG --> TX
    end

    MDB[("Mission database<br/>etana.yaml")]
    MDB -.->|"defines packet structure"| BUILD

    TX ==>|"CCSDS bytes, RF"| GRX["Ground receiver<br/>LoRa radio + bridging MCU"]
    GRX ==>|"raw bytes, no decoding"| GROUND["Ground segment"]
    MDB -.->|"same contract"| GROUND
```

The ground receiver is part of the link, not the ground segment: it relays
bytes from radio to wire and does not read the mission database.

## Responsibilities

The flight software must, in order:

1. **Read sensors** — sample GPS, the atmospheric payload (ozone, CO2), and
   housekeeping (battery, temperatures) at each stream's rate. Rates are defined
   per container in the mission database (GPS 1 Hz, payload 0.2 Hz, housekeeping
   0.1 Hz).
2. **Encode packets** — pack each reading into a CCSDS Space Packet exactly as
   the mission database specifies: correct APID, field order, byte sizes, and a
   per-APID sequence counter. Sensors report *raw* values (ADC counts, scaled
   integers); calibration to engineering units happens on the ground.
3. **Log onboard** — write every packet bit-exact to SD storage before (or
   alongside) transmitting, so data survives link dropouts and can be recovered
   after landing.
4. **Transmit** — send packets over the onboard LoRa radio to the ground
   receiver (a matching LoRa radio paired with its own bridging MCU, on the
   ground segment side of the link).

## The contract with the ground segment

The interface between flight and ground is the byte layout defined in
[`../mdb/etana.yaml`](../mdb/etana.yaml). The flight software's encoder must
produce bytes the ground segment's decoder accepts. The ground receiver sits
physically between the two but is not a party to this contract — it forwards
raw bytes without reading them, the same way the TCP socket does today.

The ground segment includes a reference encoder (the `ccsds` package, in Python)
that can serve as an oracle: for a given set of field values, the flight
software's output bytes should match the reference encoder's output byte-for-byte.
This makes conformance testable without a radio — compare bytes, not behaviour.

## Open questions

- Microcontroller and toolchain (dictates the C/C++ environment).
- LoRa module and its driver.
- Whether onboard logging and transmission are concurrent or sequential.
- Cutdown command handling, if an uplink is built (coordinate with the recovery
  system and the ground segment's commanding path).
- Ground receiver firmware (the bridging MCU's own program, mirroring this
  flight MCU's receive-side counterpart) — not yet started; needs its own
  MCU/LoRa selection, parallel to
  [`docs/mcu-lora-selection.md`](docs/mcu-lora-selection.md).

Held in this monorepo for a single mission history; separable into its own
repository later if it develops an independent release cadence.
