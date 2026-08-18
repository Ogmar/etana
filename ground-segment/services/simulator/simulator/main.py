"""Simulator transmitter: a TCP server that streams a simulated flight.

Once a client (ingestion) connects, the transmitter runs a real-time loop:
advance sim-time by the speed multiplier, and on each container's schedule
sample the flight model, convert state to raw values, encode a packet, and send
it. Discrete events (burst, landing) fire on phase transitions. The run ends
when the flight lands.

Network role: the simulator is the SERVER (passive source, like the flight
radio); ingestion is the client that connects and reads. Swapping TCP for a real
radio later replaces the client's packet source, not this server.
"""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass, field
from pathlib import Path

from ccsds import MissionDatabase, encode_packet, load_mission_db

from .flight_profile import Flight, FlightConfig, Phase
from . import telemetry


@dataclass
class _Stream:
    """Scheduling state for one periodic container."""

    container: str
    period_s: float          # sim-seconds between packets (0 = event-driven)
    next_due_s: float = 0.0
    seq: int = 0

    def take_seq(self) -> int:
        s = self.seq
        self.seq = (self.seq + 1) % 16384  # 14-bit CCSDS sequence count
        return s


# Event codes from the mission database enumeration.
EVENT_LAUNCH = 1
EVENT_BURST = 2
EVENT_DESCENT = 3
EVENT_LANDING = 4


class Simulator:
    def __init__(self, db: MissionDatabase, flight: Flight,
                 speed: float = 1.0, tick_s: float = 0.1):
        self.db = db
        self.flight = flight
        self.speed = speed          # sim-seconds per real-second
        self.tick_s = tick_s        # real-seconds between loop iterations
        self._battery_v = 8.4       # starts full, drains over the flight

        self._streams = self._build_streams()
        self._event_seq = 0

    def _build_streams(self) -> list[_Stream]:
        streams = []
        for name, container in self.db.containers.items():
            if container.rate_hz > 0:
                streams.append(_Stream(container=name, period_s=1.0 / container.rate_hz))
        return streams

    def run(self, host: str = "127.0.0.1", port: int = 9000) -> None:
        """Listen for one client, then stream a full flight to it."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((host, port))
            server.listen(1)
            print(f"simulator listening on {host}:{port} (speed x{self.speed})")
            conn, addr = server.accept()
            print(f"client connected from {addr[0]}:{addr[1]}; starting flight")
            with conn:
                self._fly(conn)
            print("flight complete")

    def _fly(self, conn: socket.socket) -> None:
        sim_t = 0.0
        last_phase = Phase.ASCENT
        self._send_event(conn, sim_t, EVENT_LAUNCH)

        while True:
            state = self.flight.state_at(sim_t)

            # Phase-transition events.
            if state.phase != last_phase:
                if state.phase == Phase.DESCENT:
                    self._send_event(conn, sim_t, EVENT_BURST)
                    self._send_event(conn, sim_t, EVENT_DESCENT)
                elif state.phase == Phase.LANDED:
                    self._send_event(conn, sim_t, EVENT_LANDING)
                last_phase = state.phase

            # Periodic streams that are due.
            for stream in self._streams:
                if sim_t + 1e-9 >= stream.next_due_s:
                    self._send_stream(conn, stream, state, sim_t)
                    stream.next_due_s += stream.period_s

            if state.phase == Phase.LANDED:
                return

            # Drain the battery slowly over the flight.
            self._battery_v = max(6.0, self._battery_v - 0.00005 * self.tick_s * self.speed)

            time.sleep(self.tick_s)
            sim_t += self.tick_s * self.speed

    def _send_stream(self, conn, stream: _Stream, state, sim_t: float) -> None:
        onboard = int(sim_t)
        if stream.container == "gps":
            values = telemetry.gps_values(state, onboard)
        elif stream.container == "payload":
            values = telemetry.payload_values(state, onboard)
        elif stream.container == "housekeeping":
            values = telemetry.housekeeping_values(state, onboard, self._battery_v)
        else:
            return
        packet = encode_packet(self.db, stream.container, values, stream.take_seq())
        self._send(conn, packet)

    def _send_event(self, conn, sim_t: float, code: int) -> None:
        values = telemetry.event_values(int(sim_t), code)
        packet = encode_packet(self.db, "events", values, self._event_seq)
        self._event_seq = (self._event_seq + 1) % 16384
        self._send(conn, packet)

    def _send(self, conn, packet: bytes) -> None:
        try:
            conn.sendall(packet)
        except OSError:
            raise SystemExit("client disconnected")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Etana telemetry simulator")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--speed", type=float, default=60.0,
                        help="sim-seconds per real-second (default 60x)")
    parser.add_argument("--mdb", type=Path,
                        default=Path(__file__).resolve().parents[4] / "mdb" / "etana.yaml")
    args = parser.parse_args()

    if not args.mdb.exists():
        raise SystemExit(
            f"mission database not found at {args.mdb}\n"
            f"pass --mdb with the path to etana.yaml"
        )

    db = load_mission_db(args.mdb)
    flight = Flight(FlightConfig())
    Simulator(db, flight, speed=args.speed).run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
