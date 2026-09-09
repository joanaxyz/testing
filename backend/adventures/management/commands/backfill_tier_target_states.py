"""Backfill AdventureLevelTierWaveVariant.target_state via command replay.

Ported legacy content (Modules 1-4) only ever authored a declarative
evaluation_spec, never a literal target-state snapshot - the old app had no
equivalent of a stored target state at all (confirmed: no such data exists
anywhere in archive/may30-old-modules). This command closes that gap the same
way curriculum/management/commands/generate_targets.py already does for
code-defined seed content: replay each variant's solution_commands against its
initial_state through the real frontend simulator
(frontend/scripts/generate-targets.mjs, reused unmodified), and write the
resulting state back.

Safe by construction: every migrated variant uses completion_policy.mode ==
"rules" (see curriculum/management/commands/seed_legacy_modules.py:ev()), so
target_state is never consulted for pass/fail - only for the Expected State
diagram. This command only touches rows where target_state is currently {}.

Run:
    python manage.py backfill_tier_target_states           # write
    python manage.py backfill_tier_target_states --check   # report only
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from adventures.models import AdventureLevelTierWaveVariant

REPO_ROOT = Path(__file__).resolve().parents[4]
FRONTEND_DIR = REPO_ROOT / "frontend"
GENERATOR_SCRIPT = FRONTEND_DIR / "scripts" / "generate-targets.mjs"


class Command(BaseCommand):
    help = (
        "Replay every AdventureLevelTierWaveVariant with an empty target_state "
        "through the frontend git engine and write the resulting state back."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--check",
            action="store_true",
            help="Report what would change without writing to the database.",
        )

    def handle(self, *args, **options) -> None:
        variants = list(
            AdventureLevelTierWaveVariant.objects.filter(target_state={})
            .select_related("wave")
            .order_by("id")
        )
        if not variants:
            self.stdout.write(self.style.SUCCESS("No variants need a target_state backfill."))
            return

        cases = self._collect_cases(variants)
        self.stdout.write(f"Collected {len(cases)} variant solutions.")
        targets = self._run_generator(cases)
        missing = sorted(set(cases) - set(targets))
        if missing:
            raise CommandError(f"Generator returned no target for: {', '.join(missing[:10])}")

        if options["check"]:
            self.stdout.write(
                self.style.SUCCESS(f"{len(targets)} variants would be backfilled.")
            )
            return

        updated = 0
        for variant in variants:
            target = targets.get(variant.case_id)
            if target is None:
                continue
            variant.target_state = target
            variant.save(update_fields=["target_state"])
            updated += 1
        self.stdout.write(self.style.SUCCESS(f"Backfilled target_state for {updated} variants."))

    def _collect_cases(self, variants: list[AdventureLevelTierWaveVariant]) -> dict[str, dict]:
        cases: dict[str, dict] = {}
        for variant in variants:
            case_id = variant.case_id or variant.slug
            if not case_id:
                continue
            if case_id in cases:
                raise CommandError(f"Duplicate variant case_id: {case_id!r}")
            workspace_files = [
                {**file, "after_command_index": file.get("after_command_index", 1)}
                for file in (variant.solution_workspace_files or [])
            ]
            cases[case_id] = {
                "initial_state": variant.initial_state or {},
                "solution_commands": list(variant.solution_commands or []),
                "workspace_files": workspace_files,
                "max_counted_commands": variant.wave.max_counted_commands,
            }
        return cases

    def _run_generator(self, cases: dict[str, dict]) -> dict[str, dict]:
        if not GENERATOR_SCRIPT.exists():
            raise CommandError(f"Generator script not found: {GENERATOR_SCRIPT}")
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "cases.json"
            output_path = Path(tmp) / "targets.json"
            input_path.write_text(json.dumps(cases), encoding="utf-8")
            try:
                result = subprocess.run(
                    ["node", str(GENERATOR_SCRIPT), str(input_path), str(output_path)],
                    cwd=FRONTEND_DIR,
                    capture_output=True,
                    text=True,
                )
            except FileNotFoundError as exc:
                raise CommandError(
                    "`node` was not found on PATH - install Node to run the generator."
                ) from exc
            if result.returncode != 0:
                raise CommandError(f"Target generator failed:\n{result.stderr or result.stdout}")
            return json.loads(output_path.read_text(encoding="utf-8"))
