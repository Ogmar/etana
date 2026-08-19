"""Per-APID sequence-gap detection.

Each packet carries a 14-bit sequence counter that increments per APID and wraps
at 16384. Tracking the last count seen for each APID lets us detect missing
packets: if the next count is not exactly one more than the last (modulo the
wrap), the difference is the number of packets lost.

This is pure logic — no database — so it is tested in isolation. The ingestion
loop calls `check` for each packet and persists any returned gap.
"""

from __future__ import annotations

from dataclasses import dataclass

SEQUENCE_MODULUS = 16384  # 2**14


@dataclass(frozen=True)
class Gap:
    """A detected sequence gap for one APID."""

    apid: int
    expected_sequence: int   # the count we expected next
    received_sequence: int   # the count we actually got
    lost_count: int          # how many packets are missing


class GapDetector:
    """Tracks the last sequence count per APID and reports gaps.

    A gap is reported when the received count is ahead of the expected count.
    A count equal to or behind the expected (duplicate or out-of-order) is not
    reported as loss; it returns None.
    """

    def __init__(self):
        self._last: dict[int, int] = {}

    def check(self, apid: int, sequence: int) -> Gap | None:
        """Register a received (apid, sequence) and return a Gap if packets were
        skipped since the last one for this APID, else None."""
        last = self._last.get(apid)
        self._last[apid] = sequence

        if last is None:
            return None  # first packet for this APID; nothing to compare

        expected = (last + 1) % SEQUENCE_MODULUS
        if sequence == expected:
            return None  # in order, no loss

        # Forward distance from expected to received, modulo the wrap.
        lost = (sequence - expected) % SEQUENCE_MODULUS

        # A large forward distance is almost certainly a duplicate or reordered
        # packet arriving late, not a near-complete-wrap loss. Treat the small
        # side as the truth: if the packet is "behind" expected, it's not loss.
        behind = (expected - sequence) % SEQUENCE_MODULUS
        if behind < lost:
            return None  # duplicate or out-of-order, not a gap

        return Gap(
            apid=apid,
            expected_sequence=expected,
            received_sequence=sequence,
            lost_count=lost,
        )
