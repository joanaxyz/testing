from copy import deepcopy
from types import SimpleNamespace

from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from adventures.models import AdventureLevel, AdventureRun
from adventures.services import (
    AdventureCommandService,
    AdventureRunService,
    form_solve_targets,
)
from adventures.services.history import AdventureCommandHistoryCache
from common.constants import RESULT_TARGET_MATCHED
from curriculum.library import library_key_for_command
from curriculum.selectors import adventure_summary_payload
from players.services import get_or_create_player
from practice.models import CommandStep
from progress.models import AdventureLevelCompletion
from simulator.services import normalize_command
from testing.frontend_execution import frontend_execution_payload


def make_user(django_user_model, username="adventurer"):
    user = django_user_model.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="pass12345",
    )
    # Starting an adventure requires an owned companion; grant one directly so
    # these runtime tests don't have to go through the shop purchase flow.
    from shop.models import Entitlement

    Entitlement.objects.get_or_create(
        player=get_or_create_player(user), kind="companion", slug="blue"
    )
    return user


def test_adventure_history_cache_key_changes_for_reused_ids_and_new_waves():
    first_wave = SimpleNamespace(
        id=7,
        started_at="run-a",
        current_wave_id=11,
        selected_variant_id=101,
    )
    next_wave = SimpleNamespace(
        id=7,
        started_at="run-a",
        current_wave_id=12,
        selected_variant_id=102,
    )
    reused_id = SimpleNamespace(
        id=7,
        started_at="run-b",
        current_wave_id=11,
        selected_variant_id=101,
    )

    first_key = AdventureCommandHistoryCache.key_for(attempt=first_wave, log_count=2)

    assert first_key != AdventureCommandHistoryCache.key_for(attempt=next_wave, log_count=2)
    assert first_key != AdventureCommandHistoryCache.key_for(attempt=reused_id, log_count=2)


def first_level():
    from adventures.models import AdventureLevel

    return (
        AdventureLevel.objects.filter(is_published=True, waves__variants__is_published=True)
        .select_related("chapter")
        .prefetch_related("command_forms", "waves__variants")
        .order_by(
            "chapter__sort_order",
            "sort_order",
            "id",
        )
        .distinct()
        .first()
    )


def complete_level(service, run):
    """Solve every wave in a level run until it completes."""
    guard = 0
    while run.status == "started" and guard < 50:
        guard += 1
        wave = run.current_wave
        service.record_wave_outcome(
            attempt=run,
            solved=True,
            defeated=False,
            counted_command_count=wave.min_counted_commands,
            command_count=wave.min_counted_commands,
        )


def test_old_adventure_launch_without_level_is_rejected(db, django_user_model):
    call_command("seed_curriculum")
    user = make_user(django_user_model)
    level = first_level()
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(f"/api/adventures/{level.slug}/runs/")

    assert response.status_code == 400
    assert "adventure-levels" in response.json()["detail"]


def test_discarding_active_adventure_deletes_run(db, django_user_model):
    call_command("seed_curriculum")
    user = make_user(django_user_model)
    level = first_level()
    run = AdventureRunService().start_run(player=get_or_create_player(user), level=level)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.delete(f"/api/adventure-runs/{run.id}/")

    assert response.status_code == 204
    assert not AdventureRun.objects.filter(id=run.id).exists()


def test_starting_adventure_level_discards_stale_active_run(db, django_user_model):
    call_command("seed_curriculum")
    user = make_user(django_user_model)
    level = first_level()
    stale = AdventureRunService().start_run(player=get_or_create_player(user), level=level)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(f"/api/adventure-levels/{level.id}/runs/")

    assert response.status_code == 201
    assert response.json()["id"] != stale.id
    assert not AdventureRun.objects.filter(id=stale.id).exists()
    assert AdventureRun.objects.filter(id=response.json()["id"], status="started").exists()


def test_active_adventure_run_is_not_exposed_as_resumable_session(db, django_user_model):
    call_command("seed_curriculum")
    user = make_user(django_user_model)
    level = first_level()
    AdventureRunService().start_run(player=get_or_create_player(user), level=level)

    payload = adventure_summary_payload(player=get_or_create_player(user), adventure=level)

    assert payload["is_passed"] is False
    assert payload["completion"] is None
    assert "status" not in payload
    assert "active_run_id" not in payload
    assert "latest_run_id" not in payload


def test_passed_run_unlocks_next_level_even_without_completion_row(db, django_user_model):
    call_command("seed_curriculum")
    user = make_user(django_user_model, username="passed-unlocks-next")
    player = get_or_create_player(user)
    levels = list(
        AdventureLevel.objects.filter(
            is_published=True,
            waves__variants__is_published=True,
            chapter__story__slug="arcane-spire",
        )
        .select_related("chapter")
        .prefetch_related("command_forms", "waves__variants")
        .order_by("chapter__sort_order", "sort_order", "id")
        .distinct()[:2]
    )
    first, second = levels
    run = AdventureRunService().start_run(player=player, level=first)
    run.status = "completed"
    run.passed_at = timezone.now()
    run.completed_at = run.passed_at
    run.save(update_fields=["status", "passed_at", "completed_at"])
    AdventureLevelCompletion.objects.filter(player=player, adventure_level=first).delete()

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(f"/api/adventure-levels/{second.id}/runs/")

    assert response.status_code == 201


def test_budget_exhaustion_fails_adventure_wave(db, django_user_model):
    call_command("seed_curriculum")
    user = make_user(django_user_model)
    level = first_level()
    run = AdventureRunService().start_run(player=get_or_create_player(user), level=level)
    budget = run.current_wave.max_counted_commands
    run.command_count = max(0, budget - 1)
    run.counted_command_count = max(0, budget - 1)
    run.save(update_fields=["command_count", "counted_command_count"])
    command = "git nope"

    result = AdventureCommandService().submit(
        attempt=run,
        command=command,
        execution=frontend_execution_payload(
            command,
            run.repository_state,
            processed=False,
            output="git: 'nope' is not a git command.",
            exit_code=129,
            client_run_revision=run.command_count,
        ),
    )

    assert result["command_outcome"]["failed"] is True
    run.refresh_from_db()
    assert run.status == "failed"
    assert run.stars == 0
    assert not AdventureLevelCompletion.objects.filter(adventure_run=run).exists()


def test_first_repository_workflow_wave_does_not_complete_after_only_init(db, django_user_model):
    from adventures.models import AdventureWave

    call_command("seed_curriculum")
    user = make_user(django_user_model)
    # The init+stage+commit workflow wave must not pass after only the first
    # command, no matter which level the blueprint places it in.
    wave = AdventureWave.objects.get(slug="ch1-adv-init-current-folder", is_published=True)
    level = wave.level
    run = AdventureRunService().start_run(player=get_or_create_player(user), level=level)
    assert run.current_wave.slug == "ch1-adv-init-current-folder"

    init_only_state = deepcopy(run.repository_state)
    init_only_state.update(
        {
            "repository_initialized": True,
            "branches": {"main": None},
            "head": {"type": "branch", "name": "main", "target": None},
            "commits": [],
            "staging": {},
            "operation_metadata": {
                "last_init_branch": "main",
                "last_init_directory": None,
                "last_init_current_directory": True,
                "last_init_initial_branch": "main",
                "last_init_quiet": False,
                "last_init_reinitialized": False,
                "repository_reinitialized": False,
            },
            "last_init_branch": "main",
            "last_init_directory": None,
            "last_init_current_directory": True,
            "last_init_initial_branch": "main",
            "last_init_quiet": False,
            "last_init_reinitialized": False,
            "repository_reinitialized": False,
        }
    )

    result = AdventureCommandService().submit(
        attempt=run,
        command="git init",
        execution=frontend_execution_payload(
            "git init", init_only_state, client_run_revision=run.command_count
        ),
    )

    assert result["step"].result_category != RESULT_TARGET_MATCHED
    run.refresh_from_db()
    assert run.status == "started"
    assert run.current_wave.slug == "ch1-adv-init-current-folder"
    assert run.counted_command_count == 1


def test_first_snapshot_battle_progress_survives_invalid_commit_and_rewards_add(
    db,
    django_user_model,
):
    from adventures.models import AdventureWave

    call_command("seed_curriculum")
    user = make_user(django_user_model, username="first-snapshot-progress")
    wave = AdventureWave.objects.get(slug="ch1-adv-init-current-folder", is_published=True)
    run = AdventureRunService().start_run(
        player=get_or_create_player(user),
        level=wave.level,
    )
    service = AdventureCommandService()

    initialized = deepcopy(run.repository_state)
    initialized.update(
        {
            "repository_initialized": True,
            "branches": {"main": None},
            "head": {"type": "branch", "name": "main", "target": None},
            "commits": [],
            "staging": {},
            "operation_metadata": {
                "last_init_branch": "main",
                "last_init_directory": None,
                "last_init_current_directory": True,
                "last_init_initial_branch": "main",
                "last_init_quiet": False,
                "last_init_reinitialized": False,
                "repository_reinitialized": False,
            },
            "last_init_branch": "main",
            "last_init_directory": None,
            "last_init_current_directory": True,
            "last_init_initial_branch": "main",
            "last_init_quiet": False,
            "last_init_reinitialized": False,
            "repository_reinitialized": False,
        }
    )
    init_result = service.submit(
        attempt=run,
        command="git init",
        execution=frontend_execution_payload(
            "git init",
            initialized,
            client_run_revision=run.command_count,
        ),
    )
    init_progress = init_result["command_outcome"]["rules_passing"]
    assert init_result["command_outcome"]["rules_delta"] > 0

    invalid_result = service.submit(
        attempt=run,
        command="git commit",
        execution=frontend_execution_payload(
            "git commit",
            initialized,
            processed=False,
            output="nothing to commit",
            exit_code=1,
            client_run_revision=run.command_count,
        ),
    )
    assert invalid_result["command_outcome"]["previous_rules_passing"] == init_progress
    assert invalid_result["command_outcome"]["rules_passing"] == init_progress
    assert invalid_result["command_outcome"]["rules_delta"] == 0

    reinitialized = deepcopy(initialized)
    reinitialized["operation_metadata"]["last_init_reinitialized"] = True
    reinitialized["operation_metadata"]["repository_reinitialized"] = True
    reinitialized["last_init_reinitialized"] = True
    reinitialized["repository_reinitialized"] = True
    repeated_init_result = service.submit(
        attempt=run,
        command="git init",
        execution=frontend_execution_payload(
            "git init",
            reinitialized,
            client_run_revision=run.command_count,
        ),
    )
    assert repeated_init_result["command_outcome"]["previous_rules_passing"] == init_progress
    assert repeated_init_result["command_outcome"]["rules_passing"] == init_progress
    assert repeated_init_result["command_outcome"]["rules_delta"] == 0

    staged = deepcopy(initialized)
    staged["staging"] = deepcopy(staged["working_tree"])
    staged["working_tree"] = {}
    add_result = service.submit(
        attempt=run,
        command="git add .",
        execution=frontend_execution_payload(
            "git add .",
            staged,
            client_run_revision=run.command_count,
        ),
    )
    assert add_result["command_outcome"]["previous_rules_passing"] == init_progress
    assert add_result["command_outcome"]["rules_passing"] > init_progress
    assert add_result["command_outcome"]["rules_delta"] > 0


def _multi_wave_level():
    from django.db.models import Count, Q

    from adventures.models import AdventureLevel

    return (
        AdventureLevel.objects.filter(is_published=True, waves__variants__is_published=True)
        .annotate(wave_count=Count("waves", filter=Q(waves__is_published=True), distinct=True))
        .filter(wave_count__gte=2)
        .select_related("chapter")
        .order_by("chapter__sort_order", "sort_order", "id")
        .distinct()
        .first()
    )


def test_wave_advance_response_returns_neutral_command_outcome(db, django_user_model):
    """Solving a non-final wave returns command_outcome only; battle animation
    state is now derived by the frontend and is not persisted or returned."""
    call_command("seed_curriculum")
    user = make_user(django_user_model)
    level = _multi_wave_level()
    assert level is not None, "seed data should include a multi-wave level"
    run = AdventureRunService().start_run(player=get_or_create_player(user), level=level)
    first_wave_id = run.current_wave_id
    variant = run.selected_variant
    solution = variant.solution_commands or ["git status"]
    # Fast-forward the earlier commands (mirrors test_depleted_hp) so the final
    # command lands the solving blow and advances the wave. HP is left untouched.
    for attempt_number, command in enumerate(solution[:-1], start=1):
        CommandStep.objects.create(
            attempt=run,
            command_text=command,
            terminal_output="",
            result_category="TargetNotYetMatched",
            command_classification="counted_action",
            normalized_command=normalize_command(command),
            was_processable=True,
            counted_increment=1,
            attempt_number=attempt_number,
            counted_total_after=attempt_number,
        )
    run.command_count = max(0, len(solution) - 1)
    run.counted_command_count = max(0, len(solution) - 1)
    run.save(update_fields=["command_count", "counted_command_count"])

    result = AdventureCommandService().submit(
        attempt=run,
        command=solution[-1],
        execution=frontend_execution_payload(
            solution[-1], variant.target_state, client_run_revision=run.command_count
        ),
    )

    assert result["step"].result_category == RESULT_TARGET_MATCHED
    assert result["wave_advanced"] is True
    run.refresh_from_db()
    assert run.current_wave_id != first_wave_id  # the run advanced to a new wave

    assert result["command_outcome"]["solved"] is True
    assert result["command_outcome"]["failed"] is False
    assert not any(key.startswith("battle_") for key in result)


def test_adventure_level_run_is_scoped_to_one_level(db, django_user_model):
    call_command("seed_curriculum")
    user = make_user(django_user_model)
    level = first_level()
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(f"/api/adventure-levels/{level.id}/runs/")

    assert response.status_code == 201
    payload = response.json()
    run = AdventureRun.objects.get(id=payload["id"])
    levels = list(
        AdventureLevel.objects.filter(chapter_id=level.chapter_id, is_published=True).order_by(
            "sort_order", "id"
        )
    )
    level_ids = [item.id for item in levels]
    current_index = level_ids.index(level.id)
    assert run.level_id == level.id
    assert run.selected_variant.wave.level_id == level.id
    assert payload["selected_level"]["id"] == level.id
    assert payload["current_level_index"] == current_index + 1
    assert payload["total_levels"] == len(levels)
    assert payload["next_level"] == (
        {
            "id": levels[current_index + 1].id,
            "slug": levels[current_index + 1].slug,
            "title": levels[current_index + 1].title,
            "is_required": levels[current_index + 1].is_required,
            "reward_coins": levels[current_index + 1].reward_coins,
        }
        if current_index + 1 < len(levels)
        else None
    )
    assert payload["current_attempt"]["level"]["id"] == level.id
    assert payload["progress"] == {"completed": 0, "total": len(levels)}


def test_completing_level_records_level_and_adventure_completion(db, django_user_model):
    call_command("seed_curriculum")
    user = make_user(django_user_model)
    player = get_or_create_player(user)
    adventure = first_level()
    service = AdventureRunService()

    required_levels = AdventureLevel.objects.filter(
        chapter_id=adventure.chapter_id, is_published=True, is_required=True
    ).order_by(
        "sort_order",
        "id",
    )
    for level in required_levels:
        run = service.start_run(player=player, level=level)
        complete_level(service, run)

    assert (
        AdventureLevelCompletion.objects.filter(
            player=player,
            adventure_level__chapter_id=adventure.chapter_id,
        ).count()
        == required_levels.count()
    )
    assert AdventureLevelCompletion.objects.filter(
        player=player, adventure_level_id__in=[level.id for level in required_levels]
    ).exists()


def test_opening_level_library_filters_commands_and_penalizes_score(db, django_user_model):
    call_command("seed_curriculum")
    user = make_user(django_user_model)
    level = first_level()
    service = AdventureRunService()
    run = service.start_run(player=get_or_create_player(user), level=level)
    expected_keys = {
        library_key_for_command(command)
        for command in (run.selected_variant.solution_commands or [])
        if str(command or "").strip()
    }
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(f"/api/adventure-runs/{run.id}/level-library/")

    assert response.status_code == 200
    payload = response.json()
    commands = payload["book"]["commands"]
    wave_skill_ids = set(run.current_wave.command_forms.values_list("command_skill_id", flat=True))
    assert payload["run"]["library_opened"] is True
    assert payload["book"]["lessons"] == []
    assert commands
    assert {command["id"] for command in commands} == wave_skill_ids
    if expected_keys:
        returned_keys = {library_key_for_command(command["base_command"]) for command in commands}
        assert returned_keys <= expected_keys

    run.refresh_from_db()
    complete_level(service, run)
    run.refresh_from_db()
    completion = AdventureLevelCompletion.objects.get(
        player=get_or_create_player(user), adventure_level=level
    )
    assert run.stars == 2
    assert completion.stars == 2


def test_replay_can_restore_perfect_score_after_library_penalty(db, django_user_model):
    call_command("seed_curriculum")
    user = make_user(django_user_model)
    level = first_level()
    service = AdventureRunService()
    run = service.start_run(player=get_or_create_player(user), level=level)
    run.library_opened = True
    run.save(update_fields=["library_opened"])

    complete_level(service, run)
    run.refresh_from_db()
    completion = AdventureLevelCompletion.objects.get(
        player=get_or_create_player(user), adventure_level=level
    )
    assert run.stars == 2
    assert completion.stars == 2

    retry = service.start_run(player=get_or_create_player(user), level=level)
    assert retry.is_replay is True
    complete_level(service, retry)
    retry.refresh_from_db()
    completion.refresh_from_db()

    assert retry.stars == 3
    assert completion.stars == 3


def _mastery_fixture(*, chapter_slug="mastery-spiral", number=999001):
    from adventures.models import AdventureLevel, AdventureWave
    from curriculum.models import Chapter, CommandForm, CommandSkill

    chapter = Chapter.objects.create(
        slug=chapter_slug, number=number, title="Spiral", description=""
    )
    skill = CommandSkill.objects.create(
        slug=f"{chapter_slug}-skill", base_command="git spiral", title="Spiral"
    )
    form = CommandForm.objects.create(
        command_skill=skill, chapter=chapter, slug="basic", usage_form="git spiral", label="Spiral"
    )

    def level(slug, *, is_required=True, is_published=True):
        return AdventureLevel.objects.create(
            chapter=chapter,
            slug=slug,
            title=slug,
            is_required=is_required,
            is_published=is_published,
        )

    def wave(level_obj, slug, *, is_published=True, forms=(form,)):
        created = AdventureWave.objects.create(
            level=level_obj, slug=slug, title=slug, sort_order=0, is_published=is_published
        )
        for item in forms:
            created.command_forms.add(item)
        return created

    return chapter, None, form, level, wave


def test_repeated_commands_raise_mastery_target(db):
    """A command form's mastery target = the number of distinct published waves
    (inside required, published levels) that exercise it, capped so core
    commands stay achievable. Optional/unpublished levels and unpublished waves
    never inflate it; an unexercised form floors at 1 instead of 0."""
    from adventures.services import MASTERY_TARGET_CAP

    _chapter, _adventure, form, level, wave = _mastery_fixture()

    # Two published waves inside required published levels drill the command...
    spiral_1 = level("spiral-1")
    wave(spiral_1, "spiral-1-intro")
    spiral_2 = level("spiral-2")
    wave(spiral_2, "spiral-2-reuse")
    # ...while optional/draft levels and draft waves never count.
    optional = level("optional", is_required=False)
    wave(optional, "optional-wave")
    draft = level("draft", is_published=False)
    wave(draft, "draft-wave")
    wave(spiral_1, "spiral-1-draft-wave", is_published=False)

    # The same command across two qualifying waves => a target of two solves.
    assert form_solve_targets({form.id})[form.id] == 2

    # A form nothing exercises still floors at 1 (never 0).
    assert form_solve_targets({form.id, 999_999}) == {form.id: 2, 999_999: 1}

    # Waves beyond the cap keep the target clamped at MASTERY_TARGET_CAP.
    overflow = level("overflow")
    for index in range(MASTERY_TARGET_CAP + 2):
        wave(overflow, f"overflow-{index}")
    assert form_solve_targets({form.id})[form.id] == MASTERY_TARGET_CAP


def test_level_completion_credits_one_solve_per_wave(db, django_user_model):
    """Clearing a level credits one solve per published wave that exercises a
    form - repetitions inside a level finally count - and never double-credits."""
    from adventures.models import SkillMastery

    user = make_user(django_user_model)
    player = get_or_create_player(user)
    _chapter, _adventure, form, level, wave = _mastery_fixture(
        chapter_slug="mastery-credit", number=999002
    )
    drills = level("drills")
    wave(drills, "drill-1")
    wave(drills, "drill-2")
    wave(drills, "drill-3")
    wave(drills, "drill-draft", is_published=False)

    service = AdventureRunService()
    assert service._credit_mastery(player=player, level=drills) is True
    row = SkillMastery.objects.get(player=player, command_form=form)
    assert row.solves == 3
    assert row.mastered is True  # target = 3 published waves, all credited at once
    assert row.learned_at is not None

    # Crediting again (as a replay would never do) still counts waves, so the
    # guard against re-crediting lives at the call site: is_replay attempts
    # never reach _credit_mastery. Verify the second call is additive, which is
    # exactly why record_wave_outcome only calls it on first-pass completions.
    service._credit_mastery(player=player, level=drills)
    row.refresh_from_db()
    assert row.solves == 6
