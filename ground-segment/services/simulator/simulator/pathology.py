"""Link pathology model: packet loss and corruption.

Real radio links do not lose packets uniformly. Loss comes in bursts — a few
seconds of dropout as the antenna nulls during spin or fades at the horizon —
over a low steady background rate. This module models that: a background drop
probability plus occasional burst windows during which the drop probability is
high.

The model is pure and deterministic given a seed, so it is testable and
reproducible. It decides only *whether* to drop or corrupt; the transmitter is
responsible for still advancing the sequence counter on a drop (a lost packet
was assigned a sequence number and sent — the ground just never received it),
which is what makes the loss detectable as a sequence gap.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class PathologyConfig:
    """Link pathology parameters. Defaults are 'light loss' for on-by-default."""

    background_loss: float = 0.01      # steady per-packet drop probability
    burst_loss: float = 0.6            # drop probability while in a loss burst
    burst_start_prob: float = 0.002    # per-packet chance a burst begins
    burst_min_s: float = 2.0           # burst duration range (sim-seconds)
    burst_max_s: float = 8.0
    corruption_prob: float = 0.003     # per-(kept)-packet chance of corruption
    enabled: bool = True


class Pathology:
    """Decides, per packet, whether it is lost or corrupted.

    Call `should_drop(sim_t)` before sending; if it returns False, call
    `should_corrupt()` to decide whether to mangle the bytes that are sent.
    """

    def __init__(self, config: PathologyConfig | None = None, seed: int | None = None):
        self.cfg = config or PathologyConfig()
        self._rng = random.Random(seed)
        self._burst_until: float | None = None

    def should_drop(self, sim_t: float) -> bool:
        """Return True if this packet should be dropped (not transmitted)."""
        if not self.cfg.enabled:
            return False

        # Are we currently in a burst?
        in_burst = self._burst_until is not None and sim_t < self._burst_until
        if self._burst_until is not None and sim_t >= self._burst_until:
            self._burst_until = None  # burst ended
            in_burst = False

        # Possibly start a new burst.
        if not in_burst and self._rng.random() < self.cfg.burst_start_prob:
            duration = self._rng.uniform(self.cfg.burst_min_s, self.cfg.burst_max_s)
            self._burst_until = sim_t + duration
            in_burst = True

        rate = self.cfg.burst_loss if in_burst else self.cfg.background_loss
        return self._rng.random() < rate

    def should_corrupt(self) -> bool:
        """Return True if a transmitted packet should have its bytes corrupted."""
        if not self.cfg.enabled:
            return False
        return self._rng.random() < self.cfg.corruption_prob

    def corrupt(self, packet: bytes) -> bytes:
        """Flip bits in a random byte of the packet body (not the header, so it
        still frames correctly but fails to decode cleanly or yields bad data)."""
        if len(packet) <= 6:
            return packet
        data = bytearray(packet)
        idx = self._rng.randrange(6, len(data))  # corrupt a data byte
        data[idx] ^= self._rng.randint(1, 255)
        return bytes(data)
