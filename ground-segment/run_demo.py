"""Run a full local demo: simulator + ingestion together, one command.

Starts the simulator (TCP server), waits for it to bind, then starts ingestion
(TCP client) against it. Streams a full simulated flight and shuts both down
cleanly on completion or Ctrl-C. Cross-platform (no shell scripting), so it runs
the same on Windows, macOS, and Linux.

    python run_demo.py                # 60x speed
    python run_demo.py --speed 200    # faster
    python run_demo.py --speed 1      # real time
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Etana simulator + ingestion demo")
    parser.add_argument("--speed", type=float, default=60.0,
                        help="sim-seconds per real-second (default 60)")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()

    sim_dir = ROOT / "services" / "simulator"
    ing_dir = ROOT / "services" / "ingestion"

    # Start the simulator (server) first so it is listening before ingestion connects.
    print(f"starting simulator (speed x{args.speed}) ...")
    simulator = subprocess.Popen(
        [sys.executable, "-m", "simulator.main",
         "--port", str(args.port), "--speed", str(args.speed)],
        cwd=sim_dir,
    )

    processes = [simulator]
    try:
        # Give the simulator a moment to bind its socket. We deliberately do NOT
        # probe by connecting: the simulator serves exactly one client and starts
        # the flight on connect, so a probe connection would consume the flight.
        time.sleep(1.0)
        if simulator.poll() is not None:
            raise RuntimeError("simulator exited before ingestion could connect")

        print("starting ingestion ...\n")
        ingestion = subprocess.Popen(
            [sys.executable, "-m", "ingestion.main", "--port", str(args.port)],
            cwd=ing_dir,
        )
        processes.append(ingestion)

        # The flight ends when the simulator finishes; ingestion follows.
        simulator.wait()
        ingestion.wait(timeout=10)
        return 0

    except KeyboardInterrupt:
        print("\ninterrupted; shutting down")
        return 130
    except RuntimeError as exc:
        print(f"\n{exc}")
        return 1
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
