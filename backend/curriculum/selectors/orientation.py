from __future__ import annotations

from django.utils import timezone

from curriculum.models import ChapterOrientationLesson, ChapterOrientationProgress


def orientation_lessons_for_chapter(*, player, chapter_id: int) -> list[ChapterOrientationLesson]:
    """Published orientation lessons for one chapter, in sort order.

    Progress is annotated onto each lesson instance (not returned separately)
    so the serializer can read it without a query per lesson.
    """
    lessons = list(
        ChapterOrientationLesson.objects.filter(chapter_id=chapter_id, is_published=True).order_by(
            "sort_order", "id"
        )
    )
    _annotate_progress(player=player, lessons=lessons)
    return lessons


def orientation_lesson_detail(*, player, lesson_id: int) -> ChapterOrientationLesson | None:
    lesson = (
        ChapterOrientationLesson.objects.filter(id=lesson_id, is_published=True)
        .select_related("chapter")
        .first()
    )
    if lesson is None:
        return None
    _annotate_progress(player=player, lessons=[lesson])
    return lesson


def mark_orientation_lesson_complete(
    *, player, lesson: ChapterOrientationLesson, highest_step_seen: int
) -> ChapterOrientationProgress:
    progress, _ = ChapterOrientationProgress.objects.get_or_create(player=player, lesson=lesson)
    progress.highest_step_seen = max(progress.highest_step_seen, highest_step_seen)
    progress.completed_at = progress.completed_at or timezone.now()
    progress.save(update_fields=["highest_step_seen", "completed_at"])
    return progress


def _annotate_progress(*, player, lessons: list[ChapterOrientationLesson]) -> None:
    """Attach `_is_complete`/`_highest_step_seen` to each lesson instance.

    Batch-loaded once per call rather than queried per lesson, matching the
    access-context pattern used elsewhere in this package (adventure_access.py,
    challenge_access.py)."""
    is_complete_by_id = {lesson.id: False for lesson in lessons}
    highest_step_by_id = {lesson.id: 0 for lesson in lessons}
    if player is not None and lessons:
        rows = ChapterOrientationProgress.objects.filter(
            player=player, lesson_id__in=[lesson.id for lesson in lessons]
        ).values_list("lesson_id", "completed_at", "highest_step_seen")
        for lesson_id, completed_at, highest_step_seen in rows:
            is_complete_by_id[lesson_id] = completed_at is not None
            highest_step_by_id[lesson_id] = highest_step_seen
    for lesson in lessons:
        lesson._is_complete = is_complete_by_id.get(lesson.id, False)
        lesson._highest_step_seen = highest_step_by_id.get(lesson.id, 0)
