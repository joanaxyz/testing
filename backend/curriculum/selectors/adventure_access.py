from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from adventures.models import AdventureLevel, AdventureLevelTier, AdventureRun
from common.constants import DIFFICULTY_EASY, DIFFICULTY_HARD, DIFFICULTY_MEDIUM

from .access_helpers import (
    _completion_payload,
    _level_commands,
)

if TYPE_CHECKING:
    from progress.models import AdventureLevelCompletion, AdventureLevelTierCompletion


@dataclass(frozen=True)
class AdventureAccessContext:
    """User-specific state for an ordered group of Adventures.

    Adventures are a linear progression within a chapter. Completion rows are
    batch-loaded once so building the overview never issues a query per level.
    """

    completion_by_adventure_id: dict[int, AdventureLevelCompletion] = field(default_factory=dict)
    passed_adventure_ids: set[int] = field(default_factory=set)
    locked_adventure_ids: set[int] = field(default_factory=set)
    lock_reasons: dict[int, str] = field(default_factory=dict)


def _build_adventure_access(*, player, adventures: list[AdventureLevel]) -> AdventureAccessContext:
    if not adventures:
        return AdventureAccessContext()

    completion_by_adventure_id: dict[int, AdventureLevelCompletion] = {}
    passed_adventure_ids: set[int] = set()
    if player is not None:
        from progress.models import AdventureLevelCompletion

        adventure_ids = [adventure.id for adventure in adventures]
        passed_adventure_ids = set(
            AdventureRun.objects.filter(
                player=player,
                level_id__in=adventure_ids,
                passed_at__isnull=False,
            ).values_list("level_id", flat=True)
        )
        completion_by_adventure_id = {
            completion.adventure_level_id: completion
            for completion in AdventureLevelCompletion.objects.filter(
                player=player,
                adventure_level_id__in=adventure_ids,
            ).only("adventure_level_id", "stars", "counted_action_total", "completed_at")
        }
        passed_adventure_ids |= completion_by_adventure_id.keys()

    return AdventureAccessContext(
        completion_by_adventure_id=completion_by_adventure_id,
        passed_adventure_ids=passed_adventure_ids,
    )


def adventure_locked(*, player, adventure: AdventureLevel) -> tuple[bool, str]:
    """Return whether the immediately preceding adventure still blocks launch."""
    adventures = list(
        AdventureLevel.objects.filter(chapter_id=adventure.chapter_id, is_published=True).order_by(
            "sort_order", "id"
        )
    )
    access = _build_adventure_access(player=player, adventures=adventures)
    return (
        adventure.id in access.locked_adventure_ids,
        access.lock_reasons.get(adventure.id, ""),
    )


def level_locked(*, player, level: AdventureLevel) -> tuple[bool, str]:
    """Return whether this adventure level is blocked by the previous level in the chapter."""
    return adventure_locked(player=player, adventure=level)


def adventure_summary_payload(
    *,
    player,
    adventure: AdventureLevel,
    access: AdventureAccessContext | None = None,
) -> dict:
    if access is None:
        chapter_adventures = list(
            AdventureLevel.objects.filter(
                chapter_id=adventure.chapter_id, is_published=True
            ).order_by("sort_order", "id")
        )
        access = _build_adventure_access(player=player, adventures=chapter_adventures)

    completion = access.completion_by_adventure_id.get(adventure.id)
    is_passed = adventure.id in access.passed_adventure_ids
    tiers = list(adventure.tiers.filter(is_published=True)) if adventure.id else []
    tier_access = _build_adventure_tier_access(player=player, tiers=tiers)

    return {
        "item_type": "adventure",
        "id": adventure.id,
        "slug": adventure.slug,
        "title": adventure.title,
        "description": adventure.description,
        "command": ", ".join(_level_commands(adventure)),
        "is_passed": is_passed,
        "locked": adventure.id in access.locked_adventure_ids,
        "lock_reason": access.lock_reasons.get(adventure.id, ""),
        "completion": _completion_payload(completion),
        "tiers": [
            adventure_level_tier_payload(tier=tier, access=tier_access)
            for tier in _ordered_adventure_tiers(tiers)
        ],
    }


# ---------------------------------------------------------------------------
# Per-node difficulty tiers (AdventureLevelTier)
#
# Mirrors the ChallengeLevel -> ChallengeTrial access pattern in
# challenge_access.py: Easy unlocks with the level itself, Medium unlocks once
# Easy has a completion row, Hard unlocks once Medium does. "Complete" means
# every wave in the tier is cleared - tracked via AdventureLevelTierCompletion,
# written once (mirrors ChallengeTrialCompletion), not re-derived per request.
# ---------------------------------------------------------------------------

_TIER_DIFFICULTY_ORDER = {DIFFICULTY_EASY: 0, DIFFICULTY_MEDIUM: 1, DIFFICULTY_HARD: 2}


def _ordered_adventure_tiers(tiers: list[AdventureLevelTier]) -> list[AdventureLevelTier]:
    return sorted(tiers, key=lambda tier: _TIER_DIFFICULTY_ORDER.get(tier.difficulty, 99))


@dataclass(frozen=True)
class AdventureTierAccessContext:
    """Batch-loaded per-tier facts: completion rows, each tier's wave (holding
    required_successful_attempts), and the player's current run (holding
    successful_clears) - so building a level's tier payloads costs a fixed
    handful of queries.

    A tier is a single repeatable exercise, not a sequence of distinct waves:
    "progress" is successful_clears vs required_successful_attempts on that
    one wave, not a count of AdventureLevelTierWave rows (there is always
    exactly one per tier)."""

    completions: dict[int, object] = field(default_factory=dict)
    required_attempts: dict[int, int] = field(default_factory=dict)
    successful_clears: dict[int, int] = field(default_factory=dict)


def _build_adventure_tier_access(
    *, player, tiers: list[AdventureLevelTier]
) -> AdventureTierAccessContext:
    if not tiers:
        return AdventureTierAccessContext()

    from adventures.models import AdventureLevelTierWave

    tier_ids = [tier.id for tier in tiers]
    required_attempts: dict[int, int] = dict(
        AdventureLevelTierWave.objects.filter(
            tier_id__in=tier_ids, is_published=True
        ).values_list("tier_id", "required_successful_attempts")
    )

    completions: dict[int, object] = {}
    successful_clears: dict[int, int] = {}
    if player is not None:
        from adventures.models import AdventureLevelTierProgress
        from progress.models import AdventureLevelTierCompletion

        completions = {
            completion.tier_id: completion
            for completion in AdventureLevelTierCompletion.objects.filter(
                player=player, tier_id__in=tier_ids
            )
        }
        # AdventureLevelTierProgress is the per-(player, tier) rollup counter
        # that persists across attempts - each AdventureLevelTierRun ends on
        # its own, so a run field can't hold this without resetting every
        # attempt (see AdventureLevelTierProgress docstring).
        successful_clears = dict(
            AdventureLevelTierProgress.objects.filter(
                player=player, tier_id__in=tier_ids
            ).values_list("tier_id", "successful_clears")
        )

    return AdventureTierAccessContext(
        completions=completions,
        required_attempts=required_attempts,
        successful_clears=successful_clears,
    )


def _adventure_tier_unlocked(
    *, tier: AdventureLevelTier, access: AdventureTierAccessContext
) -> bool:
    if tier.difficulty == DIFFICULTY_EASY:
        return True
    previous_difficulty = DIFFICULTY_EASY if tier.difficulty == DIFFICULTY_MEDIUM else DIFFICULTY_MEDIUM
    previous_tier = next(
        (
            candidate
            for candidate in tier.adventure_level.tiers.all()
            if candidate.difficulty == previous_difficulty and candidate.is_published
        ),
        None,
    )
    return bool(previous_tier and previous_tier.id in access.completions)


def adventure_level_tier_payload(
    *, tier: AdventureLevelTier, access: AdventureTierAccessContext
) -> dict:
    completion = access.completions.get(tier.id)
    total = access.required_attempts.get(tier.id, 0)
    completed = access.successful_clears.get(tier.id, 0)
    return {
        "id": tier.id,
        "difficulty": tier.difficulty,
        "locked": not _adventure_tier_unlocked(tier=tier, access=access),
        "wave_progress": {"completed": completed, "total": total},
        "completion": _completion_payload(completion),
    }


def _adventure_passed(*, player, chapter_id: int) -> bool:
    required_level_ids = set(
        AdventureLevel.objects.filter(
            chapter_id=chapter_id,
            is_published=True,
            is_required=True,
        ).values_list("id", flat=True)
    )
    if not required_level_ids:
        return True

    # Tier-based levels (AdventureLevelTier) have zero AdventureWave rows by
    # design (see AdventureLevelTier docstring) and so can never produce an
    # AdventureLevelCompletion/passed AdventureRun - the wave-based flow below
    # this branch. A chapter is either entirely tier-based or entirely
    # wave-based; checking for any tier row scopes this to tier content
    # without hardcoding a story slug, and leaves wave-based chapters
    # (arcane-spire and everything else) on the unmodified check below.
    if AdventureLevelTier.objects.filter(adventure_level_id__in=required_level_ids).exists():
        return True

    from progress.models import AdventureLevelCompletion

    completed_level_ids = set(
        AdventureLevelCompletion.objects.filter(
            player=player,
            adventure_level_id__in=required_level_ids,
        ).values_list("adventure_level_id", flat=True)
    )
    if required_level_ids <= completed_level_ids:
        return True
    passed_ids = set(
        AdventureRun.objects.filter(
            player=player, level_id__in=required_level_ids, passed_at__isnull=False
        ).values_list("level_id", flat=True)
    )
    return required_level_ids <= passed_ids
