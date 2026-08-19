"""Tests for the telemetry archive models.

Run against SQLite (ETANA_DB=sqlite) so no Postgres is needed in CI; the ORM
makes the models behave identically on Postgres.
"""

from django.test import TestCase
from django.utils import timezone

from telemetry.models import RawPacket, ParameterSample, LossEvent


class RawPacketTests(TestCase):
    def test_stores_bytes_bit_exact(self):
        data = bytes([0x00, 0x64, 0xC0, 0x05, 0x00, 0x0F, 0xDE, 0xAD])
        pkt = RawPacket.objects.create(
            apid=100, sequence_count=5, raw_bytes=data,
            received_at=timezone.now(), onboard_time=3600)
        reloaded = RawPacket.objects.get(pk=pkt.pk)
        assert bytes(reloaded.raw_bytes) == data

    def test_link_stats_default_null(self):
        pkt = RawPacket.objects.create(
            apid=100, sequence_count=0, raw_bytes=b"\x00",
            received_at=timezone.now())
        assert pkt.rssi is None
        assert pkt.snr is None

    def test_link_stats_can_be_populated(self):
        pkt = RawPacket.objects.create(
            apid=100, sequence_count=0, raw_bytes=b"\x00",
            received_at=timezone.now(), rssi=-95, snr=7.5, source="lora")
        reloaded = RawPacket.objects.get(pk=pkt.pk)
        assert reloaded.rssi == -95
        assert reloaded.snr == 7.5
        assert reloaded.source == "lora"


class ParameterSampleTests(TestCase):
    def setUp(self):
        self.pkt = RawPacket.objects.create(
            apid=100, sequence_count=1, raw_bytes=b"\x00",
            received_at=timezone.now(), onboard_time=100)

    def test_numeric_parameter(self):
        s = ParameterSample.objects.create(
            raw_packet=self.pkt, apid=100, parameter_name="gps_altitude",
            raw_value=12000, engineering_value=12000.0,
            received_at=self.pkt.received_at)
        assert s.engineering_value == 12000.0
        assert s.engineering_label is None

    def test_enumerated_parameter(self):
        s = ParameterSample.objects.create(
            raw_packet=self.pkt, apid=100, parameter_name="gps_fix",
            raw_value=3, engineering_label="dgps_fix",
            received_at=self.pkt.received_at)
        assert s.engineering_label == "dgps_fix"
        assert s.engineering_value is None

    def test_config_driven_no_schema_per_parameter(self):
        """Different parameters are just different rows, not different columns."""
        for name, raw in [("ozone_raw", 1000), ("co2_raw", 40000), ("battery", 3700)]:
            ParameterSample.objects.create(
                raw_packet=self.pkt, apid=self.pkt.apid, parameter_name=name,
                raw_value=raw, engineering_value=float(raw),
                received_at=self.pkt.received_at)
        assert ParameterSample.objects.count() == 3
        names = set(ParameterSample.objects.values_list("parameter_name", flat=True))
        assert names == {"ozone_raw", "co2_raw", "battery"}

    def test_reverse_relation_from_packet(self):
        ParameterSample.objects.create(
            raw_packet=self.pkt, apid=100, parameter_name="gps_sats",
            raw_value=9, engineering_value=9.0, received_at=self.pkt.received_at)
        assert self.pkt.samples.count() == 1

    def test_deleting_packet_cascades_to_samples(self):
        ParameterSample.objects.create(
            raw_packet=self.pkt, apid=100, parameter_name="gps_sats",
            raw_value=9, engineering_value=9.0, received_at=self.pkt.received_at)
        self.pkt.delete()
        assert ParameterSample.objects.count() == 0


class LossEventTests(TestCase):
    def test_records_a_gap(self):
        ev = LossEvent.objects.create(
            apid=100, expected_sequence=6, received_sequence=9,
            lost_count=3, detected_at=timezone.now())
        assert ev.lost_count == 3
        assert "lost=3" in str(ev)

    def test_time_series_query_by_parameter(self):
        """The core query the dashboard needs: one parameter's values over time."""
        pkt = RawPacket.objects.create(
            apid=100, sequence_count=0, raw_bytes=b"\x00",
            received_at=timezone.now())
        for alt in (100, 200, 300):
            ParameterSample.objects.create(
                raw_packet=pkt, apid=100, parameter_name="gps_altitude",
                raw_value=alt, engineering_value=float(alt),
                received_at=timezone.now())
        series = list(ParameterSample.objects
                      .filter(parameter_name="gps_altitude")
                      .order_by("received_at")
                      .values_list("engineering_value", flat=True))
        assert series == [100.0, 200.0, 300.0]
