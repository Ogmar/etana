"""Exports one flight's raw archive data to a JSON file.

Deliberately excludes ParameterSample: it's derived from RawPacket and
regenerable (see telemetry/archive.py's reprocess()), so shipping it around
would just be redundant derived data that can drift from its source. The
counterpart command, import_flight, regenerates it on the target database
instead of importing it directly.
"""

from django.core import serializers
from django.core.management.base import BaseCommand, CommandError

from telemetry.models import Flight, LossEvent, RawPacket


class Command(BaseCommand):
    help = "Export one flight's Flight/RawPacket/LossEvent rows to a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("flight_id", type=int)
        parser.add_argument("output", help="Path to write the JSON export to")

    def handle(self, *args, **options):
        try:
            flight = Flight.objects.get(pk=options["flight_id"])
        except Flight.DoesNotExist:
            raise CommandError(f"No flight with id {options['flight_id']}")

        packets = list(RawPacket.objects.filter(flight=flight))
        losses = list(LossEvent.objects.filter(flight=flight))
        objects = [flight, *packets, *losses]

        with open(options["output"], "w") as f:
            serializers.serialize("json", objects, stream=f, indent=2)

        self.stdout.write(self.style.SUCCESS(
            f"Exported flight {flight.pk} ({flight}): 1 flight, "
            f"{len(packets)} raw packets, {len(losses)} loss events -> {options['output']}"
        ))
