"""Schema-only success responses owned by the Adventure domain.

Runtime values stay in :mod:`adventures.payloads`; these serializers document
and validate that presenter output for OpenAPI generation.
"""

from drf_spectacular.utils import PolymorphicProxySerializer, extend_schema_field
from rest_framework import serializers

from common.openapi import GameplayRunStatusField, RuntimeStepResponseSerializer


class AdventureRunResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = GameplayRunStatusField()
    replay = serializers.BooleanField()
    stars = serializers.IntegerField()
    library_opened = serializers.BooleanField()
    is_passed = serializers.BooleanField()
    selected_level = serializers.DictField(allow_null=True)
    next_level = serializers.DictField(allow_null=True)
    story = serializers.DictField(allow_null=True)
    chapter_id = serializers.IntegerField(allow_null=True)
    battle_stage = serializers.DictField(allow_null=True)
    current_level_index = serializers.IntegerField()
    total_levels = serializers.IntegerField()
    current_wave = serializers.IntegerField()
    total_waves = serializers.IntegerField()
    passed = serializers.BooleanField()
    mastery = serializers.DictField()
    completed_at = serializers.DateTimeField(allow_null=True)
    current_attempt = serializers.DictField(allow_null=True)
    results = serializers.ListField(child=serializers.DictField())
    progress = serializers.DictField()


class AdventureRunPatchResponseSerializer(serializers.Serializer):
    partial = serializers.ChoiceField(choices=(True,))
    id = serializers.IntegerField()
    status = GameplayRunStatusField()
    current_attempt = serializers.DictField()


@extend_schema_field(
    PolymorphicProxySerializer(
        component_name="AdventureCommandRunResponse",
        serializers=(AdventureRunResponseSerializer, AdventureRunPatchResponseSerializer),
        resource_type_field_name=None,
    )
)
class AdventureCommandRunResponseField(serializers.Field):
    """Validate and document the full-run-or-live-patch command branch."""

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("Expected an object.")
        serializer_class = (
            AdventureRunPatchResponseSerializer
            if data.get("partial") is True
            else AdventureRunResponseSerializer
        )
        serializer = serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def to_representation(self, value):
        return value


class AdventureLevelLibraryResponseSerializer(serializers.Serializer):
    book = serializers.DictField()
    run = AdventureRunResponseSerializer()


class AdventureCommandResponseSerializer(serializers.Serializer):
    run = AdventureCommandRunResponseField()
    solved = serializers.BooleanField()
    stdout = serializers.CharField(allow_blank=True)
    stderr = serializers.CharField(allow_blank=True)
    exit_code = serializers.IntegerField()
    terminal_output = serializers.CharField(allow_blank=True)
    command_classification = serializers.CharField(allow_blank=True)
    step = RuntimeStepResponseSerializer()
    command_outcome = serializers.DictField()


# ---------------------------------------------------------------------------
# AdventureLevelTierRun response shapes - mirror challenges/openapi.py exactly,
# since tier_payloads.py mirrors challenges/payloads.py's shape (not the
# wave-based Adventure shapes above). New/parallel schema only.
# ---------------------------------------------------------------------------


class AdventureLevelTierRunStepResponseSerializer(RuntimeStepResponseSerializer):
    command_classification = serializers.CharField(allow_blank=True)
    contextual_feedback = serializers.CharField(allow_blank=True)
    visualization_snapshot = serializers.DictField()
    created_at = serializers.DateTimeField()


class AdventureLevelTierCommandStepResponseSerializer(AdventureLevelTierRunStepResponseSerializer):
    evaluation_result = serializers.CharField()


class AdventureLevelTierCommandRunResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    replay = serializers.BooleanField()
    stars = serializers.IntegerField()
    status = GameplayRunStatusField()
    failure_reason = serializers.CharField(allow_null=True, allow_blank=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    counts = serializers.DictField()
    repository_state = serializers.DictField()
    visualization = serializers.DictField()
    progress = serializers.DictField(required=False)
    completion = serializers.DictField(required=False, allow_null=True)
    next_difficulty = serializers.DictField(required=False, allow_null=True)


class AdventureLevelTierRunResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    replay = serializers.BooleanField()
    stars = serializers.IntegerField()
    status = GameplayRunStatusField()
    failure_reason = serializers.CharField(allow_null=True, allow_blank=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    tier = serializers.DictField()
    scenario_context = serializers.DictField()
    chapter = serializers.DictField(allow_null=True)
    story = serializers.DictField(allow_null=True)
    difficulty = serializers.CharField(allow_null=True)
    variant = serializers.DictField()
    progress = serializers.DictField()
    policy = serializers.DictField()
    counts = serializers.DictField()
    scaffolding = serializers.DictField()
    repository_state = serializers.DictField()
    visualization = serializers.DictField()
    expected_state = serializers.DictField(allow_null=True)
    steps = AdventureLevelTierRunStepResponseSerializer(many=True)
    next_difficulty = serializers.DictField(allow_null=True)
    completion = serializers.DictField(allow_null=True)


class AdventureLevelTierCommandResponseSerializer(serializers.Serializer):
    run = AdventureLevelTierCommandRunResponseSerializer()
    command_outcome = serializers.DictField()
    stdout = serializers.CharField(allow_blank=True)
    stderr = serializers.CharField(allow_blank=True)
    exit_code = serializers.IntegerField()
    command_family = serializers.CharField(allow_blank=True)
    diagnostic_metadata = serializers.ListField(child=serializers.CharField())
    step = AdventureLevelTierCommandStepResponseSerializer()
