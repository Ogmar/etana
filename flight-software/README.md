# Flight Software

Embedded software for the Eagle-1 payload. Reads sensors, encodes CCSDS Space
Packets per the mission database, logs packets to onboard storage, and transmits
over the LoRa link.

> **Status.** Planned. Not started.

Shares the mission database at [`../mdb/etana.yaml`](../mdb/etana.yaml) with the
ground segment; that file defines the packet structure both sides implement.

Held in this repository for a single mission history. Separable into its own
repository if it develops an independent release cadence.
