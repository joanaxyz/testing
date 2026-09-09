from django.core.management import call_command
from rest_framework.test import APIClient

from adventures.models import AdventureLevel
from curriculum.engine_capabilities import ENGINE_SUPPORTED_REFERENCE_FORMS
from curriculum.models import Chapter, ChapterLesson, CommandForm, Story
from curriculum.seed_data.chapters import (
    ARCANE_SPIRE_CHAPTERS,
    FROSTBOUND_CITADEL_CHAPTERS,
    REFERENCE_CHAPTERS,
    SKYLINE_NEXUS_CHAPTERS,
)
from curriculum.seed_data.command_catalog import COMMAND_CATALOG
from curriculum.seed_data.source.adventure_level_specs.v3_advanced_workflows import (
    LEVELS as ADVANCED_STORY_LEVELS,
)
from curriculum.seed_data.stories import STORIES
from curriculum.selectors import chapter_locked, story_locked
from players.services import get_or_create_player
from shop.models import Entitlement

EXPECTED_ARCANE_CHAPTERS = (
    (
        "creating-inspecting-repositories",
        1,
        "Repository Foundations",
        "Start from empty or remote projects, then read branch and commit-history signals before changing anything.",
        "chapter-01-foundation-hall",
    ),
    (
        "tracking-changes-snapshots",
        2,
        "Tracking Changes and Snapshots",
        "Use diff, staging, commits, restore, and tracked-file removal to create intentional snapshots.",
        "chapter-02-scriptorium-library",
    ),
    (
        "branching-switching",
        3,
        "Branch Navigation",
        "Create branch pointers, move HEAD safely, branch from old commits, and clean up merged branches.",
        "chapter-03-branching-gallery",
    ),
    (
        "merging-conflicts",
        4,
        "Merging and Conflict Resolution",
        "Integrate branch histories, recognize fast-forward versus merge commits, and finish conflicted merges.",
        "chapter-04-convergence-chamber",
    ),
    (
        "undoing-recovery",
        5,
        "Undoing and Recovery",
        "Choose between restore, amend, reset, revert, and reflog-based recovery based on history safety.",
        "chapter-05-recovery-vault",
    ),
    (
        "temporary-work-patches",
        6,
        "Temporary Work and Patch Movement",
        "Shelve unfinished work and transplant selected commits without dragging an entire branch history.",
        "chapter-06-stash-workshop",
    ),
    (
        "remotes-collaboration",
        7,
        "Remotes and Collaboration",
        "Read remote relationships, update remote-tracking refs, pull, publish, and handle collaboration history.",
        "chapter-07-remote-relay",
    ),
)


def test_canonical_story_specs_have_no_deprecated_registry_names():
    assert [(story["slug"], story["title"]) for story in STORIES] == [
        ("arcane-spire", "The Arcane Spire"),
        ("frostbound-citadel", "Frostbound Citadel"),
        ("neon-backstreets", "Neon Backstreets"),
        ("git-it-legacy", "The Runebound Turret"),
    ]
    serialized = repr(STORIES).lower()
    deprecated_slugs = ("obsidian" + "-forge", "void" + "-athenaeum")
    assert all(slug not in serialized for slug in deprecated_slugs)
    assert "neon-metropolis" not in serialized


def test_existing_arcane_chapter_specs_are_preserved_exactly():
    actual = tuple(
        (
            row["slug"],
            row["number"],
            row["title"],
            row["description"],
            row["battle_stage"]["parallax"],
        )
        for row in ARCANE_SPIRE_CHAPTERS[:7]
    )
    assert actual == EXPECTED_ARCANE_CHAPTERS


def test_additive_story_scope_is_large_and_detailed():
    assert len(ARCANE_SPIRE_CHAPTERS) == 8
    assert len(FROSTBOUND_CITADEL_CHAPTERS) == 9
    assert len(SKYLINE_NEXUS_CHAPTERS) == 12
    assert [row["number"] for row in ARCANE_SPIRE_CHAPTERS] == list(range(1, 9))
    assert [row["number"] for row in FROSTBOUND_CITADEL_CHAPTERS] == list(range(1, 10))
    assert [row["number"] for row in SKYLINE_NEXUS_CHAPTERS] == list(range(1, 13))
    for chapter in REFERENCE_CHAPTERS:
        assert len(chapter["description"]) >= 120
        assert chapter["battle_stage"]["parallax"].startswith(("frost-", "skyline-"))


def test_advanced_stories_add_deep_four_variant_incidents():
    assert len(ADVANCED_STORY_LEVELS) == 63
    assert sum(len(level["variants"]) for level in ADVANCED_STORY_LEVELS) == 252

    levels_per_chapter = {}
    for level in ADVANCED_STORY_LEVELS:
        levels_per_chapter[level["adventure"]] = levels_per_chapter.get(level["adventure"], 0) + 1
        assert len(level["scenario_context"]["story"]) >= 100
        assert len(level["scenario_context"]["task"]) >= 20
        assert len(level["objective_checks"]) >= 1
        assert len(level["variants"]) == 4
        assert min(len(variant["solution_commands_template"]) for variant in level["variants"]) >= 7
        assert level["level_type"] in {"applied_scenario", "mastery_incident"}

    assert len(levels_per_chapter) == 21
    assert set(levels_per_chapter.values()) == {3}


def test_command_catalog_expands_beyond_the_original_command_families():
    by_slug = {skill["slug"]: skill for skill in COMMAND_CATALOG}
    expected = {
        "git-bisect",
        "git-worktree",
        "git-sparse-checkout",
        "git-submodule",
        "git-rerere",
        "git-fsck",
        "git-cat-file",
        "git-symbolic-ref",
        "git-describe",
        "git-shortlog",
    }
    assert expected <= set(by_slug)
    # Every advertised command must be simulable by the engine; the old
    # patch-transport/maintenance/plumbing-write families were trimmed.
    unsimulable = {
        "git-am",
        "git-apply",
        "git-archive",
        "git-bundle",
        "git-clean",
        "git-commit-tree",
        "git-difftool",
        "git-fast-export",
        "git-fast-import",
        "git-format-patch",
        "git-gc",
        "git-hash-object",
        "git-maintenance",
        "git-notes",
        "git-pack-objects",
        "git-prune",
        "git-repack",
        "git-replace",
        "git-request-pull",
        "git-update-ref",
        "git-verify-pack",
        "git-write-tree",
    }
    assert not (unsimulable & set(by_slug))
    advanced_forms = [
        form
        for skill in COMMAND_CATALOG
        for form in skill.get("usages", [])
        if form.get("module", skill["module"]).startswith(("frost-", "skyline-"))
    ]
    assert len(advanced_forms) >= 140
    assert all(len(form["label"]) >= 8 for form in advanced_forms)


def test_seed_creates_story_books_and_playable_fieldwork(db):
    call_command("seed_curriculum")

    assert list(Story.objects.values_list("slug", flat=True)) == [
        "git-it-legacy",
        "arcane-spire",
        "frostbound-citadel",
        "neon-backstreets",
    ]
    assert list(
        Chapter.objects.filter(story__slug="frostbound-citadel")
        .order_by("number")
        .values_list("number", flat=True)
    ) == list(range(1, 10))
    assert list(
        Chapter.objects.filter(story__slug="neon-backstreets")
        .order_by("number")
        .values_list("number", flat=True)
    ) == list(range(1, 13))

    for spec in REFERENCE_CHAPTERS:
        chapter = Chapter.objects.get(slug=spec["slug"])
        assert chapter.is_published is True
        assert chapter.is_playable is True
        assert ChapterLesson.objects.filter(chapter=chapter, is_published=True).count() >= 3
        assert AdventureLevel.objects.filter(chapter=chapter, is_published=True).count() >= 3
        levels = AdventureLevel.objects.filter(chapter=chapter, is_published=True)
        assert CommandForm.objects.filter(adventure_levels__in=levels, is_published=True).exists()


def test_story_api_exposes_difficulty_ownership_and_prerequisite(db, django_user_model):
    call_command("seed_curriculum")
    user = django_user_model.objects.create_user(
        username="three-story-reader",
        email="three-story-reader@example.com",
        password="pass12345",
    )
    player = get_or_create_player(user)
    Entitlement.objects.create(player=player, kind="story", slug="frostbound-citadel")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/stories/")

    assert response.status_code == 200
    rows = {row["slug"]: row for row in response.json()}
    assert rows["arcane-spire"]["owned"] is False
    assert rows["git-it-legacy"]["owned"] is True
    assert rows["arcane-spire"]["difficulty"] == "beginner"
    assert rows["frostbound-citadel"]["owned"] is True
    assert rows["frostbound-citadel"]["locked"] is True
    assert rows["frostbound-citadel"]["prerequisite_story"] == {
        "slug": "arcane-spire",
        "title": "The Arcane Spire",
        "completed": False,
    }
    assert rows["neon-backstreets"]["difficulty"] == "advanced"
    assert rows["neon-backstreets"]["prerequisite_story"]["slug"] == "frostbound-citadel"


def test_advanced_chapters_respect_story_access(db, django_user_model):
    call_command("seed_curriculum")
    user = django_user_model.objects.create_user(
        username="advanced-reader",
        email="advanced-reader@example.com",
        password="pass12345",
    )
    player = get_or_create_player(user)
    story = Story.objects.get(slug="frostbound-citadel")
    chapter = story.chapters.order_by("number").last()

    locked, _ = story_locked(player=player, story=story)
    assert locked is True

    Entitlement.objects.create(player=player, kind="story", slug=story.slug)
    # The story remains progression-locked until every Arcane Spire command
    # form is mastered.
    locked, reason = story_locked(player=player, story=story)
    assert locked is True
    assert "Master every command in The Arcane Spire" in reason

    # Chapter access remains governed by the story prerequisite before the
    # player can enter the new playable fieldwork.
    chapter_locked_state, chapter_reason = chapter_locked(player=player, chapter=chapter)
    assert chapter_locked_state is True
    assert chapter_reason == reason


def test_engine_supported_advanced_diagnostics_are_seeded_as_playable(db):
    call_command("seed_curriculum")

    seeded = {
        f"{skill_slug}/{form_slug}"
        for skill_slug, form_slug in CommandForm.objects.filter(
            is_playable=True,
            chapter__story__slug__in=["frostbound-citadel", "neon-backstreets"],
        ).values_list("command_skill__slug", "slug")
    }

    assert ENGINE_SUPPORTED_REFERENCE_FORMS <= seeded
