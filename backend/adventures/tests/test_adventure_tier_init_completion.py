from copy import deepcopy

from rest_framework.test import APIClient

from adventures.models import (
    AdventureLevel,
    AdventureLevelTier,
    AdventureLevelTierProgress,
    AdventureLevelTierWave,
    AdventureLevelTierWaveVariant,
)
from adventures.services import AdventureLevelTierRunService
from curriculum.models import Chapter, Story
from players.services import get_or_create_player
from progress.models import AdventureLevelTierCompletion
from testing.frontend_execution import frontend_execution_payload


def test_git_init_completes_tier_persists_progress_and_unlocks_medium(db, django_user_model):
    user = django_user_model.objects.create_user(username="tier-init", password="pass12345")
    player = get_or_create_player(user)
    story = Story.objects.create(slug="tier-init-story", title="Tier init story")
    chapter = Chapter.objects.create(
        story=story,
        slug="tier-init-chapter",
        number=1,
        title="Module 1",
        description="",
    )
    level = AdventureLevel.objects.create(
        chapter=chapter,
        slug="initializing-a-local-repository",
        title="Initializing Repositories",
    )
    easy = AdventureLevelTier.objects.create(adventure_level=level, difficulty="easy")
    medium = AdventureLevelTier.objects.create(adventure_level=level, difficulty="medium")
    easy_wave = AdventureLevelTierWave.objects.create(
        tier=easy,
        slug="init-easy",
        min_counted_commands=1,
        max_counted_commands=12,
        required_successful_attempts=1,
    )
    medium_wave = AdventureLevelTierWave.objects.create(
        tier=medium,
        slug="init-medium",
        min_counted_commands=1,
        max_counted_commands=10,
        required_successful_attempts=1,
    )
    initial_state = {
        "repository_initialized": False,
        "commits": [],
        "branches": {},
        "head": {"type": "branch", "name": "main"},
        "staging": {},
        "working_tree": {},
        "conflicts": [],
    }
    rules = [
        {"type": "commit_count_equals", "count": 0},
        {"type": "operation_metadata_equals", "key": "last_init_directory", "value": None},
        {
            "type": "operation_metadata_equals",
            "key": "last_init_current_directory",
            "value": True,
        },
        {
            "type": "operation_metadata_equals",
            "key": "last_init_initial_branch",
            "value": "main",
        },
        {"type": "operation_metadata_equals", "key": "last_init_quiet", "value": False},
        {
            "type": "operation_metadata_equals",
            "key": "last_init_reinitialized",
            "value": False,
        },
    ]
    variant = AdventureLevelTierWaveVariant.objects.create(
        wave=easy_wave,
        slug="init-easy-current-empty",
        label="Initialize the current folder",
        initial_state=initial_state,
        evaluation_spec={
            "state_requirements": {
                "repository_initialized": True,
                "head_branch": "main",
                "staging_empty": True,
                "rules": rules,
            },
            "process_requirements": {"required_commands": [], "forbidden_commands": []},
            "completion_policy": {"mode": "rules"},
        },
        solution_commands=["git init"],
    )
    AdventureLevelTierWaveVariant.objects.create(
        wave=medium_wave,
        slug="init-medium-placeholder",
        label="Initialize a named folder",
        initial_state=initial_state,
        evaluation_spec={
            "state_requirements": {"repository_initialized": True},
            "process_requirements": {"required_commands": [], "forbidden_commands": []},
            "completion_policy": {"mode": "rules"},
        },
        solution_commands=["git init project"],
    )
    run = AdventureLevelTierRunService().start_run(
        player=player,
        tier=easy,
        source_entry_point="level_page",
    )
    assert run.selected_variant_id == variant.id

    initialized = deepcopy(run.repository_state)
    initialized.update(
        {
            "repository_initialized": True,
            "branches": {"main": None},
            "head": {"type": "branch", "name": "main", "target": None},
            "commits": [],
            "staging": {},
            "conflicts": [],
            "remotes": {},
            "remote_branches": {},
            "upstream_tracking": {},
        }
    )
    metadata = {
        "last_init_branch": "main",
        "last_init_initial_branch": "main",
        "last_init_directory": None,
        "last_init_current_directory": True,
        "last_init_quiet": False,
        "last_init_reinitialized": False,
        "repository_reinitialized": False,
    }
    initialized["operation_metadata"] = metadata
    initialized.update(metadata)

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/adventure-tier-runs/{run.id}/submit-command/",
        {
            "command": "git init",
            "execution": frontend_execution_payload(
                "git init",
                initialized,
                client_run_revision=0,
            ),
        },
        format="json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["command_outcome"]["solved"] is True
    assert payload["run"]["status"] == "completed"
    assert payload["run"]["progress"] == {"completed": 1, "total": 1, "cleared": True}
    assert payload["run"]["completion"] is not None
    assert payload["run"]["next_difficulty"] == {"id": medium.id, "difficulty": "medium"}

    run.refresh_from_db()
    assert run.status == "completed"
    assert AdventureLevelTierProgress.objects.get(player=player, tier=easy).successful_clears == 1
    assert AdventureLevelTierCompletion.objects.filter(player=player, tier=easy).exists()

    unlocked_run = AdventureLevelTierRunService().start_run(
        player=player,
        tier=medium,
        source_entry_point="level_page",
    )
    assert unlocked_run.status == "started"
