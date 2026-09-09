from adventures.models import AdventureLevelTierRun
from common.services.lru import LRUCommandHistoryCache


class TierCommandHistoryCache(LRUCommandHistoryCache):
    """Mirrors challenges.services.history.CommandHistoryCache for the
    AdventureLevelTierRun surface. LRUCommandHistoryCache gives each
    subclass its own isolated cache store, so this never collides with the
    challenge or adventure-wave caches on overlapping integer ids/counts."""

    @staticmethod
    def key_for(*, run: AdventureLevelTierRun, attempt_count: int) -> tuple[object, ...]:
        return (
            run.id,
            run.started_at,
            run.selected_variant_id,
            attempt_count,
        )

    def history_for(self, *, run: AdventureLevelTierRun) -> list[str]:
        from practice.models import CommandStep

        if run.total_attempts <= 0:
            return []
        key = self.key_for(run=run, attempt_count=run.total_attempts)
        cached = self._cached(key)
        if cached is not None:
            return cached
        history = list(
            CommandStep.objects.filter(adventure_tier_run=run, was_processable=True)
            .order_by("id")
            .values_list("normalized_command", flat=True)
        )
        self._remember(key, history)
        return history

    def remember_after_append(
        self,
        *,
        run: AdventureLevelTierRun,
        previous_history: list[str],
        normalized_command: str,
    ) -> None:
        self._remember(
            self.key_for(run=run, attempt_count=run.total_attempts),
            [*previous_history, normalized_command],
        )
