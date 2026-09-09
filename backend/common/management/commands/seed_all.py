"""Seed all official data with a safe, non-destructive default.

Usage:
    python manage.py seed_all
        Upsert official curriculum and command-library rows. Player progress is
        preserved.

    python manage.py seed_all --reset --confirm-reset
        Delete official curriculum rows and dependent run/progress rows before
        rebuilding. This is intentionally verbose so accidental production
        data loss is difficult.

Production reset additionally requires ALLOW_DESTRUCTIVE_SEED_RESET=True.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Safely seed all official data: curriculum and command library."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Clear seeded curriculum and dependent player progress before seeding.",
        )
        parser.add_argument(
            "--confirm-reset",
            action="store_true",
            help="Required together with --reset to acknowledge destructive deletion.",
        )
        parser.add_argument(
            "--validate",
            action="store_true",
            help="Validate curriculum shape, simulator support, and official solutions.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        reset = bool(options.get("reset"))
        confirmed = bool(options.get("confirm_reset"))

        if confirmed and not reset:
            raise CommandError("--confirm-reset is only valid together with --reset.")
        if reset and not confirmed:
            raise CommandError(
                "Destructive reset refused. Re-run with both --reset and --confirm-reset."
            )
        if reset and not settings.DEBUG and not settings.ALLOW_DESTRUCTIVE_SEED_RESET:
            raise CommandError(
                "Destructive reset is disabled when DJANGO_DEBUG=False. "
                "Set ALLOW_DESTRUCTIVE_SEED_RESET=True only for an intentional, "
                "time-bounded maintenance operation."
            )

        verbosity = options.get("verbosity", 1)
        self.stdout.write(self.style.MIGRATE_HEADING("1/3 Curriculum"))
        call_command(
            "seed_curriculum",
            reset=reset,
            validate=options.get("validate", False),
            verbosity=verbosity,
        )

        self.stdout.write(self.style.MIGRATE_HEADING("2/3 Runebound Turret"))
        call_command("seed_legacy_modules", verbosity=verbosity)

        self.stdout.write(self.style.MIGRATE_HEADING("3/3 Command library"))
        call_command("seed_command_library", verbosity=verbosity)

        mode = "reset and seeded" if reset else "safely upserted"
        self.stdout.write(self.style.SUCCESS(f"seed_all complete — {mode} official data."))
