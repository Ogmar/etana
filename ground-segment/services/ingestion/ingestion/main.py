"""Ingestion runner: connect to a packet source and process the telemetry stream.

The pipeline runs three separate steps per packet:
    1. decode  - bytes to values (the ccsds codec)
    2. archive - store the raw packet and its parameter samples
    3. gaps    - check the sequence counter and record any loss

Archiving and gap detection are independent: a packet is archived whether or not
it revealed a gap, and a gap is recorded by comparing sequence numbers regardless
of archiving. Keeping them separate keeps each simple and independently correct.

Network role: ingestion is the CLIENT. It connects to the simulator (or a radio
via a different packet source) and pulls packets.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from ccsds import DecodeError, MissionDatabase, decode_packet, load_mission_db

from .sources.base import PacketSource, PacketSourceError
from .sources.tcp import TcpPacketSource
from .gap_detector import GapDetector


def _setup_django() -> None:
    """Initialise Django so the archive writer and models are usable outside the
    web server. Adds the api project to the path and configures settings."""
    api_dir = Path(__file__).resolve().parents[3] / "api"
    sys.path.insert(0, str(api_dir))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()


def run(source: PacketSource, db: MissionDatabase, archive=None,
        quiet: bool = False, flight=None) -> dict:
    """Process every packet from a source until it is exhausted.

    If `archive` is provided (the api telemetry.archive module), each packet is
    stored and gaps are recorded. If None, packets are only decoded and shown
    (no persistence) — useful for a quick look without a database. If `flight` is
    provided, stored packets and loss events are associated with it.

    Returns a summary dict: packets decoded, stored, and total lost.
    """
    detector = GapDetector()
    stats = {"decoded": 0, "stored": 0, "lost": 0}

    for packet in source.packets():
        # Step 1 — decode.
        try:
            decoded = decode_packet(db, packet)
        except DecodeError as exc:
            if not quiet:
                print(f"  [decode error] {exc}")
            continue
        stats["decoded"] += 1
        received_at = datetime.now(timezone.utc)

        # Step 2 — archive (independent of gap detection).
        if archive is not None:
            archive.store_packet(decoded, packet, received_at=received_at,
                                 flight=flight)
            stats["stored"] += 1

        # Step 3 — gap detection (independent of archiving).
        gap = detector.check(decoded.apid, decoded.sequence_count)
        if gap is not None:
            stats["lost"] += gap.lost_count
            if archive is not None:
                archive.record_loss(
                    gap.apid, gap.expected_sequence, gap.received_sequence,
                    gap.lost_count, detected_at=received_at, flight=flight)
            if not quiet:
                print(f"  [loss] apid={gap.apid} lost {gap.lost_count} "
                      f"(expected {gap.expected_sequence}, got {gap.received_sequence})")

        if not quiet:
            _print_packet(decoded)

    return stats


def _print_packet(decoded) -> None:
    name = decoded.container.name
    seq = decoded.sequence_count
    eng = decoded.engineering()
    if name == "gps":
        print(f"GPS   seq={seq:<5} alt={eng['gps_altitude']:>6}m  "
              f"lat={eng['gps_latitude']:.4f} lon={eng['gps_longitude']:.4f} "
              f"fix={eng['gps_fix']}")
    elif name == "payload":
        print(f"PAYLD seq={seq:<5} O3={eng['ozone_raw']:.1f}ppb  "
              f"CO2={eng['co2_raw']:.0f}ppm  temp={eng['payload_temp']:.1f}C")
    elif name == "housekeeping":
        print(f"HK    seq={seq:<5} batt={eng['battery']:.2f}V  "
              f"Tin={eng['temp_internal']:.1f}C Tout={eng['temp_external']:.1f}C")
    elif name == "events":
        print(f"EVENT seq={seq:<5} >>> {eng['event']} <<<")


def main() -> None:
    parser = argparse.ArgumentParser(description="Etana telemetry ingestion")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--quiet", action="store_true",
                        help="count packets without printing each one")
    parser.add_argument("--no-archive", action="store_true",
                        help="decode and display only; do not write to the database")
    parser.add_argument("--name", default="",
                        help="name for this flight record (when archiving)")
    parser.add_argument("--mdb", type=Path,
                        default=Path(__file__).resolve().parents[4] / "mdb" / "etana.yaml")
    args = parser.parse_args()

    if not args.mdb.exists():
        raise SystemExit(
            f"mission database not found at {args.mdb}\n"
            f"pass --mdb with the path to etana.yaml"
        )

    db = load_mission_db(args.mdb)

    archive = None
    flight = None
    if not args.no_archive:
        _setup_django()
        from telemetry import archive as archive_module
        from telemetry.models import Flight
        archive = archive_module
        flight = Flight.objects.create(name=args.name or "", source="tcp")
        print(f"opened flight #{flight.id}"
              + (f" ({flight.name})" if flight.name else ""))

    print(f"connecting to {args.host}:{args.port} ...")
    try:
        source = TcpPacketSource(args.host, args.port, timeout=30).connect()
    except PacketSourceError as exc:
        raise SystemExit(f"could not connect: {exc}")

    mode = "display only" if archive is None else "archiving to database"
    print(f"connected; receiving telemetry ({mode})\n")
    with source:
        stats = run(source, db, archive=archive, quiet=args.quiet, flight=flight)
    if flight is not None:
        flight.mark_complete()
    print(f"\nstream ended; {stats['decoded']} decoded, "
          f"{stats['stored']} stored, {stats['lost']} lost"
          + (f" (flight #{flight.id}, marked complete)" if flight else ""))


if __name__ == "__main__":
    main()

