from rest_framework import serializers

PAGE_CONTEXTS = (
    "home",
    "stories",
    "story_map",
    "performance",
    "shop",
    "settings",
    "other",
)


class StrictSerializer(serializers.Serializer):
    """Serializer that rejects undeclared fields instead of silently ignoring them."""

    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields) if isinstance(data, dict) else set()
        if unknown:
            raise serializers.ValidationError(
                {field: "This field is not allowed." for field in sorted(unknown)}
            )
        return super().to_internal_value(data)


class AIChatMessageSerializer(StrictSerializer):
    role = serializers.ChoiceField(choices=("user", "assistant"))
    content = serializers.CharField(max_length=2000, trim_whitespace=True)


class AIChatRequestSerializer(StrictSerializer):
    message = serializers.CharField(max_length=1000, trim_whitespace=True)
    history = AIChatMessageSerializer(many=True, required=False, default=list)
    page_context = serializers.ChoiceField(choices=PAGE_CONTEXTS)

    def validate_history(self, value):
        if len(value) > 12:
            raise serializers.ValidationError("Keep at most 12 history messages.")
        if not value:
            return value
        if value[0]["role"] != "user" or value[-1]["role"] != "assistant":
            raise serializers.ValidationError(
                "History must contain complete user and assistant exchanges."
            )
        for previous, current in zip(value, value[1:], strict=False):
            if previous["role"] == current["role"]:
                raise serializers.ValidationError("History roles must alternate.")
        return value


class AIChatResponseSerializer(serializers.Serializer):
    reply = serializers.CharField()
    policy_status = serializers.ChoiceField(choices=("allowed", "redirected"))
    request_id = serializers.UUIDField()


class AIChatErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
