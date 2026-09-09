from django.core.management import call_command
from rest_framework.test import APIClient

from adventures.models import AdventureLevelTier, AdventureLevelTierRun
from common.constants import DIFFICULTY_HARD, SESSION_STATUS_COMPLETED, SESSION_STATUS_FAILED
from players.services import get_or_create_player
from practice.models import CommandStep
from progress.serializers import PerformanceSummaryResponseSerializer


def test_performance_summary_uses_runebound_attempts_and_server_side_formulas(
    db, django_user_model
):
    call_command("seed_legacy_modules", verbosity=0)
    user = django_user_model.objects.create_user(
        username="performance-reader",
        email="performance-reader@example.com",
        password="pass12345",
    )
    player = get_or_create_player(user)
    tier = AdventureLevelTier.objects.filter(
        adventure_level__chapter__story__slug="git-it-legacy",
        adventure_level__chapter__number=1,
        difficulty=DIFFICULTY_HARD,
    ).first()
    assert tier is not None
    wave = tier.waves.first()
    assert wave is not None
    variant = wave.variants.first()
    assert variant is not None

    first = AdventureLevelTierRun.objects.create(
        player=player,
        tier=tier,
        current_wave=wave,
        selected_variant=variant,
        status=SESSION_STATUS_FAILED,
        retry_index=0,
    )
    retry = AdventureLevelTierRun.objects.create(
        player=player,
        tier=tier,
        current_wave=wave,
        selected_variant=variant,
        prior_run=first,
        status=SESSION_STATUS_COMPLETED,
        retry_index=1,
    )
    CommandStep.objects.create(
        adventure_tier_run=retry,
        command_text="git status",
        result_category=CommandStep.ResultCategory.TARGET_MATCHED,
        command_classification=CommandStep.CommandClassification.DIAGNOSTIC,
        normalized_command="git status",
        was_processable=True,
        attempt_number=1,
    )
    CommandStep.objects.create(
        adventure_tier_run=retry,
        command_text="git unknown",
        result_category=CommandStep.ResultCategory.INVALID,
        command_classification=CommandStep.CommandClassification.UNPROCESSABLE,
        normalized_command="git unknown",
        was_processable=False,
        attempt_number=2,
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/progress/performance/")

    assert response.status_code == 200
    payload = response.json()
    assert PerformanceSummaryResponseSerializer(data=payload).is_valid()
    assert payload["kpis"] == {
        "scr": {"value": 50.0, "numerator": 1, "denominator": 2},
        "car": {"value": 50.0, "numerator": 1, "denominator": 2},
        "hlcr": {"value": 50.0, "numerator": 1, "denominator": 2},
        "rtr": {"value": 100.0, "numerator": 1, "denominator": 1},
        "arc": {"value": 1.0, "numerator": 1, "denominator": 1},
    }
    assert payload["completed_sessions"] == 1
    assert [module["number"] for module in payload["modules"]] == [1, 2, 3, 4]
    module_one = payload["modules"][0]
    assert module_one["scr"] == payload["kpis"]["scr"]
    assert module_one["hlcr"] == payload["kpis"]["hlcr"]
    assert module_one["rtr"] == payload["kpis"]["rtr"]
    assert module_one["arc"] == payload["kpis"]["arc"]
