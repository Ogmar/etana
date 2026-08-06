# Flight Software

Embedded software running on the balloon payload's microcontroller (C++).
Reads sensors, builds CCSDS Space Packets per the mission database, logs every
packet to onboard storage, and transmits over the LoRa link.

> **Status:** planned. This is the embedded teammate's domain and has not started.
> It shares exactly one thing with the ground segment: the mission database at
> [`../mdb/etana.yaml`](../mdb/etana.yaml), which defines the packet structure
> both sides must agree on.

Kept in this monorepo for a single mission front door; can be split into its own
repo later (`etana-flight-software`) if it grows its own team and cadence.
