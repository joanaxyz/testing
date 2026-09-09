"""Curriculum selector public API.

Implementation lives in named modules so this package initializer stays an
import-compatible export surface instead of another service/selectors god file.
"""

from .access import (
    AdventureAccessContext,
    ChallengeAccessContext,
    adventure_locked,
    adventure_summary_payload,
    challenge_level_access_payload,
    challenge_levels_access_payload,
    challenge_summary_payload,
    challenge_trial_access_payload,
    get_command_form,
    level_locked,
)
from .book import book_command_payload, chapter_book, lesson_summary_payload
from .challenge_queries import challenge_queryset
from .command_skills import learned_command_skills
from .content import chapter_content_overview
from .orientation import (
    mark_orientation_lesson_complete,
    orientation_lesson_detail,
    orientation_lessons_for_chapter,
)
from .progress_counts import chapter_completion_count_map, chapter_completion_denominator_map
from .stories import (
    DEFAULT_CHAPTER_HEIGHT,
    chapter_band_offset,
    chapter_completed,
    chapter_locked,
    published_chapters,
    published_stories,
    stories_completed_map,
    story_completed,
    story_locked,
)

__all__ = [
    "DEFAULT_CHAPTER_HEIGHT",
    "published_stories",
    "published_chapters",
    "chapter_completed",
    "chapter_locked",
    "story_locked",
    "story_completed",
    "stories_completed_map",
    "chapter_band_offset",
    "chapter_completion_count_map",
    "chapter_completion_denominator_map",
    "chapter_content_overview",
    "learned_command_skills",
    "chapter_book",
    "book_command_payload",
    "lesson_summary_payload",
    "challenge_queryset",
    "ChallengeAccessContext",
    "AdventureAccessContext",
    "adventure_locked",
    "level_locked",
    "adventure_summary_payload",
    "challenge_summary_payload",
    "challenge_levels_access_payload",
    "challenge_level_access_payload",
    "challenge_trial_access_payload",
    "get_command_form",
    "orientation_lessons_for_chapter",
    "orientation_lesson_detail",
    "mark_orientation_lesson_complete",
]
