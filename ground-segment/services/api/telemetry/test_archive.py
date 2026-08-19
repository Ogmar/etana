"""Tests for the archive writer."""

from pathlib import Path

from django.test import TestCase

from ccsds import decode_packet, encode_packet, load_mission_db
from telemetry import archive
from telemetry.models import LossEvent, ParameterSample, RawPacket

REAL_MDB = Path(__file__).resolve().parents[4] / "mdb" / "etana.yaml"


class ArchiveWriterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.db = load_mission_db(REAL_MDB)

    def _gps_packet(self, seq=0):
        values = {"onboard_time": 100, "gps_latitude": 454200000,
                  "gps_longitude": -738900000, "gps_altitude": 12000,
                  "gps_fix": 3, "gps_sats": 9}
        raw = encode_packet(self.db, "gps", values, seq)
        return decode_packet(self.db, raw), raw

    def test_store_packet_creates_raw_and_samples(self):
        decoded, raw = self._gps_packet()
        archive.store_packet(decoded, raw)
        assert RawPacket.objects.count() == 1
        # gps has 6 fields -> 6 samples
        assert ParameterSample.objects.count() == 6

    def test_raw_bytes_preserved(self):
        decoded, raw = self._gps_packet()
        archive.store_packet(decoded, raw)
        assert bytes(RawPacket.objects.first().raw_bytes) == raw

    def test_numeric_and_enum_samples(self):
        decoded, raw = self._gps_packet()
        archive.store_packet(decoded, raw)
        alt = ParameterSample.objects.get(parameter_name="gps_altitude")
        fix = ParameterSample.objects.get(parameter_name="gps_fix")
        assert alt.engineering_value == 12000.0 and alt.engineering_label is None
        assert fix.engineering_label == "dgps_fix" and fix.engineering_value is None

    def test_onboard_time_captured(self):
        decoded, raw = self._gps_packet()
        pkt = archive.store_packet(decoded, raw)
        assert pkt.onboard_time == 100

    def test_record_loss(self):
        archive.record_loss(100, expected_sequence=6, received_sequence=9, lost_count=3)
        ev = LossEvent.objects.get()
        assert ev.lost_count == 3 and ev.apid == 100
