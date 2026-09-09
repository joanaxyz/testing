from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import Locked
from common.openapi import (
    CommandFormPreviewResponseSerializer,
    LearnedSkillsResponseSerializer,
)
from common.services.performance import timing
from curriculum.models import Chapter
from curriculum.selectors import (
    chapter_book,
    chapter_completion_count_map,
    chapter_completion_denominator_map,
    chapter_content_overview,
    chapter_locked,
    get_command_form,
    learned_command_skills,
    mark_orientation_lesson_complete,
    orientation_lesson_detail,
    orientation_lessons_for_chapter,
    published_chapters,
    published_stories,
    stories_completed_map,
)
from curriculum.serializers import (
    ChapterListSerializer,
    ChapterOrientationCompleteSerializer,
    ChapterOrientationLessonDetailSerializer,
    ChapterOrientationLessonListSerializer,
    StorySerializer,
)
from players.services import get_or_create_player


def _player_for(request):
    if not request.user.is_authenticated:
        return None
    return get_or_create_player(request.user)


def _require_unlocked_chapter(request, chapter_id: int) -> tuple[object, Chapter]:
    chapter = (
        Chapter.objects.select_related("story")
        .filter(id=chapter_id, is_published=True, story__is_published=True)
        .first()
    )
    if chapter is None:
        raise NotFound("Chapter not found.")
    player = _player_for(request)
    locked, reason = chapter_locked(player=player, chapter=chapter)
    if locked:
        raise Locked(reason or "This chapter is locked.")
    return player, chapter


class StoryListAPIView(APIView):
    @extend_schema(responses={200: StorySerializer(many=True)})
    def get(self, request):
        stories = list(published_stories())
        player = _player_for(request)
        # One batched mastery computation covers every story and prerequisite
        # (prerequisites are select_related members of the same published set).
        completed_map = stories_completed_map(player=player, stories=stories)
        serializer = StorySerializer(
            stories,
            many=True,
            context={"player": player, "story_completed_map": completed_map},
        )
        return Response(serializer.data)


class ChapterListAPIView(APIView):
    @extend_schema(responses={200: ChapterListSerializer(many=True)})
    def get(self, request):
        chapters = list(published_chapters(story_slug=request.query_params.get("story")))
        chapter_ids = [chapter.id for chapter in chapters]
        player = _player_for(request)
        serializer = ChapterListSerializer(
            chapters,
            many=True,
            context={
                "player": player,
                "chapter_completion_count_map": chapter_completion_count_map(
                    player=player,
                    chapter_ids=chapter_ids,
                ),
                "chapter_completion_denominator_map": chapter_completion_denominator_map(
                    chapter_ids=chapter_ids,
                ),
            },
        )
        return Response(serializer.data)


class ChapterContentOverviewAPIView(APIView):
    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request, chapter_id: int):
        player, chapter = _require_unlocked_chapter(request, chapter_id)
        with timing("curriculum.chapter_overview", chapter_id=chapter.id):
            return Response(chapter_content_overview(player=player, chapter_id=chapter.id))


class ChapterBookAPIView(APIView):
    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request, chapter_id: int):
        _, chapter = _require_unlocked_chapter(request, chapter_id)
        with timing("curriculum.chapter_book", chapter_id=chapter.id):
            book = chapter_book(chapter_id=chapter.id)
        if book is None:
            raise NotFound("Chapter not found.")
        return Response(book)


class LearnedSkillsAPIView(APIView):
    """The player's registry of learned commands (their spellbook)."""

    @extend_schema(responses={200: LearnedSkillsResponseSerializer})
    def get(self, request):
        with timing("curriculum.learned_skills"):
            return Response({"results": learned_command_skills(player=_player_for(request))})


class CommandFormPreviewAPIView(APIView):
    @extend_schema(responses={200: CommandFormPreviewResponseSerializer})
    def get(self, request, form_id: int):
        form = get_command_form(form_id)
        return Response(
            {
                "id": form.id,
                "slug": form.slug,
                "usage_form": form.usage_form,
                "label": form.label,
                "summary": form.summary,
                "is_playable": form.is_playable,
                "skill": {
                    "id": form.command_skill_id,
                    "slug": form.command_skill.slug,
                    "base_command": form.command_skill.base_command,
                    "title": form.command_skill.title,
                },
                "command_preview": form.command_preview or form.command_skill.command_preview or {},
            }
        )


class ChapterOrientationLessonListAPIView(APIView):
    """Step-through reading lessons for one is_orientation=True chapter.

    Distinct from ChapterContentOverviewAPIView: orientation chapters carry no
    AdventureLevel/ChallengeLevel content, only ChapterOrientationLesson rows.
    """

    @extend_schema(responses={200: ChapterOrientationLessonListSerializer(many=True)})
    def get(self, request, chapter_id: int):
        player, chapter = _require_unlocked_chapter(request, chapter_id)
        if not chapter.is_orientation:
            raise NotFound("This chapter has no orientation lessons.")
        lessons = orientation_lessons_for_chapter(player=player, chapter_id=chapter.id)
        serializer = ChapterOrientationLessonListSerializer(lessons, many=True)
        return Response(serializer.data)


class OrientationLessonDetailAPIView(APIView):
    @extend_schema(responses={200: ChapterOrientationLessonDetailSerializer})
    def get(self, request, lesson_id: int):
        player = _player_for(request)
        lesson = orientation_lesson_detail(player=player, lesson_id=lesson_id)
        if lesson is None:
            raise NotFound("Lesson not found.")
        serializer = ChapterOrientationLessonDetailSerializer(lesson)
        return Response(serializer.data)


class OrientationLessonCompleteAPIView(APIView):
    @extend_schema(
        request=ChapterOrientationCompleteSerializer,
        responses={200: ChapterOrientationLessonDetailSerializer},
    )
    def post(self, request, lesson_id: int):
        serializer = ChapterOrientationCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        player = _player_for(request)
        if player is None:
            raise NotFound("Lesson not found.")
        lesson = orientation_lesson_detail(player=player, lesson_id=lesson_id)
        if lesson is None:
            raise NotFound("Lesson not found.")
        mark_orientation_lesson_complete(
            player=player,
            lesson=lesson,
            highest_step_seen=serializer.validated_data["highest_step_seen"],
        )
        lesson = orientation_lesson_detail(player=player, lesson_id=lesson_id)
        return Response(ChapterOrientationLessonDetailSerializer(lesson).data)
