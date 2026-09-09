"""Cheap backend-side verification for client-submitted Git transitions.

The browser simulator still owns instant UI feedback. This verifier mirrors the
supported mutating command transitions that can affect persisted progress/rewards
without shelling out to Git, so a forged client next_state cannot silently earn
completion.
"""

from __future__ import annotations

import copy

from common.exceptions import BadRequest
from simulator.services import parse_git_command


class InitCloneRemoteVerificationMixin:
    def _verify_init(self, *, command: str, previous_state: dict, next_state: dict) -> None:
        parts = parse_git_command(command) or []
        branch = (
            self._option_value(parts, "-b", "--initial-branch")
            or self._head_branch(previous_state)
            or "main"
        )
        args = self._pathspecs(parts, value_options={"-b", "--initial-branch"})
        directory = args[0] if args else None
        quiet = "-q" in parts or "--quiet" in parts
        reinitialized = bool(previous_state.get("repository_initialized"))
        expected = copy.deepcopy(previous_state)
        expected["repository_initialized"] = True
        expected["head"] = {
            "type": "branch",
            "name": branch,
            "target": (expected.get("branches") or {}).get(branch),
        }
        expected.setdefault("branches", {})
        expected["branches"].setdefault(branch, None)
        if not reinitialized:
            # Match the browser simulator: Git metadata starts empty, while
            # existing workspace files remain available to stage later.
            expected["commits"] = []
            expected["staging"] = {}
            expected["conflicts"] = []
            expected["remotes"] = {}
            expected["remote_branches"] = {}
            expected["upstream_tracking"] = {}
        self._set_operation_metadata(
            expected,
            {
                "last_init_branch": branch,
                "last_init_initial_branch": branch,
                "last_init_directory": directory,
                "last_init_current_directory": directory is None,
                "last_init_quiet": quiet,
                "last_init_reinitialized": reinitialized,
                "repository_reinitialized": reinitialized,
            },
        )
        expected = self.tools.normalize_state(expected)
        self._require_equivalent_expected(expected, next_state, "git init")

    def _verify_clone(self, *, command: str, previous_state: dict, next_state: dict) -> None:
        parts = parse_git_command(command) or []
        args = self._pathspecs(parts, value_options={"-b", "--branch", "--depth"})
        if previous_state.get("repository_initialized"):
            raise BadRequest("execution.next_state does not match the submitted git clone command.")
        if not args:
            raise BadRequest("execution.next_state does not match the submitted git clone command.")

        url = args[0]
        directory = args[1] if len(args) > 1 else self._default_clone_directory(url)
        remote_name = "origin"
        expected = copy.deepcopy(previous_state)
        expected["repository_initialized"] = True
        expected["remotes"] = {remote_name: url}
        expected["remote_branches"] = {}
        self._apply_remote_fixture_branches(expected)
        self._materialize_remote_commits(expected)

        branch_value = self._option_value(parts, "-b", "--branch") or ""
        default_remote_branch = self._default_remote_branch_for(expected, remote_name)
        selected_remote_branch = (
            f"{remote_name}/{branch_value}" if branch_value else default_remote_branch
        )
        if selected_remote_branch not in (expected.get("remote_branches") or {}):
            raise BadRequest("execution.next_state does not match the submitted git clone command.")
        selected_target = (expected.get("remote_branches") or {}).get(selected_remote_branch)
        selected_branch = "/".join(selected_remote_branch.split("/")[1:]) or "main"
        expected["branches"] = {selected_branch: selected_target}
        expected["head"] = {"type": "branch", "name": selected_branch, "target": selected_target}
        expected["upstream_tracking"] = {selected_branch: selected_remote_branch}
        expected["staging"] = {}
        expected["working_tree"] = {}
        expected["conflicts"] = []
        depth_raw = self._option_value(parts, "--depth")
        depth = (
            int(depth_raw)
            if depth_raw and str(depth_raw).isdigit() and int(depth_raw) > 0
            else None
        )
        if depth and selected_target:
            self._truncate_shallow(expected, selected_target, depth)
        self._set_operation_metadata(
            expected,
            {
                "last_clone_url": url,
                "last_clone_directory": directory,
                "last_clone_destination": directory,
                "last_clone_branch": selected_branch,
                "last_clone_depth": depth,
                "last_clone_shallow": depth is not None,
            },
        )
        expected = self.tools.normalize_state(expected)
        self._require_equivalent_expected(expected, next_state, "git clone")

    def _verify_remote(self, *, command: str, previous_state: dict, next_state: dict) -> None:
        for key in {
            "repository_initialized",
            "commits",
            "branches",
            "head",
            "staging",
            "working_tree",
            "conflicts",
            "conflict_details",
            "partial_hunks",
            "remote_branches",
            "upstream_tracking",
            "tags",
            "remote_tags",
            "stash_stack",
            "reflog",
            "replaced_commits",
            "config",
        }:
            self._require_same_key(key, previous_state, next_state)
        parts = parse_git_command(command) or []
        args = self._pathspecs(parts)
        if not args:
            self._require_same_state(
                previous_state,
                next_state,
                "git remote without arguments cannot mutate repository state.",
            )
            return
        expected = copy.deepcopy(previous_state.get("remotes") or {})
        if args[0] == "add" and len(args) >= 3:
            expected[args[1]] = args[2]
        elif args[0] == "set-url" and len(args) >= 3:
            if args[1] not in expected:
                raise BadRequest(
                    "execution.next_state does not match the submitted git remote command."
                )
            expected[args[1]] = args[2]
        else:
            raise BadRequest(
                "execution.next_state does not match the submitted git remote command."
            )
        if next_state.get("remotes") != expected:
            raise BadRequest(
                "execution.next_state does not match the submitted git remote command."
            )

    def _verify_fetch(self, *, command: str, previous_state: dict, next_state: dict) -> None:
        expected = self._expected_fetch_state(command=command, previous_state=previous_state)
        expected = self.tools.normalize_state(expected)
        self._require_equivalent_expected(expected, next_state, "git fetch")

    def _verify_pull(self, *, command: str, previous_state: dict, next_state: dict) -> None:
        parts = parse_git_command(command) or []
        args = self._pathspecs(parts)
        remote = args[0] if args else "origin"
        branch = args[1] if len(args) > 1 else self._head_branch(previous_state) or "main"
        expected = self._expected_fetch_state(
            command=f"git fetch {remote}", previous_state=previous_state
        )
        remote_key = f"{remote}/{branch}"
        remote_commit = (expected.get("remote_branches") or {}).get(remote_key)
        if not remote_commit:
            raise BadRequest("execution.next_state does not match the submitted git pull command.")
        self._set_operation_metadata(expected, {"remote_tracking_updated": True})
        current = self.normalizer.head_commit_id(expected)
        if "--ff-only" in parts:
            if current == remote_commit or self._is_ancestor(expected, current, remote_commit):
                self._set_head_commit(expected, remote_commit)
                self._set_operation_metadata(
                    expected, {"pull_strategy": "ff-only", "pull_fast_forwarded": True}
                )
                expected = self.tools.normalize_state(expected)
                self._require_equivalent_expected(expected, next_state, "git pull")
                return
            self._require_same_state(
                previous_state,
                next_state,
                "failed git pull --ff-only cannot mutate repository state.",
            )
            return
        if "--rebase" in parts:
            current_branch = self._head_branch(expected)
            if not current_branch:
                raise BadRequest(
                    "execution.next_state does not match the submitted git pull command."
                )
            if current == remote_commit or self._is_ancestor(expected, current, remote_commit):
                self._set_head_commit(expected, remote_commit)
                self._set_operation_metadata(
                    expected, {"pull_strategy": "rebase", "pull_rebased_onto": remote_commit}
                )
            else:
                applied = self._replay_linear_commits(
                    expected,
                    current,
                    self._common_ancestor(expected, current, remote_commit),
                    remote_commit,
                )
                self._set_operation_metadata(
                    expected,
                    {
                        "pull_strategy": "rebase",
                        "pull_rebased_onto": remote_commit,
                        "last_rebase_replayed_commits": applied,
                    },
                )
            expected = self.tools.normalize_state(expected)
            self._require_equivalent_expected(expected, next_state, "git pull")
            return

        expected = self._expected_merge_state(
            command=f"git merge {remote_key}", previous_state=expected
        )
        expected = self.tools.normalize_state(expected)
        self._require_equivalent_expected(expected, next_state, "git pull")

    def _verify_push(self, *, command: str, previous_state: dict, next_state: dict) -> None:
        for key in {
            "commits",
            "branches",
            "head",
            "staging",
            "working_tree",
            "conflicts",
            "conflict_details",
            "partial_hunks",
            "stash_stack",
            "replaced_commits",
            "config",
        }:
            self._require_same_key(key, previous_state, next_state)
        parts = parse_git_command(command) or []
        args = self._pathspecs(parts)
        remote = args[0] if args else "origin"
        expected_remotes = copy.deepcopy(previous_state.get("remotes") or {})
        expected_remote_branches = copy.deepcopy(previous_state.get("remote_branches") or {})
        expected_upstream = copy.deepcopy(previous_state.get("upstream_tracking") or {})
        expected_remote_tags = copy.deepcopy(previous_state.get("remote_tags") or {})

        if "--tags" in parts:
            expected_remote_tags = copy.deepcopy(previous_state.get("tags") or {})
        elif "--delete" in parts or "-d" in parts:
            branch = args[1] if len(args) > 1 else ""
            remote_key = f"{remote}/{branch}"
            if remote_key not in expected_remote_branches:
                raise BadRequest(
                    "execution.next_state does not match the submitted git push command."
                )
            expected_remote_branches.pop(remote_key, None)
            expected_upstream = {
                key: value for key, value in expected_upstream.items() if value != remote_key
            }
        else:
            branch = args[1] if len(args) > 1 else self._head_branch(previous_state)
            if not branch:
                raise BadRequest(
                    "execution.next_state does not match the submitted git push command."
                )
            commit_id = (previous_state.get("branches") or {}).get(branch)
            remote_key = f"{remote}/{branch}"
            expected_remote_branches[remote_key] = commit_id
            expected_remotes.setdefault(remote, f"https://example.test/{remote}.git")
            if "-u" in parts or "--set-upstream" in parts:
                expected_upstream[branch] = remote_key

        if next_state.get("remotes") != expected_remotes:
            raise BadRequest("execution.next_state does not match the submitted git push command.")
        if next_state.get("remote_branches") != expected_remote_branches:
            raise BadRequest("execution.next_state does not match the submitted git push command.")
        if next_state.get("upstream_tracking") != expected_upstream:
            raise BadRequest("execution.next_state does not match the submitted git push command.")
        if next_state.get("remote_tags") != expected_remote_tags:
            raise BadRequest("execution.next_state does not match the submitted git push command.")

    def _expected_fetch_state(self, *, command: str, previous_state: dict) -> dict:
        parts = parse_git_command(command) or []
        args = self._pathspecs(parts)
        all_remotes = "--all" in parts
        remote = args[0] if args else "origin"
        if (
            not all_remotes
            and remote not in (previous_state.get("remotes") or {})
            and not previous_state.get("remote_fixtures")
            and not previous_state.get("remote_updates")
        ):
            raise BadRequest("execution.next_state does not match the submitted git fetch command.")
        expected = copy.deepcopy(previous_state)
        expected.setdefault("remotes", {})
        if expected.get("remote_updates"):
            expected.setdefault("remote_branches", {}).update(
                copy.deepcopy(expected.get("remote_updates") or {})
            )
        self._apply_remote_fixture_branches(expected)
        self._materialize_remote_commits(expected)
        pruned: list[str] = []
        if "--prune" in parts or "-p" in parts:
            stale = {
                str(name) if "/" in str(name) else f"{remote}/{name}"
                for name in (expected.get("remote_stale_branches") or [])
            }
            remote_branches = expected.setdefault("remote_branches", {})
            for branch in list(remote_branches):
                if branch.startswith(f"{remote}/") and (
                    remote_branches.get(branch) is None or branch in stale
                ):
                    remote_branches.pop(branch, None)
                    pruned.append(branch)
        self._set_operation_metadata(
            expected,
            {
                "remote_tracking_updated": True,
                "last_fetch_remote": "--all" if all_remotes else remote,
                "last_fetch_all": all_remotes,
                "fetch_pruned_refs": pruned if pruned else None,
            },
        )
        return expected

    def _apply_remote_fixture_branches(self, state: dict) -> None:
        fixture = (
            state.get("remote_fixtures") if isinstance(state.get("remote_fixtures"), dict) else {}
        )
        state.setdefault("remote_branches", {})
        branch_targets: dict[str, str | None] = {}
        branches = fixture.get("branches") if isinstance(fixture.get("branches"), dict) else {}
        branch_targets.update(
            {
                str(key): (str(value) if value is not None else None)
                for key, value in branches.items()
            }
        )
        for key, value in fixture.items():
            if key in {"commits", "branches", "remote_head", "head", "default_branch"}:
                continue
            if "/" in str(key) and value:
                branch_targets[str(key)] = str(value)
        remote_head = fixture.get("remote_head") or fixture.get("head")
        default_branch = str(fixture.get("default_branch") or "origin/main")
        if remote_head:
            branch_targets.setdefault(default_branch, str(remote_head))
        for branch, target in branch_targets.items():
            state["remote_branches"][branch] = target

    def _materialize_remote_commits(self, state: dict) -> None:
        state.setdefault("commits", [])
        existing = {commit.get("id") for commit in state.get("commits", [])}
        fixture = (
            state.get("remote_fixtures") if isinstance(state.get("remote_fixtures"), dict) else {}
        )
        fixture_commits = fixture.get("commits") if isinstance(fixture.get("commits"), list) else []
        for authored in fixture_commits:
            if not isinstance(authored, dict) or not authored.get("id"):
                continue
            commit_id = str(authored.get("id"))
            existing_commit = self.normalizer.commit_by_id(state, commit_id)
            if existing_commit:
                existing_commit.update(copy.deepcopy(authored))
            else:
                state["commits"].append(copy.deepcopy(authored))
                existing.add(commit_id)
        self.normalizer.normalize_commits(state)
        remote_ids = sorted(
            {target for target in (state.get("remote_branches") or {}).values() if target}
        )
        previous: str | None = None
        for commit_id in remote_ids:
            if commit_id not in existing:
                state["commits"].append(
                    {
                        "id": commit_id,
                        "message": f"Remote commit {commit_id}",
                        "parents": [previous] if previous else [],
                        "tree": {},
                        "changes": {},
                        "files": {},
                        "is_merge": False,
                    }
                )
                existing.add(commit_id)
            previous = commit_id
        self.normalizer.normalize_commits(state)

    def _default_remote_branch_for(self, state: dict, remote: str) -> str:
        fixture = (
            state.get("remote_fixtures") if isinstance(state.get("remote_fixtures"), dict) else {}
        )
        default_name = str(fixture.get("default_branch") or f"{remote}/main")
        if default_name in (state.get("remote_branches") or {}):
            return default_name
        main_ref = f"{remote}/main"
        if main_ref in (state.get("remote_branches") or {}):
            return main_ref
        return (
            sorted(state.get("remote_branches") or {})[0]
            if (state.get("remote_branches") or {})
            else main_ref
        )

    def _default_clone_directory(self, url: str) -> str:
        tail = next((part for part in reversed(url.split("/")) if part), "repository")
        return tail.removesuffix(".git") or "repository"

    def _truncate_shallow(self, state: dict, tip: str | None, depth: int) -> None:
        kept: list[str] = []
        current = tip
        while current and len(kept) < depth:
            kept.append(current)
            commit = self.normalizer.commit_by_id(state, current)
            current = (commit.get("parents") or [None])[0] if commit else None
        kept_set = set(kept)
        state["commits"] = [
            commit for commit in (state.get("commits") or []) if commit.get("id") in kept_set
        ]
        oldest = self.normalizer.commit_by_id(state, kept[-1] if kept else None)
        if oldest:
            oldest["parents"] = []
