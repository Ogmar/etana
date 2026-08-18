"""Ingestion runner: connect to a packet source and process the telemetry stream.

For now this decodes each packet and prints it. In Phase 2 the same loop gains
the archive write (raw + parameter stores) and sequence-gap detection; the
structure here is the seam it hangs off.

Network role: ingestion is the CLIENT. It connects to the simulator (or, later,
reads from a radio via a different packet source) and pulls packets.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ccsds import DecodeError, MissionDatabase, decode_packet, load_mission_db

from .sources.base import PacketSource, PacketSourceError
from .sources.tcp import TcpPacketSource


def run(source: PacketSource, db: MissionDatabase, quiet: bool = False) -> int:
    """Process every packet from a source until it is exhausted.

    Returns the number of packets successfully decoded.
    """
    count = 0
    for packet in source.packets():
        try:
            decoded = decode_packet(db, packet)
        except DecodeError as exc:
            if not quiet:
                print(f"  [decode error] {exc}")
            continue
        count += 1
        if not quiet:
            _print_packet(decoded)
    return count


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
    parser.add_argument("--mdb", type=Path,
                        default=Path(__file__).resolve().parents[4] / "mdb" / "etana.yaml")
    args = parser.parse_args()

    if not args.mdb.exists():
        raise SystemExit(
            f"mission database not found at {args.mdb}\n"
            f"pass --mdb with the path to etana.yaml"
        )

    db = load_mission_db(args.mdb)

    print(f"connecting to {args.host}:{args.port} ...")
    try:
        source = TcpPacketSource(args.host, args.port, timeout=30).connect()
    except PacketSourceError as exc:
        raise SystemExit(f"could not connect: {exc}")

    print("connected; receiving telemetry\n")
    with source:
        total = run(source, db, quiet=args.quiet)
    print(f"\nstream ended; {total} packets decoded")


if __name__ == "__main__":
    main()
