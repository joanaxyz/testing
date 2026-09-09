"""Unit tests for the shared client-execution submit boundary."""

import copy

import pytest

from common.constants import COMMAND_COUNTED, COMMAND_DIAGNOSTIC, COMMAND_UNPROCESSABLE
from common.exceptions import BadRequest, PayloadTooLarge
from common.git import client_command_execution
from common.git.client_command_execution import (
    ClientCommandExecutionService,
    CommandCountClassifier,
)
from testing.frontend_execution import diagnostic_payload, frontend_execution_payload


class TestCommandCountClassifier:
    def classify(self, **kwargs):
        return CommandCountClassifier().classify(**kwargs)

    def test_unprocessable_git_command_still_counts(self):
        # A git command the engine can't parse must still burn budget, or
        # learners could fish for syntax for free.
        assert self.classify(command="git frobnicate", processed=False) == (COMMAND_COUNTED, 1)

    def test_misspelled_git_itself_counts(self):
        # A typo in `git` itself is still a wasted turn - a miss that costs.
        assert self.classify(command="gti commit", processed=False) == (COMMAND_COUNTED, 1)

    def test_unprocessable_non_git_input_still_counts(self):
        # Any command the engine can't run makes no progress, so it's a miss
        # that burns budget - non-git input is no longer a free retry.
        assert self.classify(command="ls -la", processed=False) == (COMMAND_COUNTED, 1)

    def test_empty_submission_is_free(self):
        assert self.classify(command="   ", processed=False) == (COMMAND_UNPROCESSABLE, 0)

    def test_diagnostic_command_is_uncounted(self):
        assert self.classify(command="git status", processed=True, diagnostic=True) == (
            COMMAND_DIAGNOSTIC,
            0,
        )

    def test_mutating_command_counts(self):
        assert self.classify(command="git commit -m x", processed=True, diagnostic=False) == (
            COMMAND_COUNTED,
            1,
        )


class TestClientCommandExecutionService:
    def init_next_state(self, state=None):
        tools = ClientCommandExecutionService().state_tools
        previous = tools.normalize_state(state or {})
        next_state = {
            **previous,
            "repository_initialized": True,
            "branches": {
                **previous.get("branches", {}),
                "main": previous.get("branches", {}).get("main"),
            },
            "head": {
                "type": "branch",
                "name": "main",
                "target": previous.get("branches", {}).get("main"),
            },
            "operation_metadata": {
                **previous.get("operation_metadata", {}),
                "last_init_branch": "main",
                "last_init_initial_branch": "main",
                "last_init_directory": None,
                "last_init_current_directory": True,
                "last_init_quiet": False,
                "last_init_reinitialized": bool(previous.get("repository_initialized")),
                "repository_reinitialized": bool(previous.get("repository_initialized")),
            },
            "last_init_branch": "main",
            "last_init_initial_branch": "main",
            "last_init_directory": None,
            "last_init_current_directory": True,
            "last_init_quiet": False,
            "last_init_reinitialized": bool(previous.get("repository_initialized")),
            "repository_reinitialized": bool(previous.get("repository_initialized")),
        }
        return tools.normalize_state(next_state)

    def execute(self, state, command, payload=None):
        if payload is None and command == "git init":
            payload = frontend_execution_payload(command, self.init_next_state(state))
        return ClientCommandExecutionService().from_payload(
            repository_state=state,
            command=command,
            execution=payload or frontend_execution_payload(command, state),
        )

    def test_git_init_payload_is_normalized_and_counted(self):
        execution = self.execute(
            {},
            "git init",
            frontend_execution_payload("git init", self.init_next_state()),
        )
        assert execution.result.processed
        assert execution.state_mutated
        assert execution.next_state["repository_initialized"] is True
        assert execution.classification == COMMAND_COUNTED

    def test_git_init_rejects_forged_curriculum_metadata(self):
        forged = self.init_next_state()
        forged["operation_metadata"]["last_init_directory"] = "invoice-tracker"
        forged["last_init_directory"] = "invoice-tracker"

        with pytest.raises(BadRequest, match="submitted git init command"):
            self.execute(
                {},
                "git init",
                frontend_execution_payload("git init", forged),
            )

    def test_diagnostic_command_does_not_mutate_state(self):
        initialized = self.execute({}, "git init").next_state
        execution = self.execute(
            initialized,
            "git status",
            diagnostic_payload("git status", initialized),
        )
        assert execution.result.processed
        assert execution.state_mutated is False
        assert execution.classification == COMMAND_DIAGNOSTIC

    def test_merge_base_persists_backend_verified_evidence_and_ignores_forged_value(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "commits": [
                    {"id": "c0", "message": "base", "parents": [], "tree": {}},
                    {
                        "id": "c1",
                        "message": "main",
                        "parents": ["c0"],
                        "tree": {"main.txt": "main"},
                    },
                    {
                        "id": "c2",
                        "message": "feature",
                        "parents": ["c0"],
                        "tree": {"feature.txt": "feature"},
                    },
                ],
                "branches": {"main": "c1", "feature": "c2"},
                "head": {"type": "branch", "name": "main", "target": "c1"},
                "operation_metadata": {"preserved_marker": "keep-me"},
            }
        )
        forged = copy.deepcopy(state)
        forged["operation_metadata"]["last_merge_base"] = "forged"
        forged["last_merge_base"] = "forged"

        execution = self.execute(
            state,
            "git merge-base main feature",
            diagnostic_payload("git merge-base main feature", forged, output="c0"),
        )

        assert execution.classification == COMMAND_DIAGNOSTIC
        assert execution.state_mutated is True
        assert execution.next_state["operation_metadata"] == {
            "preserved_marker": "keep-me",
            "last_merge_base": "c0",
        }
        assert execution.next_state["last_merge_base"] == "c0"
        assert execution.next_state["commits"] == state["commits"]
        assert execution.next_state["branches"] == state["branches"]
        assert execution.next_state["head"] == state["head"]

    def test_rev_list_persists_backend_verified_count_evidence(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "commits": [
                    {"id": "c0", "message": "base", "parents": [], "tree": {}},
                    {"id": "c1", "message": "one", "parents": ["c0"], "tree": {"one.txt": "one"}},
                    {
                        "id": "c2",
                        "message": "two",
                        "parents": ["c1"],
                        "tree": {"one.txt": "one", "two.txt": "two"},
                    },
                ],
                "branches": {"main": "c2"},
                "head": {"type": "branch", "name": "main", "target": "c2"},
            }
        )

        execution = self.execute(
            state,
            "git rev-list --count c0..main",
            diagnostic_payload("git rev-list --count c0..main", state, output="2"),
        )

        assert execution.classification == COMMAND_DIAGNOSTIC
        assert execution.state_mutated is True
        assert execution.next_state["operation_metadata"]["last_rev_list_count"] == 2
        assert execution.next_state["last_rev_list_count"] == 2

    @pytest.mark.parametrize(
        ("command", "forged_key"),
        [
            ("git merge-base --is-ancestor main feature", "last_merge_base"),
            ("git rev-list c0..main", "last_rev_list_count"),
            ("git rev-list --count c0..main extra", "last_rev_list_count"),
        ],
    )
    def test_unsupported_diagnostic_shapes_cannot_persist_evidence(self, command, forged_key):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "commits": [
                    {"id": "c0", "message": "base", "parents": [], "tree": {}},
                    {
                        "id": "c1",
                        "message": "main",
                        "parents": ["c0"],
                        "tree": {"main.txt": "main"},
                    },
                    {
                        "id": "c2",
                        "message": "feature",
                        "parents": ["c0"],
                        "tree": {"feature.txt": "feature"},
                    },
                ],
                "branches": {"main": "c1", "feature": "c2"},
                "head": {"type": "branch", "name": "main", "target": "c1"},
            }
        )
        forged = copy.deepcopy(state)
        forged["operation_metadata"][forged_key] = "forged"
        forged[forged_key] = "forged"

        execution = self.execute(
            state,
            command,
            diagnostic_payload(command, forged, output="forged"),
        )

        assert execution.classification == COMMAND_DIAGNOSTIC
        assert execution.state_mutated is False
        assert execution.next_state == state
        assert forged_key not in execution.next_state["operation_metadata"]
        assert forged_key not in execution.next_state

    @pytest.mark.parametrize(
        ("command", "family"),
        [
            ("git credential fill", "credential"),
            ("git clean -f", "clean"),
            ("git mv README.md docs/README.md", "mv"),
            ("git update-ref refs/heads/release HEAD", "update-ref"),
            ("git gc", "gc"),
        ],
    )
    def test_rejects_processed_unsupported_inventory_commands(self, command, family):
        state = self.execute({}, "git init").next_state
        payload = frontend_execution_payload(command, state, processed=True, command_family=family)

        with pytest.raises(BadRequest):
            self.execute(state, command, payload)

    def test_caller_state_is_never_mutated_in_place(self):
        state = self.execute({}, "git init").next_state
        before = repr(state)
        target = {
            **state,
            "branches": {**state["branches"], "feature": state["branches"].get("main")},
            "head": {"type": "branch", "name": "feature", "target": state["branches"].get("main")},
        }
        self.execute(
            state,
            "git switch -c feature",
            frontend_execution_payload("git switch -c feature", target),
        )
        assert repr(state) == before

    def test_cd_noop_is_allowed_as_diagnostic(self):
        payload = frontend_execution_payload(
            "cd repo",
            {},
            processed=True,
            diagnostic=True,
            command_family="cd",
            diagnostic_metadata=["changed_directory"],
        )
        execution = self.execute({}, "cd repo", payload)
        assert execution.classification == COMMAND_DIAGNOSTIC
        assert execution.state_mutated is False

    def test_unknown_command_reports_unprocessed(self):
        execution = self.execute(
            {},
            "echo hello",
            frontend_execution_payload("echo hello", {}, processed=False, exit_code=127),
        )
        assert execution.result.processed is False
        assert execution.state_mutated is False

    def test_state_size_guard_rejects_oversized_state(self, monkeypatch):
        monkeypatch.setattr(client_command_execution, "MAX_REPOSITORY_STATE_BYTES", 10)
        with pytest.raises(PayloadTooLarge):
            self.execute({}, "git init")

    def test_state_size_guard_ignores_diagnostic_commands(self, monkeypatch):
        initialized = self.execute({}, "git init").next_state
        monkeypatch.setattr(client_command_execution, "MAX_REPOSITORY_STATE_BYTES", 10)
        execution = self.execute(
            initialized,
            "git status",
            diagnostic_payload("git status", initialized),
        )  # must not raise
        assert execution.result.processed

    def test_rejects_malformed_repository_state_before_normalization(self):
        payload = frontend_execution_payload("git status", {})
        with pytest.raises(BadRequest, match="repository_state must be an object"):
            ClientCommandExecutionService().from_payload(
                repository_state=[],
                command="git status",
                execution=payload,
            )

    def test_rejects_empty_list_next_state_instead_of_treating_it_as_missing(self):
        payload = frontend_execution_payload("git init", {}, processed=True, command_family="init")
        payload["next_state"] = []
        with pytest.raises(BadRequest, match="execution.next_state must be an object"):
            self.execute({}, "git init", payload)

    def test_rejects_malformed_next_state_before_verification(self):
        payload = frontend_execution_payload("git init", {}, processed=True, command_family="init")
        payload["next_state"] = {"commits": {}}
        with pytest.raises(BadRequest, match="execution.next_state.commits must be a list"):
            self.execute({}, "git init", payload)

    def test_rejects_mismatched_normalized_command(self):
        payload = frontend_execution_payload("git status", {})
        payload["normalized_command"] = "git commit"
        with pytest.raises(BadRequest):
            self.execute({}, "git status", payload)

    def test_rejects_processed_non_git_command(self):
        payload = frontend_execution_payload("echo hello", {}, processed=True)
        with pytest.raises(BadRequest):
            self.execute({}, "echo hello", payload)

    def test_diagnostic_payload_ignores_client_state_mutation(self):
        # A read-only command cannot change the repository, so the backend keeps
        # the previous state as authoritative instead of trusting the client's
        # next_state. A sneaked mutation is silently discarded, not rejected -
        # and, crucially, a client whose local snapshot legitimately drifted from
        # the stored state is no longer falsely rejected.
        initialized = self.execute({}, "git init").next_state
        mutated = {**initialized, "working_tree": {"x.txt": "changed"}}
        payload = diagnostic_payload("git status", mutated)
        execution = self.execute(initialized, "git status", payload)
        assert execution.state_mutated is False
        assert execution.next_state == execution.previous_state
        assert "x.txt" not in execution.next_state.get("working_tree", {})

    def test_unprocessed_payload_ignores_client_state_mutation(self):
        initialized = self.execute({}, "git init").next_state
        mutated = {**initialized, "working_tree": {"x.txt": "changed"}}
        payload = frontend_execution_payload(
            "git frobnicate", mutated, processed=False, exit_code=129
        )
        execution = self.execute(initialized, "git frobnicate", payload)
        assert execution.state_mutated is False
        assert execution.next_state == execution.previous_state
        assert "x.txt" not in execution.next_state.get("working_tree", {})

    def test_rejects_command_family_mismatch(self):
        payload = frontend_execution_payload("git status", {})
        payload["command_family"] = "commit"
        with pytest.raises(BadRequest):
            self.execute({}, "git status", payload)

    def test_accepts_matching_client_run_revision(self):
        payload = frontend_execution_payload(
            "git init", self.init_next_state(), client_run_revision=3
        )
        execution = ClientCommandExecutionService().from_payload(
            repository_state={},
            command="git init",
            execution=payload,
            expected_client_revision=3,
        )
        assert execution.result.client_run_revision == 3

    def test_rejects_stale_client_run_revision(self):
        payload = frontend_execution_payload(
            "git init", self.init_next_state(), client_run_revision=2
        )
        with pytest.raises(BadRequest):
            ClientCommandExecutionService().from_payload(
                repository_state={},
                command="git init",
                execution=payload,
                expected_client_revision=3,
            )

    def test_requires_client_run_revision_when_caller_supplies_expected_revision(self):
        payload = frontend_execution_payload("git init", self.init_next_state())
        with pytest.raises(BadRequest):
            ClientCommandExecutionService().from_payload(
                repository_state={},
                command="git init",
                execution=payload,
                expected_client_revision=0,
            )

    def test_rejects_forged_commit_graph_submitted_as_git_add(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "branches": {"main": None},
                "head": {"type": "branch", "name": "main"},
                "working_tree": {"README.md": {"status": "untracked", "content": "hello"}},
            }
        )
        forged = {
            **state,
            "commits": [
                {
                    "id": "c0",
                    "message": "forged",
                    "parents": [],
                    "tree": {"README.md": "hello"},
                    "changes": {
                        "README.md": {"change_type": "added", "before": None, "after": "hello"}
                    },
                    "files": {"README.md": "added"},
                }
            ],
            "branches": {"main": "c0"},
            "head": {"type": "branch", "name": "main", "target": "c0"},
            "working_tree": {},
        }
        with pytest.raises(BadRequest):
            self.execute(
                state, "git add README.md", frontend_execution_payload("git add README.md", forged)
            )

    def test_accepts_verified_git_add_transition(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "branches": {"main": None},
                "head": {"type": "branch", "name": "main"},
                "working_tree": {"README.md": {"status": "untracked", "content": "hello"}},
            }
        )
        next_state = {
            **state,
            "staging": {"README.md": {"status": "untracked", "content": "hello"}},
            "working_tree": {},
        }
        execution = self.execute(
            state, "git add README.md", frontend_execution_payload("git add README.md", next_state)
        )
        assert execution.next_state["staging"]["README.md"]["content"] == "hello"

    def test_accepts_verified_patch_add_with_structured_worktree_entry(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "branches": {"main": "c0"},
                "head": {"type": "branch", "name": "main", "target": "c0"},
                "commits": [
                    {
                        "id": "c0",
                        "message": "base",
                        "parents": [],
                        "tree": {"src/app.ts": "export const mode = 'base'\n"},
                    }
                ],
                "working_tree": {
                    "src/app.ts": {
                        "status": "modified",
                        "content": "export const mode = 'patched'\n",
                    }
                },
            }
        )
        next_state = {
            **state,
            "staging": {
                "src/app.ts": {
                    "status": "partial",
                    "hunks": ["modified export const mode = 'patched'\n"],
                }
            },
            "working_tree": {"src/app.ts": "modified"},
        }

        execution = self.execute(
            state,
            "git add -p src/app.ts",
            frontend_execution_payload("git add -p src/app.ts", next_state),
        )

        assert execution.next_state["staging"]["src/app.ts"]["hunks"] == [
            "modified export const mode = 'patched'\n"
        ]

    @pytest.mark.parametrize(
        ("mode", "expected_staging", "expected_working"),
        [
            (
                "soft",
                {"README.md": {"status": "modified", "content": "changed"}},
                {},
            ),
            (
                "mixed",
                {},
                {"README.md": {"status": "modified", "content": "changed"}},
            ),
            ("hard", {}, {}),
        ],
    )
    def test_accepts_verified_reset_with_pre_reset_snapshot_and_scoped_metadata_mirrors(
        self,
        mode,
        expected_staging,
        expected_working,
    ):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "branches": {"main": "c1"},
                "head": {"type": "branch", "name": "main", "target": "c1"},
                "commits": [
                    {
                        "id": "c0",
                        "message": "base",
                        "parents": [],
                        "tree": {"README.md": "base"},
                    },
                    {
                        "id": "c1",
                        "message": "changed",
                        "parents": ["c0"],
                        "tree": {"README.md": "changed"},
                    },
                ],
                "operation_metadata": {"bisect_good": "c0"},
            }
        )
        reset_metadata = {
            "last_reset_mode": mode,
            "last_reset_target": "c0",
            "last_reset_target_expr": "c0",
            "last_reset_previous_head": "c1",
        }
        next_state = copy.deepcopy(state)
        next_state["merge_abort_state"] = copy.deepcopy(state)
        next_state["branches"]["main"] = "c0"
        next_state["head"]["target"] = "c0"
        next_state["staging"] = expected_staging
        next_state["working_tree"] = expected_working
        next_state["operation_metadata"].update(reset_metadata)
        next_state.update(reset_metadata)
        next_state["reflog"] = [
            {"ref": "HEAD@{0}", "target": "c0", "message": "move HEAD"},
            {"ref": "HEAD@{1}", "target": "c0", "message": "reset: moving to c0"},
        ]

        execution = self.execute(
            state,
            f"git reset --{mode} c0",
            frontend_execution_payload(f"git reset --{mode} c0", next_state),
        )

        assert execution.next_state["merge_abort_state"] == state
        assert execution.next_state["operation_metadata"]["bisect_good"] == "c0"
        assert "bisect_good" not in execution.next_state

    def test_accepts_verified_simple_commit_transition(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "branches": {"main": None},
                "head": {"type": "branch", "name": "main"},
                "staging": {"README.md": {"status": "untracked", "content": "hello"}},
            }
        )
        next_state = {
            **state,
            "commits": [
                {
                    "id": "c0",
                    "message": "first",
                    "parents": [],
                    "tree": {"README.md": "hello"},
                    "changes": {
                        "README.md": {"change_type": "added", "before": None, "after": "hello"}
                    },
                    "files": {"README.md": "added"},
                    "author": "GIT it",
                    "order": 0,
                    "is_merge": False,
                }
            ],
            "branches": {"main": "c0"},
            "head": {"type": "branch", "name": "main", "target": "c0"},
            "staging": {},
            "reflog": [{"ref": "HEAD@{0}", "target": "c0", "message": "move HEAD"}],
        }
        execution = self.execute(
            state,
            "git commit -m first",
            frontend_execution_payload("git commit -m first", next_state),
        )
        assert execution.next_state["commits"][0]["id"] == "c0"

    def test_rejects_forged_simple_commit_tree(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "branches": {"main": None},
                "head": {"type": "branch", "name": "main"},
                "staging": {"README.md": {"status": "untracked", "content": "hello"}},
            }
        )
        forged = {
            **state,
            "commits": [
                {
                    "id": "c0",
                    "message": "first",
                    "parents": [],
                    "tree": {"README.md": "forged"},
                    "changes": {
                        "README.md": {"change_type": "added", "before": None, "after": "forged"}
                    },
                    "files": {"README.md": "added"},
                }
            ],
            "branches": {"main": "c0"},
            "head": {"type": "branch", "name": "main", "target": "c0"},
            "staging": {},
        }
        with pytest.raises(BadRequest):
            self.execute(
                state,
                "git commit -m first",
                frontend_execution_payload("git commit -m first", forged),
            )

    def test_rejects_failed_command_that_mutates_state(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {"working_tree": {"README.md": "hello"}}
        )
        mutated = {**state, "staging": {"README.md": "hello"}, "working_tree": {}}
        payload = frontend_execution_payload(
            "git commit -m nope", mutated, exit_code=1, output="nothing to commit"
        )
        with pytest.raises(BadRequest):
            self.execute(state, "git commit -m nope", payload)

    def test_accepts_verified_checkout_ours_conflict_resolution(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "branches": {"main": "c0"},
                "head": {"type": "branch", "name": "main", "target": "c0"},
                "commits": [
                    {"id": "c0", "message": "base", "parents": [], "tree": {"app.txt": "base"}}
                ],
                "conflicts": ["app.txt"],
                "conflict_details": {
                    "app.txt": {"ours": "ours", "theirs": "theirs", "base": "base"}
                },
                "working_tree": {"app.txt": {"status": "conflicted", "content": "<<<<<<<"}},
            }
        )
        next_state = {
            **state,
            "working_tree": {
                "app.txt": {"status": "modified", "content": "ours", "resolution_side": "ours"}
            },
        }
        execution = self.execute(
            state,
            "git checkout --ours app.txt",
            frontend_execution_payload("git checkout --ours app.txt", next_state),
        )
        assert execution.next_state["working_tree"]["app.txt"]["content"] == "ours"

    def test_accepts_verified_tag_creation(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "branches": {"main": "c0"},
                "head": {"type": "branch", "name": "main", "target": "c0"},
                "commits": [
                    {"id": "c0", "message": "base", "parents": [], "tree": {"README.md": "hello"}}
                ],
            }
        )
        next_state = {
            **state,
            "tags": {"v1.0": {"target": "c0", "annotated": True, "message": "release"}},
        }
        execution = self.execute(
            state,
            "git tag -a v1.0 -m release",
            frontend_execution_payload("git tag -a v1.0 -m release", next_state),
        )
        assert execution.next_state["tags"]["v1.0"]["target"] == "c0"

    def test_rejects_tag_that_moves_branch(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "branches": {"main": "c0"},
                "head": {"type": "branch", "name": "main", "target": "c0"},
                "commits": [
                    {"id": "c0", "message": "base", "parents": [], "tree": {"README.md": "hello"}}
                ],
            }
        )
        forged = {
            **state,
            "branches": {"main": None},
            "tags": {"v1.0": {"target": "c0", "annotated": False, "message": ""}},
        }
        with pytest.raises(BadRequest):
            self.execute(state, "git tag v1.0", frontend_execution_payload("git tag v1.0", forged))

    def test_accepts_verified_remote_add(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "branches": {"main": "c0"},
                "head": {"type": "branch", "name": "main", "target": "c0"},
                "commits": [{"id": "c0", "message": "base", "parents": [], "tree": {}}],
            }
        )
        next_state = {**state, "remotes": {"origin": "https://example.test/repo.git"}}
        execution = self.execute(
            state,
            "git remote add origin https://example.test/repo.git",
            frontend_execution_payload(
                "git remote add origin https://example.test/repo.git", next_state
            ),
        )
        assert execution.next_state["remotes"]["origin"] == "https://example.test/repo.git"

    def test_accepts_verified_push_with_upstream(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "branches": {"main": "c0"},
                "head": {"type": "branch", "name": "main", "target": "c0"},
                "commits": [{"id": "c0", "message": "base", "parents": [], "tree": {}}],
                "remotes": {"origin": "https://example.test/repo.git"},
            }
        )
        next_state = {
            **state,
            "remote_branches": {"origin/main": "c0"},
            "upstream_tracking": {"main": "origin/main"},
        }
        execution = self.execute(
            state,
            "git push -u origin main",
            frontend_execution_payload("git push -u origin main", next_state),
        )
        assert execution.next_state["upstream_tracking"]["main"] == "origin/main"

    def test_accepts_verified_stash_push_with_message(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "branches": {"main": "c0"},
                "head": {"type": "branch", "name": "main", "target": "c0"},
                "commits": [
                    {"id": "c0", "message": "base", "parents": [], "tree": {"README.md": "base"}}
                ],
                "staging": {"README.md": {"status": "modified", "content": "staged"}},
                "working_tree": {
                    "README.md": {"status": "modified", "content": "work"},
                    "notes.txt": {"status": "untracked", "content": "draft"},
                },
            }
        )
        next_state = {
            **state,
            "stash_stack": [
                {
                    "working_tree": {"README.md": {"status": "modified", "content": "work"}},
                    "staging": {"README.md": {"status": "modified", "content": "staged"}},
                    "conflicts": [],
                    "message": "wip",
                }
            ],
            "staging": {},
            "working_tree": {"notes.txt": {"status": "untracked", "content": "draft"}},
            "conflicts": [],
            "operation_metadata": {
                **state.get("operation_metadata", {}),
                "last_stash_action": "push",
                "last_stash_operation": "push",
                "stash_count": 1,
            },
            "last_stash_action": "push",
            "last_stash_operation": "push",
            "stash_count": 1,
        }
        execution = self.execute(
            state,
            "git stash push -m wip",
            frontend_execution_payload("git stash push -m wip", next_state),
        )
        assert len(execution.next_state["stash_stack"]) == 1

    def test_accepts_verified_fast_forward_merge(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "branches": {"main": "c0", "feature": "c1"},
                "head": {"type": "branch", "name": "main", "target": "c0"},
                "commits": [
                    {"id": "c0", "message": "base", "parents": [], "tree": {"README.md": "base"}},
                    {
                        "id": "c1",
                        "message": "feature",
                        "parents": ["c0"],
                        "tree": {"README.md": "feature"},
                    },
                ],
            }
        )
        next_state = {
            **state,
            "branches": {"main": "c1", "feature": "c1"},
            "head": {"type": "branch", "name": "main", "target": "c1"},
            "reflog": [{"ref": "HEAD@{0}", "target": "c1", "message": "move HEAD"}],
            "operation_metadata": {
                **state.get("operation_metadata", {}),
                "last_merge_branch": "feature",
                "last_merge_target": "c1",
                "last_merge_fast_forward": True,
            },
            "last_merge_branch": "feature",
            "last_merge_target": "c1",
            "last_merge_fast_forward": True,
        }
        execution = self.execute(
            state,
            "git merge feature",
            frontend_execution_payload("git merge feature", next_state),
        )
        assert execution.next_state["branches"]["main"] == "c1"

    def test_accepts_verified_squash_merge_with_scoped_metadata_mirrors(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "branches": {"main": "c0", "feature": "c1"},
                "head": {"type": "branch", "name": "main", "target": "c0"},
                "commits": [
                    {
                        "id": "c0",
                        "message": "base",
                        "parents": [],
                        "tree": {"README.md": "base"},
                    },
                    {
                        "id": "c1",
                        "message": "feature",
                        "parents": ["c0"],
                        "tree": {"README.md": "feature"},
                    },
                ],
                "operation_metadata": {"bisect_good": "c0"},
            }
        )
        next_state = copy.deepcopy(state)
        next_state["staging"] = {"README.md": {"status": "modified", "content": "feature"}}
        squash_metadata = {
            "last_merge_branch": "feature",
            "last_merge_target": "c1",
            "squash_merge_staged": True,
        }
        next_state["operation_metadata"].update(squash_metadata)
        next_state.update(squash_metadata)

        execution = self.execute(
            state,
            "git merge --squash feature",
            frontend_execution_payload("git merge --squash feature", next_state),
        )

        assert execution.next_state["head"] == state["head"]
        assert execution.next_state["branches"] == state["branches"]
        assert execution.next_state["commits"] == state["commits"]
        assert execution.next_state["operation_metadata"]["bisect_good"] == "c0"
        assert "bisect_good" not in execution.next_state

    def test_accepts_verified_commit_all_transition(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "branches": {"main": "c0"},
                "head": {"type": "branch", "name": "main", "target": "c0"},
                "commits": [
                    {"id": "c0", "message": "base", "parents": [], "tree": {"README.md": "base"}}
                ],
                "working_tree": {"README.md": {"status": "modified", "content": "changed"}},
            }
        )
        next_state = {
            **state,
            "commits": [
                *state["commits"],
                {
                    "id": "c1",
                    "message": "update",
                    "parents": ["c0"],
                    "tree": {"README.md": "changed"},
                    "changes": {
                        "README.md": {
                            "change_type": "modified",
                            "before": "base",
                            "after": "changed",
                        }
                    },
                    "files": {"README.md": "modified"},
                    "author": "GIT it",
                    "order": 1,
                    "is_merge": False,
                },
            ],
            "branches": {"main": "c1"},
            "head": {"type": "branch", "name": "main", "target": "c1"},
            "staging": {},
            "working_tree": {},
            "reflog": [{"ref": "HEAD@{0}", "target": "c1", "message": "move HEAD"}],
        }
        execution = self.execute(
            state,
            "git commit -a -m update",
            frontend_execution_payload("git commit -a -m update", next_state),
        )
        assert execution.next_state["branches"]["main"] == "c1"

    def test_accepts_verified_commit_amend_transition(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "branches": {"main": "c0"},
                "head": {"type": "branch", "name": "main", "target": "c0"},
                "commits": [
                    {"id": "c0", "message": "base", "parents": [], "tree": {"README.md": "base"}}
                ],
                "staging": {"README.md": {"status": "modified", "content": "amended"}},
            }
        )
        next_state = {
            **state,
            "commits": [
                *state["commits"],
                {
                    "id": "c1",
                    "message": "better",
                    "parents": [],
                    "tree": {"README.md": "amended"},
                    "changes": {
                        "README.md": {"change_type": "added", "before": None, "after": "amended"}
                    },
                    "files": {"README.md": "added"},
                    "author": "GIT it",
                    "order": 1,
                    "is_merge": False,
                },
            ],
            "branches": {"main": "c1"},
            "head": {"type": "branch", "name": "main", "target": "c1"},
            "staging": {},
            "replaced_commits": {"c0": "c1"},
            "operation_metadata": {
                **state.get("operation_metadata", {}),
                "last_amend_replaced_commit": "c0",
                "last_amend_created_commit": "c1",
            },
            "last_amend_replaced_commit": "c0",
            "last_amend_created_commit": "c1",
            "reflog": [
                {"ref": "HEAD@{0}", "target": "c1", "message": "move HEAD"},
                {"ref": "HEAD@{1}", "target": "c1", "message": "commit --amend: replaced c0"},
            ],
        }
        execution = self.execute(
            state,
            "git commit --amend -m better",
            frontend_execution_payload("git commit --amend -m better", next_state),
        )
        assert execution.next_state["replaced_commits"] == {"c0": "c1"}

    def test_accepts_verified_fetch_transition(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "branches": {"main": "c0"},
                "head": {"type": "branch", "name": "main", "target": "c0"},
                "commits": [
                    {"id": "c0", "message": "base", "parents": [], "tree": {"README.md": "base"}}
                ],
                "remotes": {"origin": "https://example.test/repo.git"},
                "remote_fixtures": {
                    "branches": {"origin/main": "c1"},
                    "commits": [
                        {
                            "id": "c1",
                            "message": "remote",
                            "parents": ["c0"],
                            "tree": {"README.md": "remote"},
                        }
                    ],
                },
            }
        )
        next_state = ClientCommandExecutionService().transition_verifier._expected_fetch_state(
            command="git fetch origin",
            previous_state=state,
        )
        execution = self.execute(
            state,
            "git fetch origin",
            frontend_execution_payload("git fetch origin", next_state),
        )
        assert execution.next_state["remote_branches"]["origin/main"] == "c1"

    def test_rejects_fetch_that_moves_local_branch(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "branches": {"main": "c0"},
                "head": {"type": "branch", "name": "main", "target": "c0"},
                "commits": [{"id": "c0", "message": "base", "parents": [], "tree": {}}],
                "remotes": {"origin": "https://example.test/repo.git"},
                "remote_updates": {"origin/main": "c0"},
            }
        )
        forged = {**state, "branches": {"main": None}, "remote_branches": {"origin/main": "c0"}}
        with pytest.raises(BadRequest):
            self.execute(
                state, "git fetch origin", frontend_execution_payload("git fetch origin", forged)
            )

    def test_accepts_verified_clone_transition(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "repository_initialized": False,
                "remote_fixtures": {
                    "branches": {"origin/main": "r1"},
                    "commits": [
                        {
                            "id": "r1",
                            "message": "remote",
                            "parents": [],
                            "tree": {"README.md": "remote"},
                        }
                    ],
                },
            }
        )
        verifier = ClientCommandExecutionService().transition_verifier
        next_state = {**state}
        next_state["repository_initialized"] = True
        next_state["remotes"] = {"origin": "https://example.test/repo.git"}
        next_state["remote_branches"] = {"origin/main": "r1"}
        next_state["commits"] = [
            {"id": "r1", "message": "remote", "parents": [], "tree": {"README.md": "remote"}}
        ]
        next_state["branches"] = {"main": "r1"}
        next_state["head"] = {"type": "branch", "name": "main", "target": "r1"}
        next_state["upstream_tracking"] = {"main": "origin/main"}
        next_state["staging"] = {}
        next_state["working_tree"] = {}
        next_state["conflicts"] = []
        verifier._set_operation_metadata(
            next_state,
            {
                "last_clone_url": "https://example.test/repo.git",
                "last_clone_directory": "repo",
                "last_clone_destination": "repo",
                "last_clone_branch": "main",
                "last_clone_depth": None,
                "last_clone_shallow": False,
            },
        )
        execution = self.execute(
            state,
            "git clone https://example.test/repo.git",
            frontend_execution_payload("git clone https://example.test/repo.git", next_state),
        )
        assert execution.next_state["branches"]["main"] == "r1"

    def test_accepts_verified_rebase_transition(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {
                "branches": {"main": "c1", "base": "c2"},
                "head": {"type": "branch", "name": "main", "target": "c1"},
                "commits": [
                    {"id": "c0", "message": "base", "parents": [], "tree": {"app.txt": "base"}},
                    {
                        "id": "c1",
                        "message": "local",
                        "parents": ["c0"],
                        "tree": {"app.txt": "local"},
                        "changes": {
                            "app.txt": {
                                "change_type": "modified",
                                "before": "base",
                                "after": "local",
                            }
                        },
                    },
                    {
                        "id": "c2",
                        "message": "upstream",
                        "parents": ["c0"],
                        "tree": {"app.txt": "upstream"},
                        "changes": {
                            "app.txt": {
                                "change_type": "modified",
                                "before": "base",
                                "after": "upstream",
                            }
                        },
                    },
                ],
            }
        )
        verifier = ClientCommandExecutionService().transition_verifier
        next_state = verifier.tools.clone_state(state)
        applied = verifier._replay_linear_commits(next_state, "c1", "c0", "c2")
        verifier._set_operation_metadata(
            next_state,
            {
                "last_rebase_target": "base",
                "last_rebase_onto": None,
                "last_rebase_upstream": "c2",
                "last_rebase_new_head": "c3",
                "last_rebase_interactive": False,
                "last_rebase_replayed_commits": applied,
            },
        )
        execution = self.execute(
            state,
            "git rebase base",
            frontend_execution_payload("git rebase base", next_state),
        )
        assert execution.next_state["branches"]["main"] == "c3"

    def test_accepts_mutating_transition_computed_from_response_snapshot(self):
        # The browser never holds the raw stored state: every response passes
        # through RepositorySnapshotService, which fills default-empty keys
        # (config, merge_*, rebase_state, ...) the stored initial_state omits.
        # The client's next_state is a mutation of THAT filled copy, so the
        # boundary must not read the filled defaults as forged changes. This
        # used to reject every first mutating command of a fresh run with
        # "execution.next_state cannot change config for this command."
        from simulator.services import RepositorySnapshotService

        stored = {
            "repository_initialized": True,
            "commits": [
                {"id": "c0", "message": "Initial", "parents": [], "tree": {"README.md": "notes"}}
            ],
            "branches": {"main": "c0"},
            "head": {"type": "branch", "name": "main"},
            "working_tree": {"README.md": {"status": "modified", "content": "notes v2"}},
            "staging": {},
            "conflicts": [],
        }
        client_copy = RepositorySnapshotService().snapshot(stored)
        next_state = {
            **client_copy,
            "staging": {"README.md": client_copy["working_tree"]["README.md"]},
            "working_tree": {},
        }
        execution = self.execute(
            stored,
            "git add .",
            frontend_execution_payload("git add .", next_state),
        )
        assert execution.state_mutated
        assert execution.next_state["staging"]["README.md"]["content"] == "notes v2"

    def test_rejects_unknown_mutating_family_even_if_git_shaped(self):
        state = ClientCommandExecutionService().state_tools.normalize_state(
            {"working_tree": {"x.txt": "x"}}
        )
        payload = frontend_execution_payload(
            "git frobnicate", state, processed=True, command_family="frobnicate"
        )
        with pytest.raises(BadRequest):
            self.execute(state, "git frobnicate", payload)
