"""Tests for replay/reprocess: regeneration, dry-run, and safety."""

from pathlib import Path

from django.test import TestCase
from django.utils import timezone

from ccsds import decode_packet, encode_packet, load_mission_db
from telemetry import archive
from telemetry.models import ParameterSample, RawPacket

REAL_MDB = Path(__file__).resolve().parents[4] / "mdb" / "etana.yaml"


class ReprocessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.db = load_mission_db(REAL_MDB)

    def _archive_gps(self, seq, alt):
        values = {"onboard_time": seq, "gps_latitude": 0, "gps_longitude": 0,
                  "gps_altitude": alt, "gps_fix": 3, "gps_sats": 9}
        raw = encode_packet(self.db, "gps", values, seq)
        archive.store_packet(decode_packet(self.db, raw), raw,
                             received_at=timezone.now())

    def test_dry_run_writes_nothing(self):
        self._archive_gps(0, 100)
        before = ParameterSample.objects.count()
        result = archive.reprocess(self.db, dry_run=True)
        assert result["dry_run"] is True
        assert result["samples_written"] == 0
        assert ParameterSample.objects.count() == before  # unchanged

    def test_reprocess_regenerates_samples(self):
        self._archive_gps(0, 100)
        self._archive_gps(1, 200)
        before = ParameterSample.objects.count()
        result = archive.reprocess(self.db, dry_run=False)
        assert result["samples_written"] == before
        assert ParameterSample.objects.count() == before  # same count, regenerated

    def test_reprocess_never_touches_raw(self):
        self._archive_gps(0, 100)
        raw_before = RawPacket.objects.count()
        raw_bytes_before = bytes(RawPacket.objects.first().raw_bytes)
        archive.reprocess(self.db, dry_run=False)
        assert RawPacket.objects.count() == raw_before
        assert bytes(RawPacket.objects.first().raw_bytes) == raw_bytes_before

    def test_reprocess_reflects_new_calibration(self):
        """Re-decoding with changed coefficients yields changed values."""
        import tempfile, yaml
        self._archive_gps(0, 100)
        # An ozone packet, whose value is calibrated.
        ov = {"onboard_time": 0, "ozone_raw": 1000, "co2_raw": 40000, "payload_temp": 0}
        raw = encode_packet(self.db, "payload", ov, 0)
        archive.store_packet(decode_packet(self.db, raw), raw, received_at=timezone.now())
        old_val = ParameterSample.objects.get(parameter_name="ozone_raw").engineering_value

        mdb = yaml.safe_load(open(REAL_MDB))
        mdb["parameter_types"]["ozone_counts"]["calibrator"]["coefficients"] = [0.0, 0.1]
        tmp = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
        yaml.safe_dump(mdb, tmp); tmp.close()
        new_db = load_mission_db(tmp.name)

        archive.reprocess(new_db, dry_run=False)
        new_val = ParameterSample.objects.get(parameter_name="ozone_raw").engineering_value
        assert new_val != old_val
        assert new_val == 1000 * 0.1  # new slope applied to raw count
