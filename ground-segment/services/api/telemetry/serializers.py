"""Serializers: turn model instances into JSON for the API."""

from rest_framework import serializers

from .models import Flight, LossEvent, ParameterSample


class FlightSerializer(serializers.ModelSerializer):
    packet_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Flight
        fields = ["id", "name", "started_at", "ended_at", "status",
                  "source", "notes", "packet_count"]


class SamplePointSerializer(serializers.Serializer):
    """One point in a parameter time series."""

    onboard_time = serializers.IntegerField()
    received_at = serializers.DateTimeField()
    raw_value = serializers.IntegerField()
    engineering_value = serializers.FloatField(allow_null=True)
    engineering_label = serializers.CharField(allow_null=True)


class LossSummarySerializer(serializers.Serializer):
    """Per-APID loss totals for a flight."""

    apid = serializers.IntegerField()
    lost_count = serializers.IntegerField()
    event_count = serializers.IntegerField()


class EventSerializer(serializers.Serializer):
    onboard_time = serializers.IntegerField(allow_null=True)
    received_at = serializers.DateTimeField()
    event = serializers.CharField()
