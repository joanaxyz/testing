from django.db import models


class StreakRecord(models.Model):
    player = models.OneToOneField("players.Player", on_delete=models.CASCADE)
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_completed_on = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(longest_streak__gte=models.F("current_streak")),
                name="streak_longest_gte_current",
            ),
        ]

    def __str__(self) -> str:
        return f"Streak({self.player_id}: {self.current_streak})"


class Wallet(models.Model):
    player = models.OneToOneField("players.Player", on_delete=models.CASCADE, related_name="wallet")
    balance = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Wallet({self.player_id}: {self.balance})"


class CoinTransaction(models.Model):
    """GitCoin ledger entry. ``award_key`` makes every grant idempotent: a
    reward source (first clear of a level, passing an adventure) can be
    retried safely and never pays out twice."""

    player = models.ForeignKey(
        "players.Player", on_delete=models.CASCADE, related_name="coin_transactions"
    )
    amount = models.IntegerField()
    reason = models.CharField(max_length=64)
    award_key = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["player", "award_key"], name="unique_award_per_player"),
            models.CheckConstraint(
                condition=~models.Q(amount=0),
                name="coin_transaction_amount_nonzero",
            ),
        ]

    def __str__(self) -> str:
        return f"CoinTransaction({self.player_id}: {self.amount} {self.reason})"


class PlayerCompletion(models.Model):
    """Shared shape for "player finished this thing" records: who, and when."""

    player = models.ForeignKey("players.Player", on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class ScoredPlayerCompletion(PlayerCompletion):
    """A completion that also carries the run's score (stars, counted actions)."""

    stars = models.PositiveSmallIntegerField(default=0)
    counted_action_total = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True


class AdventureLevelCompletion(ScoredPlayerCompletion):
    adventure_level = models.ForeignKey(
        "adventures.AdventureLevel",
        on_delete=models.CASCADE,
        related_name="completions",
    )
    adventure_run = models.OneToOneField(
        "adventures.AdventureRun",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="completion",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["player", "adventure_level"],
                name="unique_adventure_level_completion",
            ),
            models.CheckConstraint(
                condition=models.Q(stars__lte=3),
                name="adventure_completion_stars_lte_3",
            ),
        ]

    @property
    def level(self):
        return self.adventure_level


class ChallengeTrialCompletion(ScoredPlayerCompletion):
    challenge_trial = models.ForeignKey(
        "challenges.ChallengeTrial",
        on_delete=models.CASCADE,
        related_name="completions",
    )
    challenge_run = models.OneToOneField(
        "challenges.ChallengeRun",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="completion",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["player", "challenge_trial"],
                name="unique_challenge_trial_completion",
            ),
            models.CheckConstraint(
                condition=models.Q(stars__lte=3),
                name="challenge_completion_stars_lte_3",
            ),
        ]

    @property
    def level(self):
        return self.challenge_trial


class ChallengeLevelCompletion(PlayerCompletion):
    challenge_level = models.ForeignKey(
        "challenges.ChallengeLevel",
        on_delete=models.CASCADE,
        related_name="completions",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["player", "challenge_level"],
                name="unique_challenge_level_completion",
            )
        ]


class AdventureLevelTierCompletion(ScoredPlayerCompletion):
    """Written once all of a tier's waves are cleared - mirrors
    ChallengeTrialCompletion for the adventures/AdventureLevelTier chain."""

    tier = models.ForeignKey(
        "adventures.AdventureLevelTier",
        on_delete=models.CASCADE,
        related_name="completions",
    )
    tier_run = models.OneToOneField(
        "adventures.AdventureLevelTierRun",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="completion",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["player", "tier"],
                name="unique_adv_level_tier_completion",
            ),
            models.CheckConstraint(
                condition=models.Q(stars__lte=3),
                name="adv_level_tier_completion_stars_lte_3",
            ),
        ]

    @property
    def level(self):
        return self.tier
