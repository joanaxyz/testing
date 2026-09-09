from django.db import IntegrityError, transaction

from adventures.models import AdventureLevelTier, AdventureLevelTierProgress, AdventureLevelTierRun
from common.constants import DIFFICULTY_EASY, DIFFICULTY_MEDIUM, SESSION_STATUS_STARTED
from common.exceptions import Conflict, Locked
from common.runtime import discard_started_run
from progress.models import AdventureLevelTierCompletion

from .tier_variants import TierVariantSelectionService

RUN_HYDRATE_SELECT_RELATED = (
    "tier",
    "tier__adventure_level",
    "tier__adventure_level__chapter",
    "tier__adventure_level__chapter__story",
    "current_wave",
    "selected_variant",
    "selected_variant__wave",
    "prior_run",
    "player",
)


class AdventureLevelTierRunService:
    """Mirrors challenges.services.runs.ChallengeRunService for the
    AdventureLevelTier surface. New/parallel code only - the existing
    ChallengeRun/AdventureRun lifecycles are not touched."""

    @staticmethod
    def hydrate_run(run: AdventureLevelTierRun | int, *, player=None) -> AdventureLevelTierRun:
        from django.db.models import Prefetch

        from practice.models import CommandStep

        queryset = AdventureLevelTierRun.objects.select_related(
            *RUN_HYDRATE_SELECT_RELATED
        ).prefetch_related(
            Prefetch("steps", queryset=CommandStep.objects.order_by("id")),
        )
        queryset = queryset.filter(pk=run if isinstance(run, int) else run.pk)
        if player is not None:
            queryset = queryset.filter(player=player)
        return queryset.get()

    @transaction.atomic
    def start_run(
        self,
        *,
        player,
        tier: AdventureLevelTier,
        source_entry_point: str,
        prior_run: AdventureLevelTierRun | None = None,
        is_replay: bool = False,
    ) -> AdventureLevelTierRun:
        player.__class__.objects.select_for_update().get(pk=player.pk)

        already_completed = AdventureLevelTierCompletion.objects.filter(
            player=player,
            tier=tier,
        ).exists()

        if prior_run is not None:
            prior_run = (
                AdventureLevelTierRun.objects.select_for_update()
                .select_related("tier")
                .get(pk=prior_run.pk, player=player)
            )
            if prior_run.tier_id != tier.id:
                raise Locked("Retry runs must use the same difficulty tier.")

        # Best-effort variant-avoidance input for selector.select_variant
        # below - separate from `prior_run` (which stays a real, persisted
        # row or None, since it also drives chaining/retry_index/discard
        # logic further down). AdventureLevelTierRun rows are hard-deleted on
        # discard (see common.runtime.discard_started_run), so an
        # abandoned/never-solved attempt leaves no row behind even seconds
        # later - AdventureLevelTierProgress.last_shown_variant is the only
        # durable record of what the player was just looking at, and is set
        # on every start_run call below regardless of prior_run.
        selection_reference = prior_run
        if selection_reference is None and not is_replay and not already_completed:
            progress = AdventureLevelTierProgress.objects.filter(player=player, tier=tier).first()
            if progress and progress.last_shown_variant_id:
                selection_reference = AdventureLevelTierRun(
                    selected_variant=progress.last_shown_variant
                )

        # Replay semantics are authoritative on the server, mirroring
        # ChallengeRunService: once a tier has a completion (i.e. the
        # required_successful_attempts threshold has been reached for this
        # tier), every new direct launch is free play regardless of a stale
        # or omitted client flag. Below the threshold, a solved attempt still
        # counts toward AdventureLevelTierProgress even though it isn't a
        # "completion" yet - see AdventureLevelTierCommandProcessingService.
        is_replay = bool(is_replay or already_completed or (prior_run and prior_run.is_replay))
        if not is_replay:
            self._ensure_unlocked(player=player, tier=tier)

        active = self._active_run(player=player, tier=tier, for_update=True)
        if active and (not prior_run or active.id != prior_run.id):
            self.discard(run=active)

        wave = self._published_wave(tier)
        if wave is None:
            raise Locked("This difficulty tier has no published wave.")

        selector = TierVariantSelectionService()
        published_variants = list(
            wave.variants.filter(is_published=True).order_by("semantic_key", "id")
        )
        tried_keys = (
            selector._tried_variant_keys(player=player, tier=tier) if selection_reference else set()
        )
        variant = (
            self._replay_variant(player=player, tier=tier)
            if is_replay
            else selector.select_variant(
                player=player,
                tier=tier,
                prior_run=selection_reference,
                published_variants=published_variants,
                tried_variant_keys=tried_keys,
            )
        )
        if variant is None:
            raise Locked("This difficulty tier has no published variants.")

        # Mirrors the old app's ScenarioSession.changed_variant: only
        # meaningful for a real new attempt, not a replay (which intentionally
        # reopens the same completed variant, not a fresh selection).
        changed_variant = bool(
            not is_replay
            and selection_reference
            and selector.changed_between(
                prior=selection_reference.selected_variant, current=variant
            )
        )

        if not is_replay:
            AdventureLevelTierProgress.objects.update_or_create(
                player=player,
                tier=tier,
                defaults={"last_shown_variant": variant},
            )

        retry_index = prior_run.retry_index + 1 if prior_run else 0
        prior_reference = prior_run
        if prior_run and prior_run.status == SESSION_STATUS_STARTED:
            self.discard(run=prior_run)
            prior_reference = None

        try:
            run = AdventureLevelTierRun.objects.create(
                player=player,
                tier=tier,
                current_wave=wave,
                selected_variant=variant,
                prior_run=prior_reference,
                source_entry_point=source_entry_point,
                is_replay=is_replay,
                changed_variant=changed_variant,
                retry_index=retry_index,
                min_counted_commands=wave.min_counted_commands,
                max_counted_commands=wave.max_counted_commands,
                repository_state=variant.initial_state,
            )
        except IntegrityError as exc:
            raise Conflict("An active run already exists for this difficulty tier.") from exc
        return self.hydrate_run(run)

    def _active_run(self, *, player, tier: AdventureLevelTier, for_update: bool = False):
        queryset = AdventureLevelTierRun.objects.filter(
            player=player,
            tier=tier,
            status=SESSION_STATUS_STARTED,
        )
        if for_update:
            queryset = queryset.select_for_update()
        return queryset.first()

    def _ensure_unlocked(self, *, player, tier: AdventureLevelTier) -> None:
        if tier.difficulty == DIFFICULTY_EASY:
            return
        previous_difficulty = (
            DIFFICULTY_EASY if tier.difficulty == DIFFICULTY_MEDIUM else DIFFICULTY_MEDIUM
        )
        previous_tier = AdventureLevelTier.objects.filter(
            adventure_level_id=tier.adventure_level_id,
            difficulty=previous_difficulty,
            is_published=True,
        ).first()
        if (
            not previous_tier
            or not AdventureLevelTierCompletion.objects.filter(
                player=player,
                tier=previous_tier,
            ).exists()
        ):
            raise Locked("This difficulty tier is locked until the previous tier is completed.")

    def _published_wave(self, tier: AdventureLevelTier):
        return tier.waves.filter(is_published=True).order_by("sort_order", "id").first()

    def _replay_variant(self, *, player, tier: AdventureLevelTier):
        completion = (
            AdventureLevelTierCompletion.objects.select_related("tier_run__selected_variant")
            .filter(player=player, tier=tier)
            .first()
        )
        if not completion or not completion.tier_run:
            raise Locked("Free play is available only after completing this difficulty tier.")
        return completion.tier_run.selected_variant

    def discard(self, *, run: AdventureLevelTierRun) -> bool:
        return discard_started_run(run)
