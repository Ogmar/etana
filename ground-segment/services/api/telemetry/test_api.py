"""Tests for the read-only telemetry API."""

from pathlib import Path

from django.test import TestCase
from django.utils import timezone

from ccsds import decode_packet, encode_packet, load_mission_db
from telemetry import archive
from telemetry.models import Flight

REAL_MDB = Path(__file__).resolve().parents[4] / "mdb" / "etana.yaml"


class ApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.db = load_mission_db(REAL_MDB)
        cls.flight = Flight.objects.create(name="T1")
        # a couple of GPS packets and an event
        for seq, alt in enumerate((100, 200, 300)):
            values = {"onboard_time": seq * 10, "gps_latitude": 454200000 + seq,
                      "gps_longitude": -738900000, "gps_altitude": alt,
                      "gps_fix": 3, "gps_sats": 9}
            raw = encode_packet(cls.db, "gps", values, seq)
            archive.store_packet(decode_packet(cls.db, raw), raw,
                                 received_at=timezone.now(), flight=cls.flight)
        ev = encode_packet(cls.db, "events", {"onboard_time": 5, "event": 1}, 0)
        archive.store_packet(decode_packet(cls.db, ev), ev,
                             received_at=timezone.now(), flight=cls.flight)
        archive.record_loss(100, 4, 7, 3, flight=cls.flight)

    def test_flight_list(self):
        r = self.client.get("/api/flights/")
        assert r.status_code == 200
        assert r.json()[0]["packet_count"] == 4

    def test_flight_detail_404(self):
        assert self.client.get("/api/flights/999/").status_code == 404

    def test_parameter_names(self):
        r = self.client.get(f"/api/flights/{self.flight.id}/parameters/")
        assert "gps_altitude" in r.json()

    def test_series(self):
        r = self.client.get(f"/api/flights/{self.flight.id}/series/gps_altitude/")
        body = r.json()
        assert body["count"] == 3
        assert [p["engineering_value"] for p in body["points"]] == [100.0, 200.0, 300.0]

    def test_latest_state(self):
        r = self.client.get(f"/api/flights/{self.flight.id}/latest/")
        latest = r.json()["latest"]
        assert latest["gps_altitude"] == 300.0     # most recent
        assert latest["gps_fix"] == "dgps_fix"      # enum label

    def test_loss_summary(self):
        r = self.client.get(f"/api/flights/{self.flight.id}/loss/")
        rows = r.json()
        assert rows[0]["apid"] == 100 and rows[0]["lost_count"] == 3

    def test_events(self):
        r = self.client.get(f"/api/flights/{self.flight.id}/events/")
        assert r.json()[0]["event"] == "launch_detected"

    def test_series_isolated_by_flight(self):
        """A second flight's data does not bleed into the first."""
        other = Flight.objects.create(name="T2")
        r = self.client.get(f"/api/flights/{other.id}/series/gps_altitude/")
        assert r.json()["count"] == 0


class LiveEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.db = load_mission_db(REAL_MDB)
        cls.flight = Flight.objects.create(name="Live")
        for seq, alt in enumerate((100, 200, 300, 400)):
            values = {"onboard_time": seq * 10, "gps_latitude": 454200000 + seq * 1000,
                      "gps_longitude": -738900000, "gps_altitude": alt,
                      "gps_fix": 3, "gps_sats": 9}
            raw = encode_packet(cls.db, "gps", values, seq)
            archive.store_packet(decode_packet(cls.db, raw), raw,
                                 received_at=timezone.now(), flight=cls.flight)

    def test_since_returns_incremental(self):
        # First poll from 0 gets everything.
        r1 = self.client.get(f"/api/flights/{self.flight.id}/since/?since=0").json()
        assert r1["count"] > 0
        cursor = r1["cursor"]
        # Second poll from the cursor gets nothing new.
        r2 = self.client.get(f"/api/flights/{self.flight.id}/since/?since={cursor}").json()
        assert r2["count"] == 0
        assert r2["cursor"] == cursor

    def test_since_reports_status(self):
        r = self.client.get(f"/api/flights/{self.flight.id}/since/?since=0").json()
        assert r["flight_status"] == "active"
        self.flight.mark_complete()
        r2 = self.client.get(f"/api/flights/{self.flight.id}/since/?since=0").json()
        assert r2["flight_status"] == "complete"

    def test_since_parameter_filter(self):
        r = self.client.get(
            f"/api/flights/{self.flight.id}/since/?since=0&parameter=gps_altitude").json()
        assert all(s["parameter_name"] == "gps_altitude" for s in r["samples"])
        assert r["count"] == 4

    def test_track_returns_path(self):
        r = self.client.get(f"/api/flights/{self.flight.id}/track/").json()
        assert r["count"] == 4
        p = r["points"][0]
        assert "lat" in p and "lon" in p and "altitude" in p

    def test_flight_status_in_detail(self):
        r = self.client.get(f"/api/flights/{self.flight.id}/").json()
        assert r["status"] == "active"
        assert r["ended_at"] is None
