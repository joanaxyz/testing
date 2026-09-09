"""Input-validation serializers for AdventureLevelTierRun endpoints.

Mirrors challenges/serializers.py. Response payloads are built in
tier_payloads.py (presenter layer) - this file holds input validation only.
"""

from rest_framework import serializers


class AdventureLevelTierRunStartSerializer(serializers.Serializer):
    source_entry_point = serializers.ChoiceField(
        choices=["level_page", "retry"],
        default="level_page",
    )
    prior_run_id = serializers.IntegerField(required=False, allow_null=True)
    replay = serializers.BooleanField(required=False, default=False)
