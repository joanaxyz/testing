from django.db import models
from django.db.models import Q

from common.constants import (
    COMMAND_COUNTED,
    COMMAND_DIAGNOSTIC,
    COMMAND_UNPROCESSABLE,
    RESULT_INVALID,
    RESULT_TARGET_MATCHED,
    RESULT_TARGET_NOT_YET_MATCHED,
    RESULT_UNPROCESSABLE,
)


class CommandStep(models.Model):
    class ResultCategory(models.TextChoices):
        TARGET_MATCHED = RESULT_TARGET_MATCHED, "Target matched"
        TARGET_NOT_YET_MATCHED = RESULT_TARGET_NOT_YET_MATCHED, "Target not yet matched"
        UNPROCESSABLE = RESULT_UNPROCESSABLE, "Unprocessable"
        INVALID = RESULT_INVALID, "Invalid"

    class CommandClassification(models.TextChoices):
        COUNTED = COMMAND_COUNTED, "Counted action"
        DIAGNOSTIC = COMMAND_DIAGNOSTIC, "Non-counted diagnostic"
        UNPROCESSABLE = COMMAND_UNPROCESSABLE, "Unprocessable"

    challenge_run = models.ForeignKey(
        "challenges.ChallengeRun",
        null=True,
        blank=True,
        related_name="steps",
        on_delete=models.CASCADE,
    )
    attempt = models.ForeignKey(
        "adventures.AdventureRun",
        null=True,
        blank=True,
        related_name="steps",
        on_delete=models.CASCADE,
    )
    adventure_tier_run = models.ForeignKey(
        "adventures.AdventureLevelTierRun",
        null=True,
        blank=True,
        related_name="steps",
        on_delete=models.CASCADE,
    )
    command_text = models.TextField()
    terminal_output = models.TextField(blank=True)
    result_category = models.CharField(max_length=32, choices=ResultCategory.choices)
    command_classification = models.CharField(max_length=32, choices=CommandClassification.choices)
    # The normalized form of command_text plus whether the engine could process
    # it. Folded in from the former one-to-one CommandLog so logging a command is
    # part of the step INSERT (one fewer write per command) and the command
    # history is a same-table read instead of a join. The raw command lived on
    # CommandLog.raw_command, but that was always identical to command_text, so
    # it was dropped rather than carried over.
    normalized_command = models.TextField(blank=True)
    was_processable = models.BooleanField(default=False)
    counted_increment = models.PositiveIntegerField(default=0)
    attempt_number = models.PositiveIntegerField()
    counted_total_after = models.PositiveIntegerField(default=0)
    state_hash = models.CharField(max_length=128, blank=True)
    expected_state_hash = models.CharField(max_length=128, blank=True)
    repository_state = models.JSONField(default=dict, blank=True)
    visualization_snapshot = models.JSONField(default=dict, blank=True)
    contextual_feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["challenge_run", "id"], name="cmdstep_run_id_idx"),
            # Adventure history is queried by the run held in attempt.
            models.Index(fields=["attempt", "id"], name="cmdstep_attempt_id_idx"),
            models.Index(fields=["adventure_tier_run", "id"], name="cmdstep_tier_run_id_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        challenge_run__isnull=False,
                        attempt__isnull=True,
                        adventure_tier_run__isnull=True,
                    )
                    | Q(
                        challenge_run__isnull=True,
                        attempt__isnull=False,
                        adventure_tier_run__isnull=True,
                    )
                    | Q(
                        challenge_run__isnull=True,
                        attempt__isnull=True,
                        adventure_tier_run__isnull=False,
                    )
                ),
                name="command_step_exactly_one_parent",
            ),
            models.CheckConstraint(
                condition=(
                    Q(attempt_number__gte=1)
                    & Q(counted_increment__lte=1)
                    & Q(counted_total_after__gte=models.F("counted_increment"))
                ),
                name="command_step_valid_counts",
            ),
        ]
