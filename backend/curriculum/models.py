from django.db import models

MANAGEMENT_SOURCE_SEED = "seed"
MANAGEMENT_SOURCE_ADMIN = "admin"
MANAGEMENT_SOURCE_RUNTIME = "runtime"
STORY_MANAGEMENT_SOURCE_CHOICES = (
    (MANAGEMENT_SOURCE_SEED, "Seed"),
    (MANAGEMENT_SOURCE_ADMIN, "Admin"),
)
CHAPTER_MANAGEMENT_SOURCE_CHOICES = (
    *STORY_MANAGEMENT_SOURCE_CHOICES,
    (MANAGEMENT_SOURCE_RUNTIME, "Runtime"),
)


class Story(models.Model):
    """A purchasable curriculum world containing an ordered chapter sequence."""

    DIFFICULTY_BEGINNER = "beginner"
    DIFFICULTY_INTERMEDIATE = "intermediate"
    DIFFICULTY_ADVANCED = "advanced"
    DIFFICULTY_CHOICES = (
        (DIFFICULTY_BEGINNER, "Beginner"),
        (DIFFICULTY_INTERMEDIATE, "Intermediate"),
        (DIFFICULTY_ADVANCED, "Advanced"),
    )

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=160)
    summary = models.TextField(blank=True)
    price = models.PositiveIntegerField(default=0)
    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    world_slug = models.SlugField(max_length=64, default="arcane-spire")
    difficulty = models.CharField(
        max_length=16,
        choices=DIFFICULTY_CHOICES,
        default=DIFFICULTY_BEGINNER,
    )
    prerequisite_story = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="unlocks_stories",
        on_delete=models.PROTECT,
    )
    management_source = models.CharField(
        max_length=8,
        choices=STORY_MANAGEMENT_SOURCE_CHOICES,
        default=MANAGEMENT_SOURCE_SEED,
    )

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.title


class Chapter(models.Model):
    story = models.ForeignKey(
        Story,
        null=True,
        blank=True,
        related_name="chapters",
        on_delete=models.PROTECT,
    )
    slug = models.SlugField(unique=True)
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=160)
    description = models.TextField()
    is_published = models.BooleanField(default=True)
    # True for a reading-only introductory chapter (step-through orientation
    # lessons, no adventures/challenges). Orthogonal to is_playable, which
    # tracks simulator-verification status for a chapter's playable content.
    is_orientation = models.BooleanField(default=False)
    # A reference chapter has the same detailed book content as a playable
    # chapter but does not claim to have simulator levels before its command
    # families are implemented and verified end-to-end.
    is_playable = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    # Authored battle-stage dressing rendered behind the actors during this
    # chapter's battles. Shape: {"parallax": "<asset-slug>"|null,
    # "landing": {"x", "y", "width", "height"}|null}. Coordinates are
    # normalized (0..1) so they render at any stage size.
    battle_stage = models.JSONField(default=dict, blank=True)
    management_source = models.CharField(
        max_length=8,
        choices=CHAPTER_MANAGEMENT_SOURCE_CHOICES,
        default=MANAGEMENT_SOURCE_SEED,
    )

    class Meta:
        ordering = ["sort_order", "number"]
        indexes = [
            models.Index(fields=["story", "sort_order"], name="chapter_story_sort_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["story", "number"], name="unique_chapter_story_number"),
        ]

    def __str__(self) -> str:
        return f"{self.story.title if self.story_id else 'Story'} · Chapter {self.number}: {self.title}"


class ChapterLesson(models.Model):
    """A reading lesson attached directly to a chapter.

    Lessons are pure reference content: no runs, no attempts, and no locks.
    The chapter book renders them in ``sort_order``.
    """

    chapter = models.ForeignKey(Chapter, related_name="lessons", on_delete=models.CASCADE)
    slug = models.SlugField()
    title = models.CharField(max_length=160)
    summary = models.TextField(blank=True)
    # list[BookPage] - the same page/block schema the Chapter Book renders.
    pages = models.JSONField(default=list, blank=True)
    is_published = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    source_content_definition = models.ForeignKey(
        "authoring.ContentDefinition",
        null=True,
        blank=True,
        related_name="runtime_lessons",
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ["chapter__sort_order", "sort_order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["chapter", "slug"], name="unique_lesson_chapter_slug"),
        ]

    def __str__(self) -> str:
        return self.title


class LibraryEntry(models.Model):
    """Authored reference content for one command, keyed by its canonical
    library key (``library_key_for_command``). The Chapter Book resolves each
    registered CommandSkill to its entry here; commands without an entry fall
    back to a synthesized summary page."""

    command_key = models.CharField(max_length=80, unique=True)
    title = models.CharField(max_length=160, blank=True)
    summary = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    # list[BookPage] - the same page/block schema the Chapter Book renders.
    pages = models.JSONField(default=list, blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["command_key"]
        verbose_name_plural = "library entries"

    def __str__(self) -> str:
        return self.command_key


class CommandSkill(models.Model):
    """A git command as a global library/spellbook entry (e.g. "git add").

    Chapter-agnostic: each of its CommandForms carries its own chapter, so a single
    command can introduce basic moves in one chapter and advanced moves in a later
    one without duplicating the library entry. The skill owns the reference content
    (title, summary, mental model); the chapters it touches are derived from its
    forms.
    """

    slug = models.SlugField(unique=True)
    base_command = models.CharField(max_length=80)
    title = models.CharField(max_length=160)
    summary = models.TextField(blank=True)
    mental_model = models.JSONField(default=dict, blank=True)
    command_preview = models.JSONField(default=dict, blank=True)
    is_published = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    source_content_definition = models.ForeignKey(
        "authoring.ContentDefinition",
        null=True,
        blank=True,
        related_name="runtime_command_skills",
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ["sort_order", "base_command"]

    def __str__(self) -> str:
        return self.title


class CommandForm(models.Model):
    command_skill = models.ForeignKey(
        CommandSkill, related_name="command_forms", on_delete=models.CASCADE
    )
    # The chapter where this specific move is taught. The skill spans whatever
    # chapters its forms live in (derived), so the library entry is never duplicated.
    chapter = models.ForeignKey(
        Chapter, related_name="command_forms", on_delete=models.CASCADE, null=True
    )
    slug = models.SlugField()
    usage_form = models.CharField(max_length=140)
    label = models.CharField(max_length=180)
    summary = models.TextField(blank=True)
    command_preview = models.JSONField(default=dict, blank=True)
    is_published = models.BooleanField(default=True)
    # Reference-only forms are fully authored for the chapter book but are not
    # offered by playable levels until the deterministic simulator and backend
    # transition verifier support them. This prevents curriculum scope from
    # being silently reduced to today's engine capabilities.
    is_playable = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["command_skill__sort_order", "sort_order", "usage_form"]
        constraints = [
            models.UniqueConstraint(
                fields=["command_skill", "slug"], name="unique_command_form_skill_slug"
            ),
        ]

    def __str__(self) -> str:
        return self.label


class ChapterOrientationLesson(models.Model):
    """An interactive orientation lesson attached directly to a chapter.

    Independent of ChapterLesson/the book system: content is raw HTML plus
    scoped CSS and a step script, rendered by a dedicated step-through
    workspace rather than the static book reader. Used only by
    is_orientation=True chapters.
    """

    chapter = models.ForeignKey(
        Chapter, related_name="orientation_lessons", on_delete=models.CASCADE
    )
    slug = models.SlugField()
    title = models.CharField(max_length=180)
    subtitle = models.CharField(max_length=240, blank=True)
    content_html = models.TextField()
    scoped_css = models.TextField(blank=True)
    interaction_steps = models.JSONField(default=list, blank=True)
    is_published = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["chapter__sort_order", "sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["chapter", "slug"], name="unique_orientation_lesson_chapter_slug"
            ),
        ]

    def __str__(self) -> str:
        return self.title


class ChapterOrientationProgress(models.Model):
    """Per-player progress through one orientation lesson's step script."""

    player = models.ForeignKey(
        "players.Player", on_delete=models.CASCADE, related_name="orientation_progress"
    )
    lesson = models.ForeignKey(
        ChapterOrientationLesson, on_delete=models.CASCADE, related_name="progress_rows"
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    highest_step_seen = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["player", "lesson"], name="unique_orientation_progress_player_lesson"
            ),
        ]

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    def __str__(self) -> str:
        return f"ChapterOrientationProgress(player={self.player_id}, lesson={self.lesson_id})"
