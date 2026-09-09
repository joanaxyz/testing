from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from curriculum.models import Story
from curriculum.selectors import chapter_locked, story_completed, story_locked
from curriculum.services import CHEST_SCHEDULE
from shop.access import owns_item
from shop.catalog import KIND_STORY


class StoryPrerequisiteSerializer(serializers.Serializer):
    slug = serializers.CharField()
    title = serializers.CharField()
    completed = serializers.BooleanField()


class ChapterStorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    slug = serializers.CharField()
    title = serializers.CharField()
    world_slug = serializers.CharField()


class ChapterLevelCompletionSerializer(serializers.Serializer):
    value = serializers.FloatField()
    numerator = serializers.IntegerField()
    denominator = serializers.IntegerField()


class ChapterChestRewardSerializer(serializers.Serializer):
    threshold = serializers.IntegerField()
    coins = serializers.IntegerField()


class StorySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    slug = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    summary = serializers.CharField(read_only=True)
    price = serializers.IntegerField(read_only=True)
    sort_order = serializers.IntegerField(read_only=True)
    is_published = serializers.BooleanField(read_only=True)
    completed = serializers.SerializerMethodField()
    owned = serializers.SerializerMethodField()
    world_slug = serializers.CharField(read_only=True)
    difficulty = serializers.ChoiceField(
        choices=Story.DIFFICULTY_CHOICES,
        read_only=True,
    )
    prerequisite_story = serializers.SerializerMethodField()
    locked = serializers.SerializerMethodField()
    lock_reason = serializers.SerializerMethodField()

    def _completed(self, story) -> bool:
        completed_map = self.context.get("story_completed_map")
        if completed_map is not None and story.id in completed_map:
            return completed_map[story.id]
        return story_completed(player=self.context.get("player"), story=story)

    def get_completed(self, obj) -> bool:
        return self._completed(obj)

    def get_owned(self, obj) -> bool:
        return owns_item(
            player=self.context.get("player"),
            kind=KIND_STORY,
            slug=obj.slug,
        )

    @extend_schema_field(StoryPrerequisiteSerializer(allow_null=True))
    def get_prerequisite_story(self, obj) -> dict | None:
        prerequisite = obj.prerequisite_story
        if prerequisite is None:
            return None
        return {
            "slug": prerequisite.slug,
            "title": prerequisite.title,
            "completed": self._completed(prerequisite),
        }

    def get_locked(self, obj) -> bool:
        locked, _ = story_locked(
            player=self.context.get("player"),
            story=obj,
            completed_map=self.context.get("story_completed_map"),
        )
        return locked

    def get_lock_reason(self, obj) -> str:
        _, reason = story_locked(
            player=self.context.get("player"),
            story=obj,
            completed_map=self.context.get("story_completed_map"),
        )
        return reason


class ChapterListSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    slug = serializers.CharField(read_only=True)
    number = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    sort_order = serializers.IntegerField(read_only=True)
    is_playable = serializers.BooleanField(read_only=True)
    is_orientation = serializers.BooleanField(read_only=True)
    command_skill_count = serializers.IntegerField(read_only=True)
    challenge_count = serializers.IntegerField(read_only=True)
    adventure_level_count = serializers.IntegerField(read_only=True)
    level_completion = serializers.SerializerMethodField()
    story = serializers.SerializerMethodField()
    locked = serializers.SerializerMethodField()
    lock_reason = serializers.SerializerMethodField()
    chest_schedule = serializers.SerializerMethodField()

    @extend_schema_field(ChapterLevelCompletionSerializer())
    def get_level_completion(self, obj) -> dict:
        denominator_map = self.context.get("chapter_completion_denominator_map", {})
        count_map = self.context.get("chapter_completion_count_map", {})
        denominator = int(denominator_map.get(obj.id, 0) or 0)
        numerator = int(count_map.get(obj.id, 0) or 0)
        value = round((numerator / denominator) * 100, 1) if denominator else 0.0
        return {
            "value": value,
            "numerator": numerator,
            "denominator": denominator,
        }

    @extend_schema_field(ChapterStorySerializer(allow_null=True))
    def get_story(self, obj) -> dict | None:
        if not obj.story_id:
            return None
        return {
            "id": obj.story_id,
            "slug": obj.story.slug,
            "title": obj.story.title,
            "world_slug": obj.story.world_slug,
        }

    def get_locked(self, obj) -> bool:
        locked, _ = chapter_locked(player=self.context.get("player"), chapter=obj)
        return locked

    def get_lock_reason(self, obj) -> str:
        _, reason = chapter_locked(player=self.context.get("player"), chapter=obj)
        return reason

    @extend_schema_field(ChapterChestRewardSerializer(many=True))
    def get_chest_schedule(self, obj) -> list[dict]:
        # Fixed, universal schedule computed at runtime - every chapter shows
        # the same reward-per-threshold preview; nothing is authored per chapter.
        return CHEST_SCHEDULE


class ChapterOrientationLessonListSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    slug = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    subtitle = serializers.CharField(read_only=True)
    sort_order = serializers.IntegerField(read_only=True)
    is_complete = serializers.SerializerMethodField()

    def get_is_complete(self, obj) -> bool:
        return bool(getattr(obj, "_is_complete", False))


class ChapterOrientationLessonDetailSerializer(ChapterOrientationLessonListSerializer):
    content_html = serializers.CharField(read_only=True)
    scoped_css = serializers.CharField(read_only=True)
    interaction_steps = serializers.JSONField(read_only=True)
    highest_step_seen = serializers.SerializerMethodField()

    def get_highest_step_seen(self, obj) -> int:
        return int(getattr(obj, "_highest_step_seen", 0))


class ChapterOrientationCompleteSerializer(serializers.Serializer):
    highest_step_seen = serializers.IntegerField(min_value=0)
