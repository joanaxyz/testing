from unittest import mock

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings


@mock.patch("common.management.commands.seed_all.call_command")
def test_seed_all_is_non_destructive_by_default(mock_call_command):
    call_command("seed_all", verbosity=0)

    assert mock_call_command.call_args_list[0] == mock.call(
        "seed_curriculum", reset=False, validate=False, verbosity=0
    )
    assert mock_call_command.call_args_list[1] == mock.call("seed_legacy_modules", verbosity=0)
    assert mock_call_command.call_args_list[2] == mock.call("seed_command_library", verbosity=0)


def test_seed_all_reset_requires_explicit_confirmation():
    with pytest.raises(CommandError, match="both --reset and --confirm-reset"):
        call_command("seed_all", reset=True, verbosity=0)


@override_settings(DEBUG=False, ALLOW_DESTRUCTIVE_SEED_RESET=False)
def test_seed_all_reset_is_blocked_in_production():
    with pytest.raises(CommandError, match="disabled when DJANGO_DEBUG=False"):
        call_command("seed_all", reset=True, confirm_reset=True, verbosity=0)


@override_settings(DEBUG=False, ALLOW_DESTRUCTIVE_SEED_RESET=True)
@mock.patch("common.management.commands.seed_all.call_command")
def test_seed_all_reset_can_be_explicitly_enabled_for_maintenance(mock_call_command):
    call_command("seed_all", reset=True, confirm_reset=True, verbosity=0)

    assert mock_call_command.call_args_list[0] == mock.call(
        "seed_curriculum", reset=True, validate=False, verbosity=0
    )
