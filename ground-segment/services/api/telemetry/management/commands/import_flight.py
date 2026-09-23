"""Imports a flight exported by export_flight, then regenerates its parameter
samples from the imported raw packets — raw is the archive's source of truth,
so parameters are always re-derived on import rather than copied directly
(see telemetry/archive.py's reprocess()).

Intended for moving a flight between databases (e.g. local dev -> a freshly
deployed environment with no data yet), not as a general-purpose restore tool:
it assumes the target database doesn't already have rows with colliding
primary keys.
"""

from pathlib import Path

from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ccsds import load_mission_db
from telemetry import archive

DEFAULT_MDB = Path(__file__).resolve().parents[6] / "mdb" / "etana.yaml"


class Command(BaseCommand):
    help = "Import a flight exported by export_flight and regenerate its parameter samples."

    def add_arguments(self, parser):
        parser.add_argument("input", help="Path to a JSON file from export_flight")
        parser.add_argument(
            "--mdb", default=str(DEFAULT_MDB),
            help="Mission database to decode with (default: the repo's mdb/etana.yaml)",
        )

    def handle(self, *args, **options):
        try:
            with open(options["input"]) as f:
                data = f.read()
        except FileNotFoundError:
            raise CommandError(f"No such file: {options['input']}")

        with transaction.atomic():
            count = 0
            for obj in serializers.deserialize("json", data):
                obj.save()
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Imported {count} rows from {options['input']}"))

        db = load_mission_db(options["mdb"])
        result = archive.reprocess(db, dry_run=False)
        self.stdout.write(self.style.SUCCESS(
            f"Regenerated parameter samples from raw: "
            f"{result['raw_packets']} raw packets -> {result['samples_written']} samples"
        ))
