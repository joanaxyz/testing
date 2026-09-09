from django.db import transaction
from django.utils import timezone

from adventures.models import AdventureLevelTierProgress, AdventureLevelTierRun
from common.constants import (
    COMMAND_COUNTED,
    DIFFICULTY_EASY,
    RESULT_INVALID,
    RESULT_TARGET_MATCHED,
    RESULT_UNPROCESSABLE,
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_FAILED,
    SESSION_STATUS_STARTED,
)
from common.exceptions import Locked
from common.git.client_command_execution import ClientCommandExecutionService
from common.git.command_outcomes import command_outcome_payload
from common.git.repository_state import VariantTargetStateHashCache
from common.runtime import (
    apply_command_accounting,
    command_budget_exhausted,
    progress_rule_counts,
    repository_response_snapshot,
    update_fields_for_execution,
)
from common.services.performance import timing
from evaluation.completion import CompletionEvaluationContext, PracticeCompletionEvaluator
from practice.models import CommandStep
from practice.services.scaffolding import FeedbackGenerationService
from practice.services.visualization import RepositoryVisualizationService
from progress.models import AdventureLevelTierCompletion
from simulator.services import (
    RepositorySnapshotService,
    RepositoryStateSimulator,
)

from .tier_history import TierCommandHistoryCache


class AdventureLevelTierCommandProcessingService:
    """Mirrors challenges.services.command_processing.ChallengeCommandProcessingService.

    The single behavioral divergence is completion: a ChallengeTrial needs
    one successful attempt, but an AdventureLevelTierWave needs
    required_successful_attempts successes across separate runs. See
    _complete_run below - it always ends the run on solve (mirroring
    ChallengeRun: one row per attempt, never a long-lived looping run), but
    only writes AdventureLevelTierCompletion once the running
    AdventureLevelTierProgress counter reaches that threshold.
    """

    def __init__(self) -> None:
        self.state_tools = RepositoryStateSimulator()
        self.snapshotter = RepositorySnapshotService()
        self.visualizer = RepositoryVisualizationService()
        self.executor = ClientCommandExecutionService()

    # savepoint=False: the submit view already opened the transaction (to hold
    # the run-row lock), so join it directly instead of paying a nested
    # SAVEPOINT/RELEASE round trip. Standalone callers still get their own.
    @transaction.atomic(savepoint=False)
    def submit_command(self, *, run: AdventureLevelTierRun, command: str, execution: dict) -> dict:
        if run.status != SESSION_STATUS_STARTED:
            raise Locked("This adventure tier run has already ended.")

        state_tools = self.state_tools

        def span(stage: str):
            return timing(f"adventure_tier.command.{stage}", run_id=run.id)

        execution = self.executor.from_payload(
            repository_state=run.repository_state,
            command=command,
            execution=execution,
            timing_label="adventure_tier.command",
            run_id=run.id,
            expected_client_revision=run.total_attempts,
        )
        previous_state = execution.previous_state
        next_state = execution.next_state
        command_result = execution.result
        classification, increment = execution.classification, execution.increment
        result_category = RESULT_UNPROCESSABLE
        feedback = ""
        executed_commands: list[str] = []
        state_hash = ""
        previous_rules_passing = 0
        rules_passing = 0
        total_rules = max(1, run.max_counted_commands)
        evaluator = PracticeCompletionEvaluator()
        expected_state_hash = VariantTargetStateHashCache().hash_for(
            variant=run.selected_variant,
            state_tools=state_tools,
        )
        previous_history = TierCommandHistoryCache().history_for(run=run)
        initial_state = run.selected_variant.initial_state
        initial_evaluation = evaluator.evaluate(
            CompletionEvaluationContext(
                variant=run.selected_variant,
                next_state=initial_state,
                executed_commands=[],
                next_state_hash=state_tools.state_hash(initial_state),
                expected_state_hash=expected_state_hash,
            )
        )
        previous_evaluation = evaluator.evaluate(
            CompletionEvaluationContext(
                variant=run.selected_variant,
                next_state=previous_state,
                executed_commands=previous_history,
                next_state_hash=state_tools.state_hash_for_normalized(previous_state),
                expected_state_hash=expected_state_hash,
                next_state_already_normalized=True,
            )
        )
        previous_rules_passing, total_rules = progress_rule_counts(
            previous_evaluation,
            initial_evaluation,
        )
        rules_passing = previous_rules_passing

        if command_result.processed:
            with span("evaluate"):
                state_hash = state_tools.state_hash_for_normalized(next_state)
                executed_commands = [*previous_history, command_result.normalized_command]
                evaluation = evaluator.evaluate(
                    CompletionEvaluationContext(
                        variant=run.selected_variant,
                        next_state=next_state,
                        executed_commands=executed_commands,
                        next_state_hash=state_hash,
                        expected_state_hash=expected_state_hash,
                        next_state_already_normalized=True,
                    )
                )
                result_category = evaluation.result_category
                rules_passing, total_rules = progress_rule_counts(
                    evaluation,
                    initial_evaluation,
                )
                if _uses_contextual_feedback(run) and classification == COMMAND_COUNTED:
                    feedback = FeedbackGenerationService().describe(previous_state, next_state)
        else:
            result_category = (
                RESULT_INVALID
                if command.strip().lower().startswith("git")
                else RESULT_UNPROCESSABLE
            )
            state_hash = state_tools.state_hash_for_normalized(next_state)

        accounting = apply_command_accounting(
            run,
            classification=classification,
            increment=increment,
            total_field="total_attempts",
            counted_field="counted_action_total",
            diagnostic_field="non_counted_diagnostic_total",
        )

        solved = result_category == RESULT_TARGET_MATCHED
        failed = command_budget_exhausted(
            solved=solved,
            classification=classification,
            counted_total=run.counted_action_total,
            max_counted_commands=run.max_counted_commands,
        )

        with span("visualization"):
            visualization_snapshot = self.visualizer.snapshot(
                next_state,
                previous_state=previous_state,
                target_state=_visible_target_state(run),
                already_normalized=True,
            )
        with span("step_create"):
            step = CommandStep.objects.create(
                adventure_tier_run=run,
                command_text=command,
                terminal_output=command_result.output,
                result_category=result_category,
                command_classification=classification,
                counted_increment=increment,
                attempt_number=run.total_attempts,
                counted_total_after=run.counted_action_total,
                state_hash=state_hash,
                expected_state_hash=expected_state_hash,
                contextual_feedback=feedback,
                visualization_snapshot=visualization_snapshot,
                normalized_command=command_result.normalized_command,
                was_processable=command_result.processed,
            )
        if command_result.processed:
            TierCommandHistoryCache().remember_after_append(
                run=run,
                previous_history=executed_commands[:-1],
                normalized_command=command_result.normalized_command,
            )

        if execution.state_mutated:
            run.repository_state = next_state
        update_fields = set(
            update_fields_for_execution(
                accounting.changed_fields,
                state_mutated=execution.state_mutated,
            )
        )
        if solved:
            update_fields.update(self._complete_run(run))
        elif failed:
            run.status = SESSION_STATUS_FAILED
            run.ended_at = timezone.now()
            run.failure_reason = (
                "You ran out of counted commands before reaching the target repository state."
            )
            update_fields.update({"status", "ended_at", "failure_reason"})

        with span("run_save"):
            run.save(update_fields=sorted(update_fields))
        with span("response_snapshot"):
            repository_snapshot = repository_response_snapshot(
                self.snapshotter,
                command_result=command_result,
                previous_state=previous_state,
                next_state=next_state,
            )
        return {
            "run": run,
            "step": step,
            "terminal_output": command_result.output,
            "stdout": command_result.stdout,
            "stderr": command_result.stderr,
            "exit_code": command_result.exit_code,
            "command_family": command_result.command_family,
            "diagnostic_metadata": command_result.diagnostic_metadata,
            "repository_state": repository_snapshot,
            "visualization": visualization_snapshot,
            "evaluation_result": result_category,
            "command_classification": classification,
            "contextual_feedback": feedback,
            "command_outcome": command_outcome_payload(
                processed=command_result.processed,
                counted=classification == COMMAND_COUNTED,
                solved=solved,
                failed=failed,
                command_family=command_result.command_family or "default",
                previous_rules_passing=previous_rules_passing,
                rules_passing=rules_passing,
                total_rules=total_rules,
                max_counted_commands=run.max_counted_commands,
                counted_command_count=run.counted_action_total,
            ),
        }

    def _complete_run(self, run: AdventureLevelTierRun) -> set[str]:
        """Mark the run completed and, if solving it pushed the tier's
        successful-clears count to its required threshold, write
        AdventureLevelTierCompletion. Returns the saved field names.

        Unlike ChallengeRun (one success = done), a tier needs
        required_successful_attempts successes across separate runs, so the
        running count lives on AdventureLevelTierProgress (survives across
        runs) rather than on this run row. Every solved run still ends as
        COMPLETED regardless of whether the threshold was reached - mirrors
        ChallengeRun's one-row-per-attempt shape; the player starts a fresh
        run for the next clear attempt."""
        from adventures.scoring import stars as compute_stars

        run.status = SESSION_STATUS_COMPLETED
        run.completed_at = timezone.now()
        run.ended_at = run.completed_at
        first_try = run.retry_index == 0
        run.stars = compute_stars(
            solved=True,
            counted_commands=run.counted_action_total,
            budget=run.min_counted_commands,
            first_try=first_try,
        )
        if not run.is_replay:
            progress, _ = AdventureLevelTierProgress.objects.get_or_create(
                player=run.player, tier=run.tier
            )
            progress.successful_clears += 1
            progress.save(update_fields=["successful_clears", "updated_at"])

            required = run.current_wave.required_successful_attempts
            if progress.successful_clears >= required:
                completion, created = AdventureLevelTierCompletion.objects.get_or_create(
                    player=run.player,
                    tier=run.tier,
                    defaults={
                        "tier_run": run,
                        "stars": run.stars,
                        "counted_action_total": run.counted_action_total,
                    },
                )
                if not created and (
                    run.stars > completion.stars
                    or (
                        run.stars == completion.stars
                        and run.counted_action_total < completion.counted_action_total
                    )
                ):
                    completion.tier_run = run
                    completion.stars = run.stars
                    completion.counted_action_total = run.counted_action_total
                    completion.completed_at = run.completed_at
                    completion.save(
                        update_fields=[
                            "tier_run",
                            "stars",
                            "counted_action_total",
                            "completed_at",
                        ]
                    )
        return {"status", "completed_at", "ended_at", "stars"}


def _uses_contextual_feedback(run: AdventureLevelTierRun) -> bool:
    return run.tier.difficulty == DIFFICULTY_EASY


def _visible_target_state(run: AdventureLevelTierRun) -> dict | None:
    from common.constants import DIFFICULTY_MEDIUM

    if run.tier.difficulty in (DIFFICULTY_EASY, DIFFICULTY_MEDIUM):
        return run.selected_variant.target_state
    return None
