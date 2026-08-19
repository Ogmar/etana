"""Tests for sequence-gap detection, including the 14-bit wrap."""

from ingestion.gap_detector import GapDetector, Gap, SEQUENCE_MODULUS


def test_first_packet_is_never_a_gap():
    d = GapDetector()
    assert d.check(100, 5) is None


def test_in_order_no_gap():
    d = GapDetector()
    d.check(100, 5)
    assert d.check(100, 6) is None
    assert d.check(100, 7) is None


def test_simple_gap():
    d = GapDetector()
    d.check(100, 5)
    gap = d.check(100, 9)  # 6, 7, 8 missing
    assert gap == Gap(apid=100, expected_sequence=6, received_sequence=9, lost_count=3)


def test_single_missing_packet():
    d = GapDetector()
    d.check(100, 5)
    gap = d.check(100, 7)  # 6 missing
    assert gap.lost_count == 1


def test_wrap_is_not_a_gap():
    """16383 -> 0 is a normal wrap, not 16383 lost packets."""
    d = GapDetector()
    d.check(100, SEQUENCE_MODULUS - 1)  # 16383
    assert d.check(100, 0) is None


def test_gap_across_wrap():
    """16382 -> 1 means 16383 and 0 were missed: 2 lost."""
    d = GapDetector()
    d.check(100, SEQUENCE_MODULUS - 2)  # 16382
    gap = d.check(100, 1)
    assert gap.lost_count == 2


def test_duplicate_is_not_loss():
    d = GapDetector()
    d.check(100, 5)
    d.check(100, 6)
    assert d.check(100, 6) is None  # same count again


def test_out_of_order_is_not_loss():
    d = GapDetector()
    d.check(100, 5)
    d.check(100, 8)   # this reports a gap (6,7 missing)
    assert d.check(100, 6) is None  # late arrival, behind expected: not loss


def test_apids_tracked_independently():
    d = GapDetector()
    d.check(100, 5)
    d.check(200, 100)
    assert d.check(100, 6) is None      # gps in order
    assert d.check(200, 105) is not None  # payload gapped
    assert d.check(100, 7) is None      # gps still fine


def test_loss_counts_accumulate_correctly():
    d = GapDetector()
    d.check(300, 0)
    total_lost = 0
    for seq in (2, 5, 6, 10):  # gaps: 1 | 3,4 | (none) | 7,8,9
        gap = d.check(300, seq)
        if gap:
            total_lost += gap.lost_count
    assert total_lost == 1 + 2 + 0 + 3  # = 6
