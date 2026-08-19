"""Tests for the link pathology model."""

from simulator.pathology import Pathology, PathologyConfig


def test_disabled_never_drops_or_corrupts():
    p = Pathology(PathologyConfig(enabled=False), seed=1)
    assert not any(p.should_drop(t) for t in range(1000))
    assert not any(p.should_corrupt() for _ in range(1000))


def test_seed_is_deterministic():
    """Same seed and config produce identical drop decisions."""
    cfg = PathologyConfig(background_loss=0.1)
    a = Pathology(cfg, seed=7)
    b = Pathology(cfg, seed=7)
    seq_a = [a.should_drop(t * 0.1) for t in range(500)]
    seq_b = [b.should_drop(t * 0.1) for t in range(500)]
    assert seq_a == seq_b


def test_background_loss_rate_is_roughly_configured():
    """With no bursts, the drop fraction approximates the background rate."""
    cfg = PathologyConfig(background_loss=0.1, burst_start_prob=0.0)
    p = Pathology(cfg, seed=3)
    n = 20000
    drops = sum(p.should_drop(t * 0.1) for t in range(n))
    rate = drops / n
    assert 0.08 < rate < 0.12  # near 0.10


def test_zero_loss_config_drops_nothing():
    cfg = PathologyConfig(background_loss=0.0, burst_start_prob=0.0)
    p = Pathology(cfg, seed=5)
    assert not any(p.should_drop(t * 0.1) for t in range(2000))


def test_bursts_raise_the_local_loss_rate():
    """A config with frequent bursts loses more than background alone.

    Each detector is created once and sampled over the whole window; creating a
    fresh Pathology per iteration would reset its RNG and repeat one draw.
    """
    background_only = PathologyConfig(background_loss=0.02, burst_start_prob=0.0)
    with_bursts = PathologyConfig(background_loss=0.02, burst_start_prob=0.05,
                                  burst_loss=0.8)
    n = 5000
    bg_p = Pathology(background_only, seed=9)
    br_p = Pathology(with_bursts, seed=9)
    bg = sum(bg_p.should_drop(t * 0.1) for t in range(n))
    br = sum(br_p.should_drop(t * 0.1) for t in range(n))
    assert br > bg


def test_corrupt_changes_a_body_byte_not_header():
    p = Pathology(seed=2)
    original = bytes(range(20))  # 20-byte packet, header is first 6
    corrupted = p.corrupt(original)
    assert corrupted[:6] == original[:6]      # header intact
    assert corrupted != original             # something changed
    assert len(corrupted) == len(original)   # same length


def test_corrupt_leaves_tiny_packets_alone():
    """A header-only packet (<=6 bytes) has no body to corrupt."""
    p = Pathology(seed=2)
    tiny = bytes(range(6))
    assert p.corrupt(tiny) == tiny


def test_corruption_probability_respected():
    cfg = PathologyConfig(corruption_prob=0.2)
    p = Pathology(cfg, seed=4)
    n = 10000
    hits = sum(p.should_corrupt() for _ in range(n))
    assert 0.17 < hits / n < 0.23  # near 0.20
