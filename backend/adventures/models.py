from django.db import models
from django.db.models import Q

from common.constants import (
    DIFFICULTY_EASY,
    DIFFICULTY_HARD,
    DIFFICULTY_MEDIUM,
    SESSION_STATUS_ABANDONED,
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_FAILED,
    SESSION_STATUS_STARTED,
)
from common.models import VariantBase


class AdventureLevel(models.Model):
    """A playable adventure level attached directly to a chapter.

    The content tree is:

        Chapter -> AdventureLevel -> AdventureWave -> AdventureWaveVariant
    """

    chapter = models.ForeignKey(
        "curriculum.Chapter",
        related_name="adventure_levels",
        on_delete=models.CASCADE,
    )
    slug = models.SlugField()
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    command_forms = models.ManyToManyField(
        "curriculum.CommandForm",
        related_name="adventure_levels",
        blank=True,
    )
    is_required = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    # GitCoins paid (once, via the idempotent wallet ledger) on first completion.
    reward_coins = models.PositiveIntegerField(default=0)
    source_content_definition = models.ForeignKey(
        "authoring.ContentDefinition",
        null=True,
        blank=True,
        related_name="runtime_adventure_levels",
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ["chapter__sort_order", "sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["chapter", "slug"], name="unique_adventure_level_chapter_slug"
            ),
        ]
        indexes = [
            models.Index(fields=["chapter", "sort_order"], name="adv_level_chapter_sort_idx"),
        ]

    def __str__(self) -> str:
        return self.title


class AdventureWave(models.Model):
    """The playable Git problem inside an adventure level."""

    level = models.ForeignKey(AdventureLevel, related_name="waves", on_delete=models.CASCADE)
    slug = models.SlugField()
    title = models.CharField(max_length=180, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    story = models.TextField(blank=True)
    task = models.TextField(blank=True)
    command_forms = models.ManyToManyField(
        "curriculum.CommandForm",
        related_name="adventure_waves",
        blank=True,
    )
    min_counted_commands = models.PositiveIntegerField(default=1)
    max_counted_commands = models.PositiveIntegerField(default=4)
    objective_checks = models.JSONField(default=list, blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["level_id", "sort_order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["level", "slug"], name="unique_adventure_wave_slug"),
            models.CheckConstraint(
                condition=(
                    Q(min_counted_commands__gte=0)
                    & Q(max_counted_commands__gte=models.F("min_counted_commands"))
                ),
                name="adventure_wave_valid_command_budget",
            ),
        ]
        indexes = [
            models.Index(fields=["level", "sort_order"], name="adv_wave_slot_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.level_id}:wave:{self.slug}"

    @property
    def chapter(self):
        return self.level.chapter


class AdventureWaveVariant(VariantBase):
    wave = models.ForeignKey(AdventureWave, related_name="variants", on_delete=models.CASCADE)

    class Meta:
        ordering = ["wave_id", "semantic_key", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["wave", "slug"], name="unique_adventure_wave_variant_slug"
            ),
        ]

    def __str__(self) -> str:
        return f"adventure-wave:{self.wave_id}:{self.slug}"


class AdventureRun(models.Model):
    """One playable adventure level run.

    The run walks the level's waves in order: each wave selects its own variant,
    and the run completes only when the last wave is cleared.
    """

    class Status(models.TextChoices):
        STARTED = SESSION_STATUS_STARTED, "Started"
        COMPLETED = SESSION_STATUS_COMPLETED, "Completed"
        FAILED = SESSION_STATUS_FAILED, "Failed"
        ABANDONED = SESSION_STATUS_ABANDONED, "Abandoned"

    player = models.ForeignKey(
        "players.Player", on_delete=models.CASCADE, related_name="adventure_runs"
    )
    level = models.ForeignKey(
        AdventureLevel,
        related_name="runs",
        on_delete=models.CASCADE,
    )
    current_wave = models.ForeignKey(
        AdventureWave,
        null=True,
        blank=True,
        related_name="current_runs",
        on_delete=models.PROTECT,
    )
    selected_variant = models.ForeignKey(
        AdventureWaveVariant,
        related_name="runs",
        on_delete=models.PROTECT,
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=SESSION_STATUS_STARTED)
    is_replay = models.BooleanField(default=False)
    stars = models.PositiveSmallIntegerField(default=0)
    library_opened = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    passed_at = models.DateTimeField(null=True, blank=True)
    command_count = models.PositiveIntegerField(default=0)
    counted_command_count = models.PositiveIntegerField(default=0)
    repository_state = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["player", "level", "status"], name="advrun_plyr_level_status_idx"),
            models.Index(fields=["player", "status"], name="advrun_plyr_status_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["player", "level"],
                condition=Q(status=SESSION_STATUS_STARTED),
                name="unique_active_adventure_run",
            ),
            models.CheckConstraint(
                condition=Q(stars__lte=3),
                name="adventure_run_stars_lte_3",
            ),
        ]

    @property
    def chapter(self):
        return self.level.chapter

    @property
    def story(self):
        return self.level.chapter.story

    def __str__(self) -> str:
        return f"AdventureRun({self.id}, level={self.level_id}, {self.status})"


class AdventureRunWave(models.Model):
    """Per-wave progress inside one level run."""

    class Status(models.TextChoices):
        STARTED = SESSION_STATUS_STARTED, "Started"
        COMPLETED = SESSION_STATUS_COMPLETED, "Completed"

    run = models.ForeignKey(AdventureRun, related_name="run_waves", on_delete=models.CASCADE)
    wave = models.ForeignKey(AdventureWave, related_name="run_waves", on_delete=models.CASCADE)
    selected_variant = models.ForeignKey(
        AdventureWaveVariant,
        related_name="run_waves",
        on_delete=models.PROTECT,
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=SESSION_STATUS_STARTED)
    stars = models.PositiveSmallIntegerField(default=0)
    counted_command_count = models.PositiveIntegerField(default=0)
    command_count = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["run_id", "wave__sort_order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["run", "wave"], name="unique_adventure_run_wave"),
            models.CheckConstraint(
                condition=Q(stars__lte=3),
                name="adventure_run_wave_stars_lte_3",
            ),
        ]

    def __str__(self) -> str:
        return f"AdventureRunWave(run={self.run_id}, wave={self.wave_id}, {self.status})"


class SkillMastery(models.Model):
    """Per-user mastery for one command form."""

    player = models.ForeignKey(
        "players.Player", on_delete=models.CASCADE, related_name="skill_mastery_states"
    )
    command_form = models.ForeignKey(
        "curriculum.CommandForm",
        related_name="skill_mastery_states",
        on_delete=models.CASCADE,
    )
    learned_at = models.DateTimeField(null=True, blank=True)
    solves = models.PositiveIntegerField(default=0)
    mastered = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["player", "command_form"], name="unique_skill_mastery_player_form"
            ),
        ]

    def __str__(self) -> str:
        return f"SkillMastery(player={self.player_id}, form={self.command_form_id}, solves={self.solves})"


class AdventureLevelTier(models.Model):
    """A difficulty-scoped playable variant of an AdventureLevel.

    Additive, parallel content tree - does not interact with the level's
    existing waves/runs:

        AdventureLevel -> AdventureLevelTier -> AdventureLevelTierWave
                                              -> AdventureLevelTierVariant (per wave)
                        -> AdventureLevelTierRun -> AdventureLevelTierRunWave

    A level either has AdventureWave rows (the existing single-difficulty
    flow) or AdventureLevelTier rows (this flow), never both.
    """

    class Difficulty(models.TextChoices):
        EASY = DIFFICULTY_EASY, "Easy"
        MEDIUM = DIFFICULTY_MEDIUM, "Medium"
        HARD = DIFFICULTY_HARD, "Hard"

    adventure_level = models.ForeignKey(
        AdventureLevel, related_name="tiers", on_delete=models.CASCADE
    )
    difficulty = models.CharField(max_length=12, choices=Difficulty.choices)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["adventure_level_id", "difficulty"]
        constraints = [
            models.UniqueConstraint(
                fields=["adventure_level", "difficulty"],
                name="unique_adv_level_tier_difficulty",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.adventure_level_id}:tier:{self.difficulty}"


class AdventureLevelTierWave(models.Model):
    """The playable Git problem inside one difficulty tier of an adventure
    level. Mirrors AdventureWave, one level deeper (tier, not level, is the
    parent)."""

    tier = models.ForeignKey(AdventureLevelTier, related_name="waves", on_delete=models.CASCADE)
    slug = models.SlugField()
    title = models.CharField(max_length=180, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    story = models.TextField(blank=True)
    task = models.TextField(blank=True)
    command_forms = models.ManyToManyField(
        "curriculum.CommandForm",
        related_name="adventure_level_tier_waves",
        blank=True,
    )
    min_counted_commands = models.PositiveIntegerField(default=1)
    max_counted_commands = models.PositiveIntegerField(default=4)
    objective_checks = models.JSONField(default=list, blank=True)
    # How many successful clears of this wave (drawing a fresh variant each
    # attempt) are required to master the tier. Mirrors the old
    # DifficultyInstance.required_successful_attempts semantics: a tier is a
    # single repeatable exercise, not a sequence of distinct waves.
    required_successful_attempts = models.PositiveIntegerField(default=1)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["tier_id", "sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["tier", "slug"], name="unique_adv_level_tier_wave_slug"
            ),
            models.CheckConstraint(
                condition=(
                    Q(min_counted_commands__gte=0)
                    & Q(max_counted_commands__gte=models.F("min_counted_commands"))
                ),
                name="adv_level_tier_wave_valid_command_budget",
            ),
        ]
        indexes = [
            models.Index(fields=["tier", "sort_order"], name="adv_lvl_tier_wave_slot_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.tier_id}:wave:{self.slug}"

    @property
    def adventure_level(self):
        return self.tier.adventure_level


class AdventureLevelTierWaveVariant(VariantBase):
    wave = models.ForeignKey(
        AdventureLevelTierWave, related_name="variants", on_delete=models.CASCADE
    )

    class Meta:
        ordering = ["wave_id", "semantic_key", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["wave", "slug"], name="unique_adv_level_tier_wave_variant_slug"
            ),
        ]

    def __str__(self) -> str:
        return f"adventure-level-tier-wave:{self.wave_id}:{self.slug}"


class AdventureLevelTierRun(models.Model):
    """One playable attempt at a difficulty tier.

    Mirrors ChallengeRun's lifecycle shape (one row per attempt; a fresh row
    is created for each retry rather than one long-lived row looping
    internally). A tier's progress toward required_successful_attempts is
    NOT tracked here - a run field would reset every attempt - see
    AdventureLevelTierProgress for the per-(player, tier) rollup counter.
    """

    class Status(models.TextChoices):
        STARTED = SESSION_STATUS_STARTED, "Started"
        COMPLETED = SESSION_STATUS_COMPLETED, "Completed"
        FAILED = SESSION_STATUS_FAILED, "Failed"
        ABANDONED = SESSION_STATUS_ABANDONED, "Abandoned"

    player = models.ForeignKey(
        "players.Player", on_delete=models.CASCADE, related_name="adventure_tier_runs"
    )
    tier = models.ForeignKey(AdventureLevelTier, related_name="runs", on_delete=models.PROTECT)
    current_wave = models.ForeignKey(
        AdventureLevelTierWave,
        null=True,
        blank=True,
        related_name="current_runs",
        on_delete=models.PROTECT,
    )
    selected_variant = models.ForeignKey(
        AdventureLevelTierWaveVariant,
        related_name="runs",
        on_delete=models.PROTECT,
    )
    prior_run = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="retry_runs",
        on_delete=models.SET_NULL,
    )
    source_entry_point = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=SESSION_STATUS_STARTED)
    is_replay = models.BooleanField(default=False)
    # True when this run's selected_variant differs from the player's
    # immediately-previous attempt on this tier (mirrors the old app's
    # ScenarioSession.changed_variant, computed once at selection time via
    # TierVariantSelectionService.changed_between() - see start_run). Powers
    # the "Changed variant" context-panel tag; not used by any grading logic.
    changed_variant = models.BooleanField(default=False)
    stars = models.PositiveSmallIntegerField(default=0)
    min_counted_commands = models.PositiveIntegerField(default=1)
    max_counted_commands = models.PositiveIntegerField(default=4)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    passed_at = models.DateTimeField(null=True, blank=True)
    total_attempts = models.PositiveIntegerField(default=0)
    counted_action_total = models.PositiveIntegerField(default=0)
    non_counted_diagnostic_total = models.PositiveIntegerField(default=0)
    retry_index = models.PositiveIntegerField(default=0)
    failure_reason = models.CharField(max_length=160, blank=True)
    repository_state = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["player", "tier", "status"], name="advtier_run_plyr_tier_stat_idx"
            ),
            models.Index(fields=["player", "status"], name="advtier_run_plyr_stat_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["player", "tier"],
                condition=Q(status=SESSION_STATUS_STARTED),
                name="unique_active_adv_level_tier_run",
            ),
            models.CheckConstraint(
                condition=Q(stars__lte=3),
                name="adv_level_tier_run_stars_lte_3",
            ),
            models.CheckConstraint(
                condition=(
                    Q(min_counted_commands__gte=1)
                    & Q(max_counted_commands__gte=models.F("min_counted_commands"))
                ),
                name="adv_level_tier_run_valid_command_budget",
            ),
        ]

    @property
    def adventure_level(self):
        return self.tier.adventure_level

    def __str__(self) -> str:
        return f"AdventureLevelTierRun({self.id}, tier={self.tier_id}, {self.status})"


class AdventureLevelTierRunWave(models.Model):
    """Per-wave progress inside one tier run. Mirrors AdventureRunWave."""

    class Status(models.TextChoices):
        STARTED = SESSION_STATUS_STARTED, "Started"
        COMPLETED = SESSION_STATUS_COMPLETED, "Completed"

    run = models.ForeignKey(
        AdventureLevelTierRun, related_name="run_waves", on_delete=models.CASCADE
    )
    wave = models.ForeignKey(
        AdventureLevelTierWave, related_name="run_waves", on_delete=models.CASCADE
    )
    selected_variant = models.ForeignKey(
        AdventureLevelTierWaveVariant,
        related_name="run_waves",
        on_delete=models.PROTECT,
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=SESSION_STATUS_STARTED)
    stars = models.PositiveSmallIntegerField(default=0)
    counted_command_count = models.PositiveIntegerField(default=0)
    command_count = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["run_id", "wave__sort_order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["run", "wave"], name="unique_adv_level_tier_run_wave"),
            models.CheckConstraint(
                condition=Q(stars__lte=3),
                name="adv_level_tier_run_wave_stars_lte_3",
            ),
        ]

    def __str__(self) -> str:
        return f"AdventureLevelTierRunWave(run={self.run_id}, wave={self.wave_id}, {self.status})"


class AdventureLevelTierProgress(models.Model):
    """Per-(player, tier) rollup of successful clears toward
    AdventureLevelTierWave.required_successful_attempts.

    Each AdventureLevelTierRun is one attempt and ends (completed/failed) on
    its own - a run field can't hold this count since it would reset to zero
    on every new attempt. This row persists across attempts and is the
    source AdventureLevelTierCompletion is written from once
    successful_clears reaches the wave's threshold.
    """

    player = models.ForeignKey(
        "players.Player", on_delete=models.CASCADE, related_name="adventure_tier_progress"
    )
    tier = models.ForeignKey(
        AdventureLevelTier, on_delete=models.CASCADE, related_name="progress_rows"
    )
    successful_clears = models.PositiveIntegerField(default=0)
    # The variant shown on the player's most recent start_run call for this
    # tier, solved or not. AdventureLevelTierRun rows are hard-deleted on
    # discard (see common.runtime.discard_started_run), so an abandoned,
    # never-solved attempt leaves no run row behind - this field is the only
    # way start_run can still know which variant to rotate away from after
    # an exit-without-solving. Set on every start_run call, independent of
    # successful_clears.
    last_shown_variant = models.ForeignKey(
        "AdventureLevelTierWaveVariant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["player", "tier"], name="unique_adv_level_tier_progress_player_tier"
            ),
        ]

    def __str__(self) -> str:
        return f"AdventureLevelTierProgress(player={self.player_id}, tier={self.tier_id}, clears={self.successful_clears})"
