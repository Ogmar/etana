"""Read-only API over the telemetry archive.

The API only reads: ingestion writes the archive, these endpoints serve it. Each
view wraps a query the dashboard needs — a parameter's time series, the latest
GPS state, per-APID loss, the event timeline — into JSON.
"""

from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Flight, LossEvent, ParameterSample, RawPacket
from .serializers import (
    EventSerializer, FlightSerializer, LossSummarySerializer, SamplePointSerializer,
)


@api_view(["GET"])
def flight_list(request):
    """All flights, newest first, each with its packet count."""
    flights = Flight.objects.annotate(packet_count=Count("packets"))
    return Response(FlightSerializer(flights, many=True).data)


@api_view(["GET"])
def flight_detail(request, flight_id):
    """One flight with summary counts."""
    flight = get_object_or_404(
        Flight.objects.annotate(packet_count=Count("packets")), pk=flight_id)
    return Response(FlightSerializer(flight).data)


@api_view(["GET"])
def parameter_names(request, flight_id):
    """The distinct parameter names available for this flight (for building UI)."""
    flight = get_object_or_404(Flight, pk=flight_id)
    names = (ParameterSample.objects.filter(raw_packet__flight=flight)
             .values_list("parameter_name", flat=True).distinct().order_by("parameter_name"))
    return Response(list(names))


@api_view(["GET"])
def telemetry_series(request, flight_id, parameter_name):
    """The full time series for one parameter in one flight.

    Returns points in onboard-time order — the shape a chart consumes directly.
    """
    flight = get_object_or_404(Flight, pk=flight_id)
    samples = (ParameterSample.objects
               .filter(raw_packet__flight=flight, parameter_name=parameter_name)
               .order_by("onboard_time", "received_at")
               .values("onboard_time", "received_at", "raw_value",
                       "engineering_value", "engineering_label"))
    data = SamplePointSerializer(samples, many=True).data
    return Response({
        "flight_id": flight.id,
        "parameter": parameter_name,
        "count": len(data),
        "points": data,
    })


@api_view(["GET"])
def latest_state(request, flight_id):
    """The most recent value of each GPS parameter — the 'current position' dot."""
    flight = get_object_or_404(Flight, pk=flight_id)
    gps_params = ["gps_latitude", "gps_longitude", "gps_altitude", "gps_fix", "gps_sats"]
    latest = {}
    for name in gps_params:
        s = (ParameterSample.objects
             .filter(raw_packet__flight=flight, parameter_name=name)
             .order_by("-onboard_time", "-received_at").first())
        if s is not None:
            latest[name] = s.engineering_label if s.engineering_label is not None else s.engineering_value
    return Response({"flight_id": flight.id, "latest": latest})


@api_view(["GET"])
def telemetry_since(request, flight_id):
    """Incremental fetch for live polling: samples newer than a cursor.

    The dashboard passes ?since=<id> (the highest sample id it has seen) and gets
    only newer samples, plus the new cursor to use next poll and whether the
    flight is still active. This is how the live view stays current without
    re-fetching the whole series each second.

    Optional ?parameter=<name> narrows to one parameter.
    """
    flight = get_object_or_404(Flight, pk=flight_id)
    since = int(request.query_params.get("since", 0))

    qs = (ParameterSample.objects
          .filter(raw_packet__flight=flight, id__gt=since)
          .order_by("id"))
    param = request.query_params.get("parameter")
    if param:
        qs = qs.filter(parameter_name=param)

    rows = list(qs.values("id", "parameter_name", "onboard_time", "received_at",
                          "raw_value", "engineering_value", "engineering_label")[:5000])
    new_cursor = rows[-1]["id"] if rows else since

    return Response({
        "flight_id": flight.id,
        "flight_status": flight.status,
        "since": since,
        "cursor": new_cursor,
        "count": len(rows),
        "samples": rows,
    })


@api_view(["GET"])
def track(request, flight_id):
    """The lat/lon/altitude path of the flight, for drawing the map trail."""
    flight = get_object_or_404(Flight, pk=flight_id)

    # Pull the three GPS series and zip them by onboard_time.
    def series(name):
        return {s["onboard_time"]: s["engineering_value"] for s in
                ParameterSample.objects
                .filter(raw_packet__flight=flight, parameter_name=name)
                .values("onboard_time", "engineering_value")}

    lat = series("gps_latitude")
    lon = series("gps_longitude")
    alt = series("gps_altitude")
    times = sorted(set(lat) & set(lon))
    points = [{"onboard_time": t, "lat": lat[t], "lon": lon[t],
               "altitude": alt.get(t)} for t in times]
    return Response({"flight_id": flight.id, "count": len(points), "points": points})


@api_view(["GET"])
def loss_summary(request, flight_id):
    """Per-APID loss totals — the data behind the loss badges."""
    flight = get_object_or_404(Flight, pk=flight_id)
    rows = (LossEvent.objects.filter(flight=flight)
            .values("apid")
            .annotate(lost_count=Sum("lost_count"), event_count=Count("id"))
            .order_by("apid"))
    return Response(LossSummarySerializer(rows, many=True).data)


@api_view(["GET"])
def events(request, flight_id):
    """The flight's events (launch, burst, descent, landing) in order."""
    flight = get_object_or_404(Flight, pk=flight_id)
    samples = (ParameterSample.objects
               .filter(raw_packet__flight=flight, parameter_name="event")
               .order_by("onboard_time", "received_at"))
    data = [{"onboard_time": s.onboard_time, "received_at": s.received_at,
             "event": s.engineering_label} for s in samples]
    return Response(EventSerializer(data, many=True).data)
