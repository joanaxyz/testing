"""Seed the archived Module 0-4 content into the new Story/Chapter/Adventure schema.

Source of truth for every literal below is the archived branch
``archive/may30-old-modules`` (read via ``git show``), specifically:
  - backend/learning/management/commands/seed_module0_orientation.py
  - backend/learning/management/commands/seed_module1_scenarios.py
  - backend/learning/management/commands/seed_module2_scenarios.py
  - backend/learning/management/commands/seed_module3_scenarios.py
  - backend/learning/management/commands/seed_module4_scenarios.py

This is a one-shot legacy-import command, kept fully separate from
seed_curriculum.py: it never touches the arcane-spire/frostbound-citadel/
neon-backstreets Story or Chapter rows, and it is not wired into
seed_curriculum's mixins. Re-running it is idempotent (update_or_create
throughout), matching the archived commands' own convention.

Two content shapes are ported:
  - Module 0 (orientation): 8 ChapterOrientationLesson rows carrying the old
    Lesson.content_html/scoped_css/interaction_steps verbatim. Independent of
    ChapterLesson/the book system, per the approved plan.
  - Modules 1-4: one AdventureLevel per old lesson anchor. A level with old
    difficulty content gets three AdventureLevelTier rows (easy/medium/hard),
    each with exactly one AdventureLevelTierWave (the old system tracked
    required *successful attempts* of a single repeatable exercise, not a
    sequence of distinct waves - see AdventureLevelTierWave.required_successful_attempts).
    Each old ScenarioVariant becomes one AdventureLevelTierWaveVariant under
    that wave. A level with no old difficulty content (Module 1's
    "Inspecting Repository State") is seeded with zero AdventureLevelTier
    rows - the existing single-Play-pill frontend path already handles that
    correctly with no special-casing.

The old target_rule (declarative pass/fail conditions) is ported into
evaluation_spec.state_requirements, matching how the current, already-working
arcane-spire content encodes rule-based validation (see
curriculum/seed_data/spec_helpers.py:ev()). target_state is intentionally left
empty ({}): the working new-system content computes it with a separate
generate_targets pipeline (replaying solution_commands against initial_state),
which is out of scope for this data port.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from adventures.models import (
    AdventureLevel,
    AdventureLevelTier,
    AdventureLevelTierWave,
    AdventureLevelTierWaveVariant,
)
from curriculum.models import (
    Chapter,
    ChapterOrientationLesson,
    Story,
)

LEGACY_STORY_SLUG = "git-it-legacy"

DIFFICULTY_MAX_COUNTED_COMMANDS = {"easy": 12, "medium": 10, "hard": 8}


def ev(state_requirements: dict | None = None, *, required: list[str] | None = None) -> dict:
    """Mirror curriculum/seed_data/spec_helpers.py:ev() - the shape the current,
    working rule-based (non-snapshot) content already uses for evaluation_spec."""
    return {
        "state_requirements": state_requirements or {},
        "process_requirements": {"required_commands": required or [], "forbidden_commands": []},
        "completion_policy": {"mode": "rules"},
    }


# ---------------------------------------------------------------------------
# Story + Chapter scaffold
# ---------------------------------------------------------------------------

STORY_SPEC = {
    "slug": LEGACY_STORY_SLUG,
    "title": "GIT it! Legacy Modules",
    "summary": (
        "The original Module 0-4 curriculum, restored as its own campaign. "
        "Placeholder art and theme - real world assets land separately."
    ),
    "price": 0,
    "sort_order": 100,
    "is_published": True,
    "world_slug": "legacy-modules-placeholder",
    "difficulty": Story.DIFFICULTY_BEGINNER,
}

# (number, slug, title, description, is_orientation) - titles/descriptions are
# the archived branch's LearningUnit.title/description verbatim.
CHAPTER_SPECS: list[dict[str, Any]] = [
    {
        "number": 0,
        "slug": "module-0-orientation",
        "title": "Module 0",
        "description": (
            "Build your Git mental model and platform familiarity before scenario "
            "practice. Eight guided lessons — recommended before Modules 1–4."
        ),
        "is_orientation": True,
    },
    {
        "number": 1,
        "slug": "module-1-local-repository-foundations",
        "title": "Module 1",
        "description": (
            "Initialize, clone, stage, commit, ignore, partially stage, amend, "
            "clean up, and inspect local Git repositories through scenario practice."
        ),
        "is_orientation": False,
    },
    {
        "number": 2,
        "slug": "module-2-branching-and-collaboration",
        "title": "Module 2",
        "description": (
            "Create, switch, and delete branches; stash work in progress; push "
            "and pull with remotes; merge, squash-merge, and reconcile diverged "
            "histories through scenario practice."
        ),
        "is_orientation": False,
    },
    {
        "number": 3,
        "slug": "module-3-conflict-resolution",
        "title": "Module 3",
        "description": (
            "Practice conflict diagnostics, manual resolution, mergetool "
            "workflows, prevention checks, cherry-picking, and integrated recovery."
        ),
        "is_orientation": False,
    },
    {
        "number": 4,
        "slug": "module-4-advanced-recovery-and-history",
        "title": "Module 4",
        "description": (
            "Practice hard reset recovery, safe pushed commit reversal, and "
            "rebase recovery sequences."
        ),
        "is_orientation": False,
    },
]


# ---------------------------------------------------------------------------
# Module 0 - orientation lessons (verbatim from LESSON_SPECS)
# ---------------------------------------------------------------------------

EMPTY_REPO = {
    "repository_initialized": False,
    "commits": [],
    "branches": {"main": None},
    "head": {"type": "none", "name": None},
    "working_tree": {},
    "staging": {},
    "conflicts": [],
}

STATUS_DEMO_STATE = {
    "repository_initialized": True,
    "commits": [
        {
            "id": "c0",
            "message": "Initial commit",
            "parents": [],
            "tree": {"app.txt": "tracked", "notes.txt": "tracked"},
            "order": 0,
        }
    ],
    "branches": {"main": "c0"},
    "head": {"type": "branch", "name": "main"},
    "working_tree": {"app.txt": "modified"},
    "staging": {"notes.txt": "staged"},
    "conflicts": [],
}

DAG_DEMO_STATE = {
    "repository_initialized": True,
    "commits": [
        {
            "id": "c0",
            "message": "Initial commit",
            "parents": [],
            "tree": {"README.md": "tracked"},
            "files": {"README.md": "tracked"},
            "order": 0,
        },
        {
            "id": "c1",
            "message": "Shared base",
            "parents": ["c0"],
            "tree": {"README.md": "tracked"},
            "files": {"README.md": "tracked"},
            "order": 1,
        },
        {
            "id": "c2",
            "message": "Main line",
            "parents": ["c1"],
            "tree": {"README.md": "tracked", "app.txt": "tracked"},
            "files": {"README.md": "tracked", "app.txt": "tracked"},
            "order": 2,
        },
        {
            "id": "c3",
            "message": "Feature branch",
            "parents": ["c1"],
            "tree": {"README.md": "tracked", "feature.txt": "tracked"},
            "files": {"README.md": "tracked", "feature.txt": "tracked"},
            "order": 3,
        },
    ],
    "branches": {"main": "c2", "feature": "c3"},
    "head": {"type": "branch", "name": "main"},
    "working_tree": {},
    "staging": {},
    "conflicts": [],
}

STATUS_SAMPLE_OUTPUT = """On branch main
Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
\tmodified:   notes.txt
Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
\tmodified:   app.txt"""

ORIENTATION_LESSON_SPECS: list[dict[str, Any]] = [
    {
        "sort_order": 1,
        "slug": "what-is-git-and-why-it-matters",
        "title": "What Is Git and Why Does It Matter?",
        "subtitle": "Version control fundamentals and the team workflow Git protects.",
        "content_html": """
            <p>Git is a <strong>distributed version control system</strong>. It tracks the full history of your project so teams can compare versions, recover work, and collaborate safely.</p>
            <p>Think of Git as a timeline plus collaboration protocol. It stores <em>what changed</em>, <em>why it changed</em>, and <em>how changes connect</em>.</p>
        """,
        "interaction_steps": [
            {
                "id": "vc-discipline",
                "kind": "continue",
                "title": "Version control discipline",
                "prompt": "Read this scenario, then continue: two teammates both edit a file called report_final.docx and keep making renamed copies.",
                "body": "Manual copy naming breaks quickly in teams: no reliable ownership, unclear latest file, and no safe rollback point. Git replaces that with a shared, auditable history.",
            },
            {
                "id": "centralized-vs-distributed",
                "kind": "compare_toggle",
                "title": "Centralized vs distributed",
                "prompt": "Compare each model and note where authoritative history lives and what happens if the server goes down.",
                "options": [
                    {
                        "id": "centralized",
                        "label": "Centralized (SVN)",
                        "detail": "One central server owns history. Clients depend on it for full context and many operations.",
                    },
                    {
                        "id": "distributed",
                        "label": "Distributed (Git)",
                        "detail": "Every clone has complete history. Remotes coordinate sharing, but work can continue locally.",
                    },
                ],
            },
            {
                "id": "three-problems",
                "kind": "continue",
                "title": "Three problems Git solves",
                "prompt": "Review these three problems directly and map each one to the Git capability that solves it.",
                "body": "History: identify exactly who changed a line and why. Collaboration: multiple branches can progress without overwriting each other. Recovery: previous known-good states can be restored quickly during incidents.",
            },
            {
                "id": "industry-standard",
                "kind": "continue",
                "title": "Industry standard",
                "prompt": "Git is the default VCS in software teams, open-source projects, and CI/CD pipelines.",
                "body": "Modern workflows (feature branching, code review, release tagging, bisecting regressions, and automated deployments) all assume Git fluency. Build the mental model first, then command syntax becomes predictable rather than memorized.",
            },
        ],
    },
    {
        "sort_order": 2,
        "slug": "installing-git-and-environment",
        "title": "Installing Git and Setting Up Your Environment",
        "subtitle": "Install Git and configure authorship for commits.",
        "content_html": "<p>Install Git for your OS, verify the install, and configure your identity. These values appear in commit metadata and power collaboration tools like blame, review, and release auditing.</p>",
        "interaction_steps": [
            {
                "id": "install-notes",
                "kind": "continue",
                "title": "Install Git",
                "prompt": "Windows: Git Bash from git-scm.com. macOS: Homebrew or Xcode CLI. Linux: apt install git.",
                "body": "Use a real terminal on your machine for install; this lesson practices configuration commands.",
            },
            {
                "id": "verify-version",
                "kind": "git_command",
                "title": "Verify installation",
                "prompt": "Type the command that prints the installed Git version (exact flag spelling matters).",
                "accept_prefixes": ["git --version"],
                "hint": "Use git --version (not --v).",
                "require_processed": False,
                "success_output": "git version 2.44.0",
                "initial_state": EMPTY_REPO,
            },
            {
                "id": "set-name",
                "kind": "git_command",
                "title": "Set your name",
                "prompt": 'Set global user.name, e.g. git config --global user.name "Your Name"',
                "accept_prefixes": ["git config --global user.name"],
                "hint": "Use git config --global user.name followed by your name in quotes.",
                "require_processed": False,
                "success_output": "Set global user.name",
                "initial_state": EMPTY_REPO,
            },
            {
                "id": "set-email",
                "kind": "git_command",
                "title": "Set your email",
                "prompt": "Set global user.email with your commit email.",
                "accept_prefixes": ["git config --global user.email"],
                "hint": "Use git config --global user.email and a valid email in quotes.",
                "require_processed": False,
                "success_output": "Set global user.email",
                "initial_state": EMPTY_REPO,
            },
            {
                "id": "list-config",
                "kind": "git_command",
                "title": "List configuration",
                "prompt": "List active Git configuration values, then look for user.name and user.email.",
                "accept_prefixes": ["git config --list", "git config -l"],
                "hint": "Try git config --list, then scan the output for identity keys.",
                "require_processed": False,
                "success_output": "user.name=Your Name\nuser.email=you@example.com",
                "initial_state": EMPTY_REPO,
            },
        ],
    },
    {
        "sort_order": 3,
        "slug": "command-line-basics",
        "title": "Command Line Basics for Git Users",
        "subtitle": "Navigate the filesystem before running Git in the right folder.",
        "content_html": "<p>Many Git mistakes start as filesystem mistakes. Before running Git commands, always confirm where you are, what files exist, and what just changed in your working directory.</p>",
        "interaction_steps": [
            {
                "id": "pwd",
                "kind": "shell_command",
                "title": "Where am I?",
                "prompt": "Type pwd to print the working directory.",
                "accept_prefixes": ["pwd"],
                "hint": "pwd takes no arguments.",
            },
            {
                "id": "ls-la",
                "kind": "shell_command",
                "title": "List including hidden",
                "prompt": "Type ls -la to see hidden files like .git later.",
                "accept_prefixes": ["ls -la", "ls -a -l"],
                "hint": "Use ls with -la flags.",
            },
            {
                "id": "mkdir-practice",
                "kind": "shell_command",
                "title": "Create a folder",
                "prompt": "Type mkdir practice to create a project folder.",
                "accept_prefixes": ["mkdir practice"],
                "hint": "mkdir creates a directory.",
            },
            {
                "id": "cd-practice",
                "kind": "shell_command",
                "title": "Enter the folder",
                "prompt": "Type cd practice to move into that folder, then confirm your new location in the next commands.",
                "accept_prefixes": ["cd practice"],
                "hint": "cd changes your working directory.",
            },
            {
                "id": "touch-readme",
                "kind": "shell_command",
                "title": "Create a file",
                "prompt": "Type touch readme.md to create an empty file.",
                "accept_prefixes": ["touch readme.md"],
                "hint": "touch creates an empty file.",
            },
            {
                "id": "echo-readme",
                "kind": "shell_command",
                "title": "Write to the file",
                "prompt": 'Type echo "hello" > readme.md to write text into the file.',
                "accept_prefixes": ['echo "hello" > readme.md', "echo hello > readme.md"],
                "hint": "echo with > writes text to a file.",
            },
            {
                "id": "cat-readme",
                "kind": "shell_command",
                "title": "Read the file",
                "prompt": "Type cat readme.md to print the file contents.",
                "accept_prefixes": ["cat readme.md"],
                "hint": "cat prints file contents to the terminal.",
            },
        ],
    },
    {
        "sort_order": 4,
        "slug": "git-diagram-four-areas",
        "title": "The Git Diagram: How Git Thinks About Your Files",
        "subtitle": "Working tree, staging, local repo, and remote — plus git status.",
        "content_html": "<p>The four-area model is the core Git mental model: <strong>Working Tree</strong> (your edits), <strong>Staging Area</strong> (selected snapshot), <strong>Local Repository</strong> (committed history), and <strong>Remote</strong> (shared collaboration point). <code>git status</code> tells you where each change currently lives.</p>",
        "interaction_steps": [
            {
                "id": "pipeline-drag",
                "kind": "pipeline",
                "title": "Move through four areas",
                "prompt": "Move a file through the lifecycle: edit in working tree, select in staging, save in local repo, and share to remote.",
                "stages": ["working_tree", "staging", "local_repo", "remote"],
            },
            {
                "id": "staging-why",
                "kind": "continue",
                "title": "Why staging exists",
                "prompt": "Staging exists so one commit can contain only related changes, even when your working tree has multiple tasks in progress.",
                "body": "Use staging to curate commit scope. This is what keeps commit history readable and makes code review faster.",
            },
            {
                "id": "status-annotate",
                "kind": "status_annotate",
                "title": "Read git status",
                "prompt": "Study the sample output and map each section to one area of the model.",
                "sample_output": STATUS_SAMPLE_OUTPUT,
            },
            {
                "id": "run-status",
                "kind": "git_command",
                "title": "Run git status",
                "prompt": "Run git status on the demo repository and compare it with the annotated sample.",
                "accept_prefixes": ["git status"],
                "hint": "git status is diagnostic — use it freely in practice.",
                "initial_state": STATUS_DEMO_STATE,
            },
        ],
    },
    {
        "sort_order": 5,
        "slug": "commits-and-history",
        "title": "Understanding Commits and Commit History",
        "subtitle": "Commit structure, metadata meaning, and why commit objects are immutable.",
        "content_html": "<p>A commit is a structured record, not just a message. It stores a content snapshot plus metadata: hash, author, timestamp, message, and parent commit links. Together these fields make history traceable and verifiable.</p>",
        "interaction_steps": [
            {
                "id": "anatomy-explore",
                "kind": "anatomy",
                "title": "Commit anatomy",
                "prompt": "Inspect each commit field and learn what question it answers during debugging and collaboration.",
                "parts": ["hash", "author", "timestamp", "message", "tree", "parent"],
            },
            {
                "id": "immutability",
                "kind": "immutability_demo",
                "title": "Immutability",
                "prompt": "Use the demo to see why amend creates a new commit object instead of mutating the old one.",
            },
            {
                "id": "messages",
                "kind": "continue",
                "title": "Commit messages",
                "prompt": "Use clear commit message structure: imperative subject line + optional body for rationale.",
                "body": "Recommended format: first line <= 72 chars in imperative mood (for example: Add login validation for empty passwords). Add a body when needed: why this change exists, key constraints, and notable side effects.",
            },
        ],
    },
    {
        "sort_order": 6,
        "slug": "reading-a-dag",
        "title": "Reading a DAG: Branches, HEAD, and Commit Graphs",
        "subtitle": "Read branch labels, HEAD, merges, and git log output.",
        "content_html": "<p>Git history is a DAG (Directed Acyclic Graph): each commit points to parent commit(s). Branch labels are movable pointers to commits, and HEAD points to your current checkout context.</p>",
        "interaction_steps": [
            {
                "id": "dag-labels",
                "kind": "dag_explore",
                "title": "Label the graph",
                "prompt": "Inspect the graph and identify which commit each branch label points to, then identify what HEAD currently follows.",
                "initial_state": DAG_DEMO_STATE,
            },
            {
                "id": "detached-head",
                "kind": "continue",
                "title": "Detached HEAD",
                "prompt": "When HEAD points to a commit hash instead of a branch, new work can become unreachable.",
                "body": "Create a branch before switching away from detached HEAD if you want to keep commits.",
            },
            {
                "id": "log-graph",
                "kind": "git_command",
                "title": "Graph log",
                "prompt": "Run git log --oneline --graph --all to print a compact branch-aware commit graph.",
                "accept_prefixes": [
                    "git log --oneline --graph --all",
                    "git log --graph --oneline --all",
                ],
                "hint": "Use git log with --oneline --graph --all (order of flags can vary).",
                "initial_state": DAG_DEMO_STATE,
            },
            {
                "id": "log-decorate",
                "kind": "continue",
                "title": "Branch labels on the graph",
                "prompt": "Branch labels are pointers, not copies of commits. When a branch advances, only the label moves.",
                "body": "In terminal output, --decorate shows these labels beside commits. In this platform, the visual DAG shows the same idea directly.",
            },
        ],
    },
    {
        "sort_order": 7,
        "slug": "git-command-anatomy",
        "title": "Git Command Anatomy",
        "subtitle": "Subcommands, flags, arguments, and reading help output.",
        "content_html": "<p>Parse commands as <code>git &lt;subcommand&gt; [flags] [arguments]</code>. Understanding this anatomy helps you debug syntax quickly and adapt commands without memorizing full strings.</p>",
        "interaction_steps": [
            {
                "id": "decompose-commit",
                "kind": "command_builder",
                "title": "Decompose commit",
                "prompt": 'Build: git commit -m "message"',
                "target": 'git commit -m "message"',
            },
            {
                "id": "decompose-log",
                "kind": "command_builder",
                "title": "Decompose log",
                "prompt": "Build: git log --oneline --graph --all",
                "target": "git log --oneline --graph --all",
            },
            {
                "id": "read-help",
                "kind": "git_command",
                "title": "Quick help",
                "prompt": "Type git commit -h to read the short help synopsis and identify required vs optional parts.",
                "accept_prefixes": ["git commit -h"],
                "hint": "Use -h for a short summary of a subcommand.",
                "require_processed": False,
                "success_output": "usage: git commit [-m <msg>] [--amend]\n\n-m <msg>    use the given commit message\n--amend     replace the latest commit with a new commit object",
                "initial_state": EMPTY_REPO,
            },
            {
                "id": "parse-error",
                "kind": "error_parse",
                "title": "Read an error",
                "prompt": "Which part failed? fatal: not a git repository → you are outside a repo (need git init).",
                "error_text": "fatal: not a git repository (or any of the parent directories): .git",
                "answer": "repository",
            },
        ],
    },
    {
        "sort_order": 8,
        "slug": "how-git-it-works",
        "title": "How GIT it! Works: The Platform Walkthrough",
        "subtitle": "Scenario workspace, scaffolding tiers, and progress tools.",
        "content_html": "<p>Before scenario practice, understand the workspace flow end-to-end: read objective, inspect repository state, run commands, compare actual vs target state, and iterate from feedback.</p>",
        "interaction_steps": [
            {
                "id": "workspace-map",
                "kind": "platform_panel",
                "title": "Practice workspace",
                "prompt": "Walk through a sample practice session by inspecting each workspace region in order of use.",
                "body": "Sample flow: (1) Read the objective in the narrative panel, (2) inspect current repository state in the DAG, (3) run a command in the terminal, (4) compare against expected state, (5) use feedback to decide the next command.",
                "hotspots": ["narrative", "files", "dag", "expected", "terminal", "feedback"],
            },
            {
                "id": "difficulty-tiers",
                "kind": "platform_panel",
                "title": "Difficulty tiers",
                "prompt": "Compare support levels: Easy (guided), Medium (reduced hints), Hard (minimal scaffolding).",
                "body": "Easy exposes all instructional panels. Medium removes direct feedback so you infer more from state. Hard keeps only essential state indicators so you rely on command reasoning.",
                "hotspots": ["easy", "medium", "hard"],
            },
            {
                "id": "counted-commands",
                "kind": "platform_panel",
                "title": "Counted vs diagnostic",
                "prompt": "Diagnostic commands (git status, git log, git diff) do not consume the action budget.",
                "body": "Use diagnostics frequently to inspect state. Counted commands are history-changing actions such as add, commit, merge, checkout conflict-side, and restore operations.",
                "hotspots": ["diagnostic", "counted"],
            },
            {
                "id": "retry-policy",
                "kind": "platform_panel",
                "title": "Retries and no-answer policy",
                "prompt": "Failed sessions retry with changed variants. The platform avoids answer leaks so you build transferable command fluency.",
                "body": "Treat retries as fresh scenarios. Focus on principles instead of memorizing sequences, and rely on status/log/diff evidence to recover.",
                "hotspots": ["retry", "no_answer"],
            },
            {
                "id": "dashboard",
                "kind": "continue",
                "title": "Progress dashboard",
                "prompt": "Track completion, accuracy, and review mode from the dashboard after orientation.",
                "body": "You are ready to open Module 1 scenarios when you feel prepared — orientation is recommended first.",
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Module 1 - Local Repository Foundations
#
# Source: seed_module1_scenarios.py. SESSION_COUNTS default is
# {easy: 3, medium: 2, hard: 2}; the only override anywhere in the file is
# init_scenario()'s EASY difficulty (required_attempts=1), applied below via
# each tier's own "required_successful_attempts" key when present.
# "Inspecting Repository State" (diagnostic_scenario) has no difficulties in
# the source - it becomes a level with an empty "tiers" list.
# ---------------------------------------------------------------------------

MODULE_1_SESSION_COUNTS_DEFAULT = {"easy": 3, "medium": 2, "hard": 2}

# "Inspecting Repository State" (the old diagnostic-only scenario, zero
# difficulties in the source - see seed_module1_scenarios.py:diagnostic_scenario())
# is deliberately NOT a numbered AdventureLevel node. In the old app it was a
# "Guided Preview" card in the same scenario list (ScenarioSkillFocusCard.tsx:
# isPreviewOnly = difficulties.length === 0), excluded from the Lesson N
# counter but still shown inline. Confirmed via `git show
# archive/may30-old-modules:...` that this was real seeded ScenarioSkillFocus
# data, not a hardcoded UI element - so its title/description below are
# preserved for wherever the new UI places this reference content (a separate
# decision from node numbering). See INSPECTING_REPOSITORY_STATE_PREVIEW.
INSPECTING_REPOSITORY_STATE_PREVIEW = {
    "slug": "inspecting-repository-state",
    "title": "Inspecting Repository State",
    "description": "Read repository status, history, diffs, branches, remotes, and objects before acting.",
}

MODULE_1_LEVELS: list[dict[str, Any]] = [
    {
        "sort_order": 1,
        "slug": "initializing-a-local-repository",
        "title": "Initializing Repositories",
        "description": "Create Git metadata in an existing or named project folder.",
        "tiers": {
            "easy": {
                "required_successful_attempts": 1,  # explicit override in source
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "Initialize the current folder with the requested first-branch behavior.",
                "task": "Make the current folder a Git repository, but do not stage files or create a commit.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "init-easy-current-empty",
                        "label": "Initialize the current folder",
                        "context": "Your team just created a project folder but never initialized it as a Git repository. Initialize the current directory so the project can be version-controlled.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git init"],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "main",
                            "staging_empty": True,
                            "rules": [
                                {"type": "commit_count_equals", "count": 0},
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_directory",
                                    "value": None,
                                },
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
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_quiet",
                                    "value": False,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_reinitialized",
                                    "value": False,
                                },
                            ],
                        },
                    },
                    {
                        "case_id": "init-easy-trunk-branch",
                        "label": "Initialize with trunk as the first branch",
                        "context": "Your team uses 'trunk' as the main branch name by convention. Initialize the current directory as a Git repository with 'trunk' as the initial branch.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git init --initial-branch=trunk"],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "trunk",
                            "staging_empty": True,
                            "rules": [
                                {"type": "commit_count_equals", "count": 0},
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_directory",
                                    "value": None,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_current_directory",
                                    "value": True,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_initial_branch",
                                    "value": "trunk",
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_quiet",
                                    "value": False,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_reinitialized",
                                    "value": False,
                                },
                            ],
                        },
                    },
                    {
                        "case_id": "init-easy-invoice",
                        "label": "Initialize invoice-tracker",
                        "context": "A client hired you to build a simple invoice tracker. You need to start the project from scratch with Git version control. Create and initialize a new Git repository named invoice-tracker.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git init invoice-tracker"],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "main",
                            "staging_empty": True,
                            "rules": [
                                {"type": "commit_count_equals", "count": 0},
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_directory",
                                    "value": "invoice-tracker",
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_current_directory",
                                    "value": False,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_initial_branch",
                                    "value": "main",
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_quiet",
                                    "value": False,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_reinitialized",
                                    "value": False,
                                },
                            ],
                        },
                    },
                ],
            },
            "medium": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "Initialize a named project folder with branch and quiet options when requested.",
                "task": "Initialize the exact target directory and branch mode named in the brief.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "init-med-oss",
                        "label": "Initialize oss-contrib",
                        "context": "You want to start contributing to an open-source project. Your mentor told you to first create a local scaffold directory called oss-contrib where you'll mirror your fork setup. Create and initialize the repo.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git init oss-contrib"],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "main",
                            "staging_empty": True,
                            "rules": [
                                {"type": "commit_count_equals", "count": 0},
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_directory",
                                    "value": "oss-contrib",
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_current_directory",
                                    "value": False,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_initial_branch",
                                    "value": "main",
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_quiet",
                                    "value": False,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_reinitialized",
                                    "value": False,
                                },
                            ],
                        },
                    },
                    {
                        "case_id": "init-medium-docs-site",
                        "label": "Initialize docs-site",
                        "context": "Your team needs a dedicated Git repository for the project documentation site. Initialize a new repo named docs-site in your current workspace.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git init docs-site"],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "main",
                            "staging_empty": True,
                            "rules": [
                                {"type": "commit_count_equals", "count": 0},
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_directory",
                                    "value": "docs-site",
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_current_directory",
                                    "value": False,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_initial_branch",
                                    "value": "main",
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_quiet",
                                    "value": False,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_reinitialized",
                                    "value": False,
                                },
                            ],
                        },
                    },
                    {
                        "case_id": "init-medium-trunk-api-playground",
                        "label": "Initialize api-playground with trunk",
                        "context": "You're setting up a sandbox repo for API experiments. The team uses 'trunk' as the default branch. Initialize a new named directory api-playground with trunk as the initial branch.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git init -b trunk api-playground"],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "trunk",
                            "staging_empty": True,
                            "rules": [
                                {"type": "commit_count_equals", "count": 0},
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_directory",
                                    "value": "api-playground",
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_current_directory",
                                    "value": False,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_initial_branch",
                                    "value": "trunk",
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_quiet",
                                    "value": False,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_reinitialized",
                                    "value": False,
                                },
                            ],
                        },
                    },
                    {
                        "case_id": "init-medium-quiet-research-log",
                        "label": "Initialize research-log quietly",
                        "context": "You're initializing a research notes repository called research-log. The CI script expects quiet output so nothing is printed to the console. Initialize it with quiet mode enabled.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git init --quiet --initial-branch=main research-log"
                        ],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "main",
                            "staging_empty": True,
                            "rules": [
                                {"type": "commit_count_equals", "count": 0},
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_directory",
                                    "value": "research-log",
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_current_directory",
                                    "value": False,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_initial_branch",
                                    "value": "main",
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_quiet",
                                    "value": True,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_reinitialized",
                                    "value": False,
                                },
                            ],
                        },
                    },
                ],
            },
            "hard": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "Combine child-folder targeting with branch, quiet, and reinitialization details.",
                "task": "Initialize only the requested child directory or safely reinitialize the existing repository as directed.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "init-hard-ci",
                        "label": "Initialize ci-configs",
                        "context": "You've been asked to create a versioned pipeline configuration store. The ops team refers to it as ci-configs. No step-by-step instructions were given — figure out what needs to be done and do it.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {"pipelines/build.yml": "untracked"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git init ci-configs"],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "main",
                            "staging_empty": True,
                            "rules": [
                                {"type": "commit_count_equals", "count": 0},
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_directory",
                                    "value": "ci-configs",
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_current_directory",
                                    "value": False,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_initial_branch",
                                    "value": "main",
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_quiet",
                                    "value": False,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_reinitialized",
                                    "value": False,
                                },
                            ],
                        },
                    },
                    {
                        "case_id": "init-hard-research-log",
                        "label": "Initialize research-log subfolder only",
                        "context": "You're working in a parent workspace with multiple subdirectories. Only the research-log subfolder should become a Git repository — the parent and sibling folders must not be affected. Initialize only that subdirectory, quietly.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "research-log/README.md": "untracked",
                                "notes/ideas.md": "untracked",
                                "archive/old.md": "untracked",
                            },
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git init -q -b main research-log"],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "main",
                            "staging_empty": True,
                            "rules": [
                                {"type": "commit_count_equals", "count": 0},
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_directory",
                                    "value": "research-log",
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_current_directory",
                                    "value": False,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_initial_branch",
                                    "value": "main",
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_quiet",
                                    "value": True,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_reinitialized",
                                    "value": False,
                                },
                            ],
                        },
                    },
                    {
                        "case_id": "init-hard-ui-kit",
                        "label": "Initialize ui-kit with trunk, quietly",
                        "context": "You're in a design parent workspace. Only the ui-kit subfolder should be version-controlled — sibling folders like brand-assets and experiments must be left alone. Initialize ui-kit quietly with 'trunk' as the branch name.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "ui-kit/tokens.css": "untracked",
                                "brand-assets/logo.svg": "untracked",
                                "experiments/mockup.html": "untracked",
                            },
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git init --quiet --initial-branch=trunk ui-kit"],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "trunk",
                            "staging_empty": True,
                            "rules": [
                                {"type": "commit_count_equals", "count": 0},
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_directory",
                                    "value": "ui-kit",
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_current_directory",
                                    "value": False,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_initial_branch",
                                    "value": "trunk",
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_quiet",
                                    "value": True,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_reinitialized",
                                    "value": False,
                                },
                            ],
                        },
                    },
                    {
                        "case_id": "init-hard-safe-rerun",
                        "label": "Safely reinitialize the current repository",
                        "context": "The release-notes directory is already a Git repository with one commit. A teammate ran a script that re-runs git init as a safety check. You need to safely reinitialize without losing the existing history. Run it quietly.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Keep existing notes",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {"notes/today.md": "untracked"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git init --quiet"],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "main",
                            "staging_empty": True,
                            "rules": [
                                {"type": "commit_count_equals", "count": 1},
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_directory",
                                    "value": None,
                                },
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
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_quiet",
                                    "value": True,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_init_reinitialized",
                                    "value": True,
                                },
                            ],
                        },
                    },
                ],
            },
        },
    },
    {
        "sort_order": 2,
        "slug": "cloning-a-remote-repository",
        "title": "Cloning Remote Repositories",
        "description": "Create a local working copy and verify the origin relationship.",
        "tiers": {
            "easy": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "Clone with the requested destination and branch behavior.",
                "task": "Use the provided remote URL and follow the destination or branch details exactly.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "clone-easy-docs-portal",
                        "label": "Clone docs-portal",
                        "context": "Your team's documentation portal is hosted remotely. Clone it so you can start contributing to the docs locally.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {},
                            "staging": {},
                            "conflicts": [],
                            "remote_fixtures": {
                                "url": "https://example.test/training/docs-portal.git",
                                "default_branch": "main",
                                "head": "r10",
                                "tree": {
                                    "README.md": "docs-readme-v1",
                                    "docs/intro.md": "docs-intro-v1",
                                },
                            },
                        },
                        "solution_commands": [
                            "git clone https://example.test/training/docs-portal.git"
                        ],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "main",
                            "remote_exists": ["origin"],
                            "remote_branch_exists": ["origin/main"],
                            "remote_branch_points_to": {"origin/main": "r10"},
                            "branch_points_to": {"main": "r10"},
                            "upstream_tracking": {"main": "origin/main"},
                            "staging_empty": True,
                            "working_tree_clean": True,
                        },
                    },
                    {
                        "case_id": "clone-easy-api-lab",
                        "label": "Clone api-lab into api-workshop",
                        "context": "You're onboarding at a startup. The backend API is hosted remotely. Your team's convention is to store repos in a folder named api-workshop. Clone it into that folder.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {},
                            "staging": {},
                            "conflicts": [],
                            "remote_fixtures": {
                                "url": "https://example.test/training/api-lab.git",
                                "default_branch": "main",
                                "head": "r11",
                                "tree": {
                                    "README.md": "api-readme-v1",
                                    "api/routes.py": "api-routes-v1",
                                },
                            },
                        },
                        "solution_commands": [
                            "git clone https://example.test/training/api-lab.git api-workshop"
                        ],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "main",
                            "remote_exists": ["origin"],
                            "remote_branch_exists": ["origin/main"],
                            "remote_branch_points_to": {"origin/main": "r11"},
                            "branch_points_to": {"main": "r11"},
                            "upstream_tracking": {"main": "origin/main"},
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_clone_destination",
                                    "value": "api-workshop",
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "clone-easy-profile-starter",
                        "label": "Clone profile-site at the starter branch",
                        "context": "The profile site repo has a starter branch with template files ready to use. Clone it and check out the starter branch directly instead of main.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {},
                            "staging": {},
                            "conflicts": [],
                            "remote_fixtures": {
                                "url": "https://example.test/training/profile-site.git",
                                "default_branch": "main",
                                "head": "r13",
                                "branches": {"origin/main": "r12", "origin/starter": "r13"},
                                "tree": {
                                    "index.html": "profile-index-v2",
                                    "styles/site.css": "profile-css-v1",
                                    "starter-notes.md": "starter-notes-v1",
                                },
                            },
                        },
                        "solution_commands": [
                            "git clone -b starter https://example.test/training/profile-site.git"
                        ],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "starter",
                            "remote_exists": ["origin"],
                            "remote_branch_exists": ["origin/starter"],
                            "remote_branch_points_to": {"origin/starter": "r13"},
                            "branch_points_to": {"starter": "r13"},
                            "upstream_tracking": {"starter": "origin/starter"},
                            "staging_empty": True,
                            "working_tree_clean": True,
                        },
                    },
                    {
                        "case_id": "clone-easy-oss-ssh",
                        "label": "Clone oss-toolkit via SSH",
                        "context": "You've set up SSH keys and want to clone the OSS project you're contributing to. Clone it using the SSH URL.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {},
                            "staging": {},
                            "conflicts": [],
                            "remote_fixtures": {
                                "url": "git@github.com:open-dev/oss-toolkit.git",
                                "default_branch": "main",
                                "head": "r40",
                                "tree": {
                                    "README.md": "oss-readme-v1",
                                    "src/toolkit.py": "toolkit-v1",
                                },
                            },
                        },
                        "solution_commands": ["git clone git@github.com:open-dev/oss-toolkit.git"],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "main",
                            "remote_exists": ["origin"],
                            "remote_branch_exists": ["origin/main"],
                            "remote_branch_points_to": {"origin/main": "r40"},
                            "branch_points_to": {"main": "r40"},
                            "upstream_tracking": {"main": "origin/main"},
                            "staging_empty": True,
                            "working_tree_clean": True,
                        },
                    },
                    {
                        "case_id": "clone-easy-corp",
                        "label": "Clone audit-logs into audit-logs-local",
                        "context": "Your company hosts Git internally. Clone the internal audit logs repository into a local folder named audit-logs-local.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {},
                            "staging": {},
                            "conflicts": [],
                            "remote_fixtures": {
                                "url": "https://git.corp.example/it/audit-logs.git",
                                "default_branch": "main",
                                "head": "r41",
                                "tree": {"README.md": "audit-readme-v1", "logs/q1.csv": "q1-v1"},
                            },
                        },
                        "solution_commands": [
                            "git clone https://git.corp.example/it/audit-logs.git audit-logs-local"
                        ],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "main",
                            "remote_exists": ["origin"],
                            "remote_branch_exists": ["origin/main"],
                            "remote_branch_points_to": {"origin/main": "r41"},
                            "branch_points_to": {"main": "r41"},
                            "upstream_tracking": {"main": "origin/main"},
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_clone_destination",
                                    "value": "audit-logs-local",
                                }
                            ],
                        },
                    },
                ],
            },
            "medium": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "Clone SSH, branch, and shallow variants.",
                "task": "Use the requested URL syntax, branch, destination folder, and depth exactly.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "clone-med-feature",
                        "label": "Clone backend-api at feature/auth",
                        "context": "The backend team is mid-sprint on a feature/auth branch. You need to clone the repo and start from that branch directly rather than switching after cloning.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {},
                            "staging": {},
                            "conflicts": [],
                            "remote_fixtures": {
                                "url": "https://github.com/acme-startup/backend-api.git",
                                "default_branch": "main",
                                "default_head": "r49",
                                "head": "r50",
                                "branches": {"origin/main": "r49", "origin/feature/auth": "r50"},
                                "tree": {"README.md": "api-readme-v1", "src/auth.py": "auth-v1"},
                            },
                        },
                        "solution_commands": [
                            "git clone -b feature/auth https://github.com/acme-startup/backend-api.git"
                        ],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "feature/auth",
                            "remote_exists": ["origin"],
                            "remote_branch_exists": ["origin/feature/auth"],
                            "remote_branch_points_to": {"origin/feature/auth": "r50"},
                            "branch_points_to": {"feature/auth": "r50"},
                        },
                    },
                    {
                        "case_id": "clone-medium-analytics-ssh",
                        "label": "Clone analytics-lab via SSH into analytics-worktree",
                        "context": "You've configured SSH access to the analytics lab repository. Clone it into a custom local folder named analytics-worktree using the SSH URL.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {},
                            "staging": {},
                            "conflicts": [],
                            "remote_fixtures": {
                                "url": "git@example.test:training/analytics-lab.git",
                                "default_branch": "main",
                                "head": "r30",
                                "tree": {
                                    "README.md": "analytics-readme-v3",
                                    "metrics/report.md": "metrics-report-v2",
                                    "src/summary.py": "summary-v1",
                                },
                            },
                        },
                        "solution_commands": [
                            "git clone git@example.test:training/analytics-lab.git analytics-worktree"
                        ],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "main",
                            "remote_exists": ["origin"],
                            "remote_branch_exists": ["origin/main"],
                            "remote_branch_points_to": {"origin/main": "r30"},
                            "branch_points_to": {"main": "r30"},
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_clone_destination",
                                    "value": "analytics-worktree",
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "clone-medium-cli-starter-folder",
                        "label": "Clone cli-tool at starter into cli-starter-lab",
                        "context": "A CLI tool repo has a starter branch prepared for onboarding contributors. Clone it into a folder called cli-starter-lab, checking out the starter branch immediately.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {},
                            "staging": {},
                            "conflicts": [],
                            "remote_fixtures": {
                                "url": "https://example.test/tools/cli-tool.git",
                                "default_branch": "main",
                                "default_head": "r19",
                                "head": "r20",
                                "branches": {"origin/main": "r19", "origin/starter": "r20"},
                                "tree": {
                                    "README.md": "cli-readme-v2",
                                    "src/parser.py": "cli-parser-v2",
                                    "starter.md": "cli-starter-v1",
                                },
                            },
                        },
                        "solution_commands": [
                            "git clone --branch starter https://example.test/tools/cli-tool.git cli-starter-lab"
                        ],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "starter",
                            "remote_exists": ["origin"],
                            "remote_branch_exists": ["origin/starter"],
                            "remote_branch_points_to": {"origin/starter": "r20"},
                            "branch_points_to": {"starter": "r20"},
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_clone_destination",
                                    "value": "cli-starter-lab",
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "clone-medium-css-kit-shallow",
                        "label": "Shallow clone css-kit",
                        "context": "Your CI pipeline needs a lightweight clone of the CSS kit repository for a one-time build. Disk space is limited — use a shallow clone of depth 1 to keep it fast.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {},
                            "staging": {},
                            "conflicts": [],
                            "remote_fixtures": {
                                "url": "https://example.test/frontend/css-kit.git",
                                "default_branch": "main",
                                "head": "r22",
                                "tree": {
                                    "README.md": "css-readme-v2",
                                    "styles/tokens.css": "tokens-v2",
                                },
                            },
                        },
                        "solution_commands": [
                            "git clone --depth 1 https://example.test/frontend/css-kit.git"
                        ],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "main",
                            "remote_exists": ["origin"],
                            "remote_branch_exists": ["origin/main"],
                            "remote_branch_points_to": {"origin/main": "r22"},
                            "branch_points_to": {"main": "r22"},
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_clone_depth",
                                    "value": 1,
                                }
                            ],
                        },
                    },
                ],
            },
            "hard": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "Combine shallow clone, selected branch, and custom destination requirements.",
                "task": "Use the exact clone syntax requested, then end with clean tracking refs.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "clone-hard-ssh-shallow",
                        "label": "Shallow SSH clone of oss-toolkit into oss-review",
                        "context": "You want a minimal clone of the OSS toolkit repository with only the latest commit using SSH, stored in a folder named oss-review. Combine shallow cloning with a custom destination.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {},
                            "staging": {},
                            "conflicts": [],
                            "remote_fixtures": {
                                "url": "git@github.com:open-dev/oss-toolkit.git",
                                "default_branch": "main",
                                "default_head": "r59",
                                "head": "r60",
                                "tree": {
                                    "README.md": "oss-readme-v2",
                                    "src/toolkit.py": "toolkit-v2",
                                },
                            },
                        },
                        "solution_commands": [
                            "git clone --depth 1 git@github.com:open-dev/oss-toolkit.git oss-review"
                        ],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "main",
                            "remote_exists": ["origin"],
                            "remote_branch_exists": ["origin/main"],
                            "remote_branch_points_to": {"origin/main": "r60"},
                            "branch_points_to": {"main": "r60"},
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_clone_depth",
                                    "value": 1,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_clone_destination",
                                    "value": "oss-review",
                                },
                            ],
                        },
                    },
                    {
                        "case_id": "clone-hard-mobile-ui-shallow-branch",
                        "label": "Shallow clone mobile-ui at starter into mobile-ui-lab",
                        "context": "You need a lightweight copy of the mobile UI starter branch for a quick review. Clone only the tip of the starter branch into a folder named mobile-ui-lab — no full history needed.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {},
                            "staging": {},
                            "conflicts": [],
                            "remote_fixtures": {
                                "url": "https://example.test/frontend/mobile-ui.git",
                                "default_branch": "main",
                                "default_head": "r23",
                                "head": "r31",
                                "branches": {"origin/main": "r23", "origin/starter": "r31"},
                                "tree": {
                                    "README.md": "mobile-readme-v2",
                                    "screens/home.tsx": "home-v1",
                                    "styles/mobile.css": "mobile-css-v1",
                                },
                            },
                        },
                        "solution_commands": [
                            "git clone --depth 1 -b starter https://example.test/frontend/mobile-ui.git mobile-ui-lab"
                        ],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "starter",
                            "remote_exists": ["origin"],
                            "remote_branch_exists": ["origin/starter"],
                            "remote_branch_points_to": {"origin/starter": "r31"},
                            "branch_points_to": {"starter": "r31"},
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_clone_depth",
                                    "value": 1,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_clone_destination",
                                    "value": "mobile-ui-lab",
                                },
                            ],
                        },
                    },
                    {
                        "case_id": "clone-hard-lab-notebook-depth-branch",
                        "label": "Shallow clone lab-notebook at review into notebook-review",
                        "context": "You need to review specific lab notebook entries on the review branch, but don't need the full commit history. Clone only the tip of the review branch into a folder named notebook-review.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {},
                            "staging": {},
                            "conflicts": [],
                            "remote_fixtures": {
                                "url": "https://example.test/docs/lab-notebook.git",
                                "default_branch": "main",
                                "default_head": "r24",
                                "head": "r32",
                                "branches": {"origin/main": "r24", "origin/review": "r32"},
                                "tree": {
                                    "README.md": "notebook-readme-v2",
                                    "entries/day-1.md": "day1-v1",
                                    "entries/day-2.md": "day2-v1",
                                },
                            },
                        },
                        "solution_commands": [
                            "git clone --depth 1 --branch review https://example.test/docs/lab-notebook.git notebook-review"
                        ],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "review",
                            "remote_exists": ["origin"],
                            "remote_branch_exists": ["origin/review"],
                            "remote_branch_points_to": {"origin/review": "r32"},
                            "branch_points_to": {"review": "r32"},
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_clone_depth",
                                    "value": 1,
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_clone_destination",
                                    "value": "notebook-review",
                                },
                            ],
                        },
                    },
                    {
                        "case_id": "clone-hard-research-log-ssh",
                        "label": "Clone research-log via SSH into research-log-lab",
                        "context": "You've configured SSH access and need a full clone of the research log repository. Clone it via SSH into a local folder named research-log-lab for offline analysis.",
                        "initial_state": {
                            "repository_initialized": False,
                            "commits": [],
                            "branches": {},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {},
                            "staging": {},
                            "conflicts": [],
                            "remote_fixtures": {
                                "url": "git@example.test:docs/research-log.git",
                                "default_branch": "main",
                                "default_head": "r33",
                                "head": "r34",
                                "tree": {
                                    "README.md": "research-readme-v2",
                                    "notes/week-1.md": "week1-v1",
                                    "notes/week-2.md": "week2-v1",
                                },
                            },
                        },
                        "solution_commands": [
                            "git clone git@example.test:docs/research-log.git research-log-lab"
                        ],
                        "state_requirements": {
                            "repository_initialized": True,
                            "head_branch": "main",
                            "remote_exists": ["origin"],
                            "remote_branch_exists": ["origin/main"],
                            "remote_branch_points_to": {"origin/main": "r34"},
                            "branch_points_to": {"main": "r34"},
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_clone_destination",
                                    "value": "research-log-lab",
                                }
                            ],
                        },
                    },
                ],
            },
        },
    },
    {
        "sort_order": 3,
        "slug": "staging-and-committing-basic-workflow",
        "title": "Staging and Committing",
        "description": "Prepare intentional changes and save them with a clear message.",
        "tiers": {
            "easy": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "Commit one clear file change.",
                "task": "Stage and save the single intended file with the required message.",
                "min_counted_commands": 2,
                "cases": [
                    {
                        "case_id": "commit-easy-initial",
                        "label": "Initial commit for library-system",
                        "context": "You've just initialized the library-system repo. You have three files ready: README.md, main.py, and requirements.txt. Your group lead says 'do the initial commit.'",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "README.md": "readme-init-v1",
                                "main.py": "main-init-v1",
                                "requirements.txt": "reqs-init-v1",
                            },
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git add .", 'git commit -m "Initial commit"'],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Initial commit"],
                                "contains_paths": ["README.md", "main.py", "requirements.txt"],
                            },
                        },
                    },
                    {
                        "case_id": "commit-easy-auth-dir",
                        "label": "Commit the auth module directory",
                        "context": "You added a new src/auth/ directory containing login.py and logout.py. Both are new files. Stage the entire directory and commit it as one focused snapshot.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "src/auth/login.py": "login-v1",
                                "src/auth/logout.py": "logout-v1",
                            },
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add src/auth/",
                            'git commit -m "Add auth module"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Add auth module"],
                                "contains_paths": ["src/auth/login.py", "src/auth/logout.py"],
                            },
                        },
                    },
                    {
                        "case_id": "commit-easy-form-validation",
                        "label": "Commit form validation update",
                        "context": "You updated the form validation logic in src/form.js. It's the only file changed and it's ready to commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {"src/form.js": "form-validation-v2"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add src/form.js",
                            'git commit -m "Update form validation"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Update form validation"],
                                "contains_paths": ["src/form.js"],
                            },
                        },
                    },
                    {
                        "case_id": "commit-easy-readme-setup",
                        "label": "Commit README clarification",
                        "context": "You revised the README.md to make the setup instructions clearer. Stage it and commit with the required message.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {"README.md": "readme-setup-v2"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add README.md",
                            'git commit --message "Clarify setup steps"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Clarify setup steps"],
                                "contains_paths": ["README.md"],
                            },
                        },
                    },
                    {
                        "case_id": "commit-easy-navbar-spacing",
                        "label": "Commit navbar spacing fix",
                        "context": "You tweaked the navbar spacing in styles/navbar.css to fix a visual alignment issue. Stage and commit just that one file.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {"styles/navbar.css": "navbar-spacing-v2"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add -A",
                            'git commit -m "Adjust navbar spacing"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Adjust navbar spacing"],
                                "contains_paths": ["styles/navbar.css"],
                            },
                        },
                    },
                ],
            },
            "medium": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "Commit multiple related files.",
                "task": "Stage and save all intended files as one focused snapshot.",
                "min_counted_commands": 2,
                "cases": [
                    {
                        "case_id": "commit-med-docker",
                        "label": "Commit Docker configuration",
                        "context": "You updated Dockerfile and .env.example as part of a container setup. Stage both files and commit them together as one focused snapshot.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "Dockerfile": "dockerfile-v2",
                                ".env.example": "env-example-v1",
                            },
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add Dockerfile .env.example",
                            'git commit -m "Add Docker configuration"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Add Docker configuration"],
                                "contains_paths": ["Dockerfile", ".env.example"],
                            },
                        },
                    },
                    {
                        "case_id": "commit-medium-profile-card",
                        "label": "Commit profile card layout",
                        "context": "You redesigned the profile card component. Both the JavaScript logic and the CSS stylesheet are updated and ready to commit together.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "src/profile-card.js": "profile-js-v2",
                                "styles/profile-card.css": "profile-css-v2",
                            },
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add --all",
                            'git commit -m "Update profile card layout"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Update profile card layout"],
                                "contains_paths": [
                                    "src/profile-card.js",
                                    "styles/profile-card.css",
                                ],
                            },
                        },
                    },
                    {
                        "case_id": "commit-medium-search-results",
                        "label": "Commit search results view",
                        "context": "You refined the search results view — the JavaScript handler and the HTML template both changed. Commit both files together with the required message.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "src/search.js": "search-js-v2",
                                "templates/search.html": "search-template-v2",
                            },
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add src/search.js templates/search.html",
                            'git commit --message "Refine search results view"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Refine search results view"],
                                "contains_paths": ["src/search.js", "templates/search.html"],
                            },
                        },
                    },
                    {
                        "case_id": "commit-medium-export-flow",
                        "label": "Commit export flow update",
                        "context": "You updated the export module and rewrote the matching documentation to reflect the new behavior. Commit both the code and the docs as one snapshot.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "src/export.py": "export-code-v2",
                                "docs/export.md": "export-docs-v2",
                            },
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add src/export.py docs/export.md",
                            'git commit -m "Document export flow update"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Document export flow update"],
                                "contains_paths": ["src/export.py", "docs/export.md"],
                            },
                        },
                    },
                ],
            },
            "hard": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "Commit intended work while leaving unrelated work out.",
                "task": "Stage and save only the target files; leave unrelated work uncommitted.",
                "min_counted_commands": 2,
                "cases": [
                    {
                        "case_id": "commit-hard-selective",
                        "label": "Commit handler fix, leave experimental file out",
                        "context": "You've been working on two things: a bug fix in api/handler.py and experimental work in api/experimental.py. Only the bug fix is ready. Stage handler.py and leave the experimental file out.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "api/handler.py": "handler-bugfix-v2",
                                "api/experimental.py": "experimental-wip-v1",
                            },
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add api/handler.py",
                            'git commit -m "Fix request handler null check"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Fix request handler null check"],
                                "contains_paths": ["api/handler.py"],
                                "excludes_paths": ["api/experimental.py"],
                            },
                            "working_tree_contains": ["api/experimental.py"],
                        },
                    },
                    {
                        "case_id": "commit-hard-parser",
                        "label": "Commit parser and tests, leave debug/scratch files out",
                        "context": "You're preparing a PR for a new parser feature. The files ready to go are src/parser.py and tests/test_parser.py. A debug.log and scratch.py are also in the tree — keep them out of the commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "src/parser.py": "parser-v2",
                                "tests/test_parser.py": "test-parser-v1",
                                "debug.log": "debug-draft",
                                "scratch.py": "scratch-draft",
                            },
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add src/parser.py tests/test_parser.py",
                            'git commit -m "Add parser module with unit tests"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Add parser module with unit tests"],
                                "contains_paths": ["src/parser.py", "tests/test_parser.py"],
                                "excludes_paths": ["debug.log", "scratch.py"],
                            },
                            "working_tree_contains": ["debug.log", "scratch.py"],
                        },
                    },
                    {
                        "case_id": "commit-hard-profile-distractor",
                        "label": "Commit profile card change, leave notes out",
                        "context": "You updated the profile card behavior in src/profile-card.js. You also have a notes/profile-ideas.md scratch file in the working tree — that's not ready and should stay out of the commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "src/profile-card.js": "profile-js-v3",
                                "notes/profile-ideas.md": "profile-notes-draft",
                            },
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add src/profile-card.js",
                            'git commit -m "Update profile card behavior"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Update profile card behavior"],
                                "contains_paths": ["src/profile-card.js"],
                                "excludes_paths": ["notes/profile-ideas.md"],
                            },
                            "working_tree_contains": ["notes/profile-ideas.md"],
                        },
                    },
                    {
                        "case_id": "commit-hard-export-distractor",
                        "label": "Commit export fix, leave scratch output out",
                        "context": "You fixed the export validation logic in src/export.py. A scratch/export-test-output.txt file from your testing is also present — leave it uncommitted.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "src/export.py": "export-code-v3",
                                "scratch/export-test-output.txt": "export-output-draft",
                            },
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add src/export.py",
                            'git commit -m "Fix export validation"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Fix export validation"],
                                "contains_paths": ["src/export.py"],
                                "excludes_paths": ["scratch/export-test-output.txt"],
                            },
                            "working_tree_contains": ["scratch/export-test-output.txt"],
                        },
                    },
                    {
                        "case_id": "commit-hard-search-two-targets-one-distractor",
                        "label": "Commit search ranking display, leave notes out",
                        "context": "You refined the search ranking display — both src/search.js and templates/search.html are updated and ready. A notes/search-ranking.md scratch file is present but must stay out of this commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "src/search.js": "search-js-v3",
                                "templates/search.html": "search-template-v3",
                                "notes/search-ranking.md": "search-notes-draft",
                            },
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add src/search.js templates/search.html",
                            'git commit -m "Refine search ranking display"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Refine search ranking display"],
                                "contains_paths": ["src/search.js", "templates/search.html"],
                                "excludes_paths": ["notes/search-ranking.md"],
                            },
                            "working_tree_contains": ["notes/search-ranking.md"],
                        },
                    },
                ],
            },
        },
    },
    {
        "sort_order": 4,
        "slug": "partial-staging-and-git-add-p",
        "title": "Partial Staging",
        "description": "Stage selected hunks so each commit has one clear purpose.",
        "tiers": {
            "easy": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "Commit one selected hunk from one file.",
                "task": "Commit only the named hunk and leave the other hunk in the working tree.",
                "min_counted_commands": 2,
                "cases": [
                    {
                        "case_id": "partial-easy-billing",
                        "label": "Stage the billing fix hunk only",
                        "context": "You modified billing.py. The file has two changed sections: a rounding fix at the top and some experimental print statements at the bottom. Your client is waiting on the fix only — stage just that hunk.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "src/billing.py": {
                                    "status": "modified",
                                    "hunks": ["billing-fix-hunk", "billing-experimental-hunk"],
                                }
                            },
                            "staging": {},
                            "conflicts": [],
                            "partial_hunks": {
                                "src/billing.py": {
                                    "target_hunks": ["billing-fix-hunk"],
                                    "leftover_hunks": ["billing-experimental-hunk"],
                                }
                            },
                        },
                        "solution_commands": [
                            "git add -p src/billing.py",
                            'git commit -m "Fix billing calculation rounding error"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Fix billing calculation rounding error"],
                                "contains_paths": ["src/billing.py"],
                            },
                            "working_tree_contains": ["src/billing.py"],
                        },
                    },
                    {
                        "case_id": "partial-easy-routes",
                        "label": "Stage the routes handler hunk only",
                        "context": "src/routes.py has two changed sections: updated route handlers (ready to commit) and a commented-out experimental auth middleware section (skip this for now). Use partial staging to commit only the handler update.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "src/routes.py": {
                                    "status": "modified",
                                    "hunks": ["routes-handler-hunk", "routes-experimental-hunk"],
                                }
                            },
                            "staging": {},
                            "conflicts": [],
                            "partial_hunks": {
                                "src/routes.py": {
                                    "target_hunks": ["routes-handler-hunk"],
                                    "leftover_hunks": ["routes-experimental-hunk"],
                                }
                            },
                        },
                        "solution_commands": [
                            "git add -p src/routes.py",
                            'git commit -m "Update API route handlers"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Update API route handlers"],
                                "contains_paths": ["src/routes.py"],
                            },
                            "working_tree_contains": ["src/routes.py"],
                        },
                    },
                    {
                        "case_id": "partial-easy-auth-validation",
                        "label": "Stage the auth validation hunk only",
                        "context": "src/auth.py has two hunks: a validation fix that's ready and a larger refactor that's still in progress. Stage only the validation fix and leave the refactor in the working tree.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "src/auth.py": {
                                    "status": "modified",
                                    "hunks": ["auth-validation-hunk", "auth-refactor-hunk"],
                                }
                            },
                            "staging": {},
                            "conflicts": [],
                            "partial_hunks": {
                                "src/auth.py": {
                                    "target_hunks": ["auth-validation-hunk"],
                                    "leftover_hunks": ["auth-refactor-hunk"],
                                }
                            },
                        },
                        "solution_commands": [
                            "git add -p src/auth.py",
                            'git commit -m "Isolate auth validation"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Isolate auth validation"],
                                "contains_paths": ["src/auth.py"],
                            },
                            "working_tree_contains": ["src/auth.py"],
                        },
                    },
                    {
                        "case_id": "partial-easy-search-ranking",
                        "label": "Stage the search ranking hunk only",
                        "context": "src/search.py has two hunks: a ranking algorithm fix (ready) and some cleanup refactoring (not ready). Commit only the ranking fix.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "src/search.py": {
                                    "status": "modified",
                                    "hunks": ["search-ranking-hunk", "search-cleanup-hunk"],
                                }
                            },
                            "staging": {},
                            "conflicts": [],
                            "partial_hunks": {
                                "src/search.py": {
                                    "target_hunks": ["search-ranking-hunk"],
                                    "leftover_hunks": ["search-cleanup-hunk"],
                                }
                            },
                        },
                        "solution_commands": [
                            "git add -p src/search.py",
                            'git commit -m "Isolate search ranking"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Isolate search ranking"],
                                "contains_paths": ["src/search.py"],
                            },
                            "working_tree_contains": ["src/search.py"],
                        },
                    },
                    {
                        "case_id": "partial-easy-export-format",
                        "label": "Stage the export formatting hunk only",
                        "context": "src/export.py has two changed sections: a formatting fix (stage this) and some added logging statements (leave these out for now). Use git add -p to commit only the formatting change.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "src/export.py": {
                                    "status": "modified",
                                    "hunks": ["export-format-hunk", "export-logging-hunk"],
                                }
                            },
                            "staging": {},
                            "conflicts": [],
                            "partial_hunks": {
                                "src/export.py": {
                                    "target_hunks": ["export-format-hunk"],
                                    "leftover_hunks": ["export-logging-hunk"],
                                }
                            },
                        },
                        "solution_commands": [
                            "git add -p src/export.py",
                            'git commit -m "Isolate export formatting"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Isolate export formatting"],
                                "contains_paths": ["src/export.py"],
                            },
                            "working_tree_contains": ["src/export.py"],
                        },
                    },
                ],
            },
            "medium": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "Commit one hunk while another file remains unrelated.",
                "task": "Commit only the target hunk and leave the unrelated file out.",
                "min_counted_commands": 2,
                "cases": [
                    {
                        "case_id": "partial-med-three-hunk",
                        "label": "Stage only the parser bug fix hunk",
                        "context": "src/parser.py has three hunks: a bug fix (stage), a refactor (skip — not ready), and an experimental section (skip). Use partial staging to commit only the bug fix.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "src/parser.py": {
                                    "status": "modified",
                                    "hunks": [
                                        "parser-bugfix-hunk",
                                        "parser-refactor-hunk",
                                        "parser-experimental-hunk",
                                    ],
                                }
                            },
                            "staging": {},
                            "conflicts": [],
                            "partial_hunks": {
                                "src/parser.py": {
                                    "target_hunks": ["parser-bugfix-hunk"],
                                    "leftover_hunks": [
                                        "parser-refactor-hunk",
                                        "parser-experimental-hunk",
                                    ],
                                }
                            },
                        },
                        "solution_commands": [
                            "git add -p src/parser.py",
                            'git commit -m "Fix parser bug and refactor token handling"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Fix parser bug and refactor token handling"],
                                "contains_paths": ["src/parser.py"],
                            },
                            "working_tree_contains": ["src/parser.py"],
                        },
                    },
                    {
                        "case_id": "partial-medium-profile-validation",
                        "label": "Stage only the profile validation hunk",
                        "context": "src/profile.py has three changed sections: a validation fix (stage), a copy update (skip), and a cleanup block (skip). A notes/profile-todo.md file is also present — leave it out. Stage only the validation fix.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "src/profile.py": {
                                    "status": "modified",
                                    "hunks": [
                                        "profile-validation-hunk",
                                        "profile-copy-hunk",
                                        "profile-cleanup-hunk",
                                    ],
                                },
                                "notes/profile-todo.md": "profile-todo-draft",
                            },
                            "staging": {},
                            "conflicts": [],
                            "partial_hunks": {
                                "src/profile.py": {
                                    "target_hunks": ["profile-validation-hunk"],
                                    "leftover_hunks": ["profile-copy-hunk", "profile-cleanup-hunk"],
                                }
                            },
                        },
                        "solution_commands": [
                            "git add -p src/profile.py",
                            'git commit -m "Commit profile validation only"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Commit profile validation only"],
                                "contains_paths": ["src/profile.py"],
                                "excludes_paths": ["notes/profile-todo.md"],
                            },
                            "working_tree_contains": ["src/profile.py", "notes/profile-todo.md"],
                        },
                    },
                    {
                        "case_id": "partial-medium-payment-rounding",
                        "label": "Stage only the payment rounding hunk",
                        "context": "src/payment.py has three changed sections: a rounding fix (stage), added logging (skip), and a comment update (skip). A tmp/payment-scratch.txt file is also in the working tree. Commit only the rounding fix.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "src/payment.py": {
                                    "status": "modified",
                                    "hunks": [
                                        "payment-rounding-hunk",
                                        "payment-logging-hunk",
                                        "payment-comment-hunk",
                                    ],
                                },
                                "tmp/payment-scratch.txt": "payment-scratch-draft",
                            },
                            "staging": {},
                            "conflicts": [],
                            "partial_hunks": {
                                "src/payment.py": {
                                    "target_hunks": ["payment-rounding-hunk"],
                                    "leftover_hunks": [
                                        "payment-logging-hunk",
                                        "payment-comment-hunk",
                                    ],
                                }
                            },
                        },
                        "solution_commands": [
                            "git add -p src/payment.py",
                            'git commit -m "Commit payment rounding fix"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Commit payment rounding fix"],
                                "contains_paths": ["src/payment.py"],
                                "excludes_paths": ["tmp/payment-scratch.txt"],
                            },
                            "working_tree_contains": ["src/payment.py", "tmp/payment-scratch.txt"],
                        },
                    },
                    {
                        "case_id": "partial-medium-dashboard-filter",
                        "label": "Stage only the dashboard filter hunk",
                        "context": "src/dashboard.js has three hunks: a filter logic fix (stage), a theme update (skip), and some console.log statements (skip). A notes/dashboard-ideas.md is also present. Stage only the filter change.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "src/dashboard.js": {
                                    "status": "modified",
                                    "hunks": [
                                        "dashboard-filter-hunk",
                                        "dashboard-theme-hunk",
                                        "dashboard-console-hunk",
                                    ],
                                },
                                "notes/dashboard-ideas.md": "dashboard-ideas-draft",
                            },
                            "staging": {},
                            "conflicts": [],
                            "partial_hunks": {
                                "src/dashboard.js": {
                                    "target_hunks": ["dashboard-filter-hunk"],
                                    "leftover_hunks": [
                                        "dashboard-theme-hunk",
                                        "dashboard-console-hunk",
                                    ],
                                }
                            },
                        },
                        "solution_commands": [
                            "git add -p src/dashboard.js",
                            'git commit -m "Commit dashboard filter change"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Commit dashboard filter change"],
                                "contains_paths": ["src/dashboard.js"],
                                "excludes_paths": ["notes/dashboard-ideas.md"],
                            },
                            "working_tree_contains": [
                                "src/dashboard.js",
                                "notes/dashboard-ideas.md",
                            ],
                        },
                    },
                ],
            },
            "hard": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "Commit selected hunks across files in a noisy workspace.",
                "task": "Use the hunk-level target and leave all unrelated work out of the final snapshot.",
                "min_counted_commands": 2,
                "cases": [
                    {
                        "case_id": "partial-hard-terraform",
                        "label": "Stage only the network Terraform hunk",
                        "context": "terraform/main.tf has two hunks: network configuration (stage) and experimental feature flags (skip). A terraform/debug.txt file is also in the workspace. Stage only the network hunk and leave everything else behind.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "terraform/main.tf": {
                                    "status": "modified",
                                    "hunks": [
                                        "terraform-network-hunk",
                                        "terraform-experimental-hunk",
                                    ],
                                },
                                "terraform/debug.txt": "terraform-debug-draft",
                            },
                            "staging": {},
                            "conflicts": [],
                            "partial_hunks": {
                                "terraform/main.tf": {
                                    "target_hunks": ["terraform-network-hunk"],
                                    "leftover_hunks": ["terraform-experimental-hunk"],
                                }
                            },
                        },
                        "solution_commands": [
                            "git add -p terraform/main.tf",
                            'git commit -m "Update network Terraform configuration"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Update network Terraform configuration"],
                                "contains_paths": ["terraform/main.tf"],
                                "excludes_paths": ["terraform/debug.txt"],
                            },
                            "working_tree_contains": ["terraform/main.tf", "terraform/debug.txt"],
                        },
                    },
                    {
                        "case_id": "partial-hard-auth-cross-file",
                        "label": "Stage validation hunks across auth code and tests",
                        "context": "Two files are modified: src/auth.py (validation fix hunk to stage, refactor hunk to skip) and tests/test_auth.py (validation test hunk to stage, test cleanup hunk to skip). A notes/auth-debug.md is also present. Stage only the validation path across both files.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "src/auth.py": {
                                    "status": "modified",
                                    "hunks": ["auth-validation-hunk", "auth-refactor-hunk"],
                                },
                                "tests/test_auth.py": {
                                    "status": "modified",
                                    "hunks": [
                                        "auth-validation-test-hunk",
                                        "auth-test-cleanup-hunk",
                                    ],
                                },
                                "notes/auth-debug.md": "auth-debug-draft",
                            },
                            "staging": {},
                            "conflicts": [],
                            "partial_hunks": {
                                "src/auth.py": {
                                    "target_hunks": ["auth-validation-hunk"],
                                    "leftover_hunks": ["auth-refactor-hunk"],
                                },
                                "tests/test_auth.py": {
                                    "target_hunks": ["auth-validation-test-hunk"],
                                    "leftover_hunks": ["auth-test-cleanup-hunk"],
                                },
                            },
                        },
                        "solution_commands": [
                            "git add -p src/auth.py",
                            "git add -p tests/test_auth.py",
                            'git commit -m "Commit auth validation path"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Commit auth validation path"],
                                "contains_paths": ["src/auth.py", "tests/test_auth.py"],
                                "excludes_paths": ["notes/auth-debug.md"],
                            },
                            "working_tree_contains": [
                                "src/auth.py",
                                "tests/test_auth.py",
                                "notes/auth-debug.md",
                            ],
                        },
                    },
                    {
                        "case_id": "partial-hard-search-cross-file",
                        "label": "Stage ranking hunks across search code and tests",
                        "context": "Two files are modified: src/search.py (ranking fix to stage, cleanup to skip) and tests/test_search.py (ranking test to stage, fixture cleanup to skip). A tmp/search-output.txt is also present. Stage only the ranking change across both files.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "src/search.py": {
                                    "status": "modified",
                                    "hunks": ["search-ranking-hunk", "search-cleanup-hunk"],
                                },
                                "tests/test_search.py": {
                                    "status": "modified",
                                    "hunks": [
                                        "search-ranking-test-hunk",
                                        "search-test-fixture-hunk",
                                    ],
                                },
                                "tmp/search-output.txt": "search-output-draft",
                            },
                            "staging": {},
                            "conflicts": [],
                            "partial_hunks": {
                                "src/search.py": {
                                    "target_hunks": ["search-ranking-hunk"],
                                    "leftover_hunks": ["search-cleanup-hunk"],
                                },
                                "tests/test_search.py": {
                                    "target_hunks": ["search-ranking-test-hunk"],
                                    "leftover_hunks": ["search-test-fixture-hunk"],
                                },
                            },
                        },
                        "solution_commands": [
                            "git add -p src/search.py",
                            "git add -p tests/test_search.py",
                            'git commit -m "Commit search ranking path"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Commit search ranking path"],
                                "contains_paths": ["src/search.py", "tests/test_search.py"],
                                "excludes_paths": ["tmp/search-output.txt"],
                            },
                            "working_tree_contains": [
                                "src/search.py",
                                "tests/test_search.py",
                                "tmp/search-output.txt",
                            ],
                        },
                    },
                    {
                        "case_id": "partial-hard-export-cross-file",
                        "label": "Stage formatting hunks across export code and tests",
                        "context": "Two files are modified: src/export.py (formatting fix to stage, logging additions to skip) and tests/test_export.py (formatting test to stage, test cleanup to skip). A notes/export-followup.md is also present. Stage only the formatting path.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {
                                "src/export.py": {
                                    "status": "modified",
                                    "hunks": ["export-format-hunk", "export-logging-hunk"],
                                },
                                "tests/test_export.py": {
                                    "status": "modified",
                                    "hunks": [
                                        "export-format-test-hunk",
                                        "export-test-cleanup-hunk",
                                    ],
                                },
                                "notes/export-followup.md": "export-followup-draft",
                            },
                            "staging": {},
                            "conflicts": [],
                            "partial_hunks": {
                                "src/export.py": {
                                    "target_hunks": ["export-format-hunk"],
                                    "leftover_hunks": ["export-logging-hunk"],
                                },
                                "tests/test_export.py": {
                                    "target_hunks": ["export-format-test-hunk"],
                                    "leftover_hunks": ["export-test-cleanup-hunk"],
                                },
                            },
                        },
                        "solution_commands": [
                            "git add -p src/export.py",
                            "git add -p tests/test_export.py",
                            'git commit -m "Commit export formatting path"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Commit export formatting path"],
                                "contains_paths": ["src/export.py", "tests/test_export.py"],
                                "excludes_paths": ["notes/export-followup.md"],
                            },
                            "working_tree_contains": [
                                "src/export.py",
                                "tests/test_export.py",
                                "notes/export-followup.md",
                            ],
                        },
                    },
                ],
            },
        },
    },
    {
        "sort_order": 5,
        "slug": "amending-commits",
        "title": "Amending Commits",
        "description": "Repair the latest commit message or contents before sharing it.",
        "tiers": {
            "easy": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "Fix only the latest commit message.",
                "task": "Repair the latest commit message without creating a separate commit.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "amend-easy-typo",
                        "label": "Fix a typo in the last commit message",
                        "context": "You committed with the message 'Initiall commit' — a typo. No file content needs to change, just the message. Amend the last commit to fix it.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Initiall commit",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "main.py": "main.py-committed-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": ['git commit --amend -m "Initial commit"'],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Initial commit"],
                                "contains_paths": ["main.py"],
                            },
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_amend_replaced_commit",
                                    "value": "c2",
                                },
                                {"type": "branch_tip_replaces_commit", "old": "c2"},
                                {"type": "commit_replaced_by_amend", "old": "c2"},
                            ],
                        },
                    },
                    {
                        "case_id": "amend-easy-forgot",
                        "label": "Add a forgotten file to the last commit",
                        "context": "You committed login.py but forgot to include logout.py — it belongs in the same commit. Stage logout.py and amend the last commit to include it without changing the message.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Add auth module",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/login.py": "src/login.py-committed-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {"src/logout.py": "logout-v1"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add src/logout.py",
                            'git commit --amend -m "Add auth module"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Add auth module"],
                                "contains_paths": ["src/login.py", "src/logout.py"],
                            },
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_amend_replaced_commit",
                                    "value": "c2",
                                },
                                {"type": "branch_tip_replaces_commit", "old": "c2"},
                                {"type": "commit_replaced_by_amend", "old": "c2"},
                            ],
                        },
                    },
                    {
                        "case_id": "amend-easy-login-copy-message",
                        "label": "Clarify a vague commit message",
                        "context": "Your last commit message says 'Update text' — too vague. It should be 'Clarify login copy'. No file content needs to change. Amend just the message.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Update text",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/login.js": "src/login.js-committed-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": ['git commit --amend -m "Clarify login copy"'],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Clarify login copy"],
                                "contains_paths": ["src/login.js"],
                            },
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_amend_replaced_commit",
                                    "value": "c2",
                                },
                                {"type": "branch_tip_replaces_commit", "old": "c2"},
                                {"type": "commit_replaced_by_amend", "old": "c2"},
                            ],
                        },
                    },
                    {
                        "case_id": "amend-easy-readme-message",
                        "label": "Clarify the README commit message",
                        "context": "Your last commit message is 'Update README' — not specific enough. The correct message is 'Clarify setup requirements'. Amend the commit message without changing any files.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Update README",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "README.md-committed-v1"},
                                },
                            ],
                            "branches": {"main": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": ['git commit --amend -m "Clarify setup requirements"'],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Clarify setup requirements"],
                                "contains_paths": ["README.md"],
                            },
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_amend_replaced_commit",
                                    "value": "c2",
                                },
                                {"type": "branch_tip_replaces_commit", "old": "c2"},
                                {"type": "commit_replaced_by_amend", "old": "c2"},
                            ],
                        },
                    },
                    {
                        "case_id": "amend-easy-navbar-message",
                        "label": "Clarify the navbar commit message",
                        "context": "Your last commit message is 'CSS updates' — too generic. It should be 'Adjust navbar spacing'. No content changes needed — just fix the message.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "CSS updates",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "styles/navbar.css": "styles/navbar.css-committed-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": ['git commit --amend -m "Adjust navbar spacing"'],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Adjust navbar spacing"],
                                "contains_paths": ["styles/navbar.css"],
                            },
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_amend_replaced_commit",
                                    "value": "c2",
                                },
                                {"type": "branch_tip_replaces_commit", "old": "c2"},
                                {"type": "commit_replaced_by_amend", "old": "c2"},
                            ],
                        },
                    },
                ],
            },
            "medium": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "Add missing content to the latest commit.",
                "task": "Stage the missing file and repair the latest commit while keeping its message.",
                "min_counted_commands": 2,
                "cases": [
                    {
                        "case_id": "amend-med-both",
                        "label": "Add changelog and correct the commit message",
                        "context": "Your last commit message was 'update stuff' (too vague) AND you forgot to include docs/CHANGELOG.md. Stage the changelog and fix the message in one amend operation.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "update stuff",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/parser.py": "src/parser.py-committed-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {"docs/CHANGELOG.md": "changelog-v2"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add docs/CHANGELOG.md",
                            'git commit --amend -m "Add parser feature and update changelog"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Add parser feature and update changelog"],
                                "contains_paths": ["src/parser.py", "docs/CHANGELOG.md"],
                            },
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_amend_replaced_commit",
                                    "value": "c2",
                                },
                                {"type": "branch_tip_replaces_commit", "old": "c2"},
                                {"type": "commit_replaced_by_amend", "old": "c2"},
                            ],
                        },
                    },
                    {
                        "case_id": "amend-medium-profile-missing-css",
                        "label": "Add missing profile CSS to the last commit",
                        "context": "You committed profile-card.js but forgot to include styles/profile-card.css — it belongs in the same commit. Stage the missing CSS file and amend without changing the commit message.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Update profile card layout",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/profile-card.js": "src/profile-card.js-committed-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {"styles/profile-card.css": "profile-css-v2"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add styles/profile-card.css",
                            'git commit --amend -m "Update profile card layout"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Update profile card layout"],
                                "contains_paths": [
                                    "src/profile-card.js",
                                    "styles/profile-card.css",
                                ],
                            },
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_amend_replaced_commit",
                                    "value": "c2",
                                },
                                {"type": "branch_tip_replaces_commit", "old": "c2"},
                                {"type": "commit_replaced_by_amend", "old": "c2"},
                            ],
                        },
                    },
                    {
                        "case_id": "amend-medium-export-doc",
                        "label": "Add missing export docs to the last commit",
                        "context": "You committed the export module code but forgot to include docs/export.md. Amend the last commit to add the documentation without changing the message.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Document export flow update",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/export.py": "src/export.py-committed-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {"docs/export.md": "export-docs-v2"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add docs/export.md",
                            'git commit --amend -m "Document export flow update"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Document export flow update"],
                                "contains_paths": ["src/export.py", "docs/export.md"],
                            },
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_amend_replaced_commit",
                                    "value": "c2",
                                },
                                {"type": "branch_tip_replaces_commit", "old": "c2"},
                                {"type": "commit_replaced_by_amend", "old": "c2"},
                            ],
                        },
                    },
                    {
                        "case_id": "amend-medium-search-template",
                        "label": "Add missing search template to the last commit",
                        "context": "You committed the search JavaScript but forgot to include templates/search.html — it belongs in the same snapshot. Stage the missing template and amend the commit without changing the message.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Refine search results view",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/search.js": "src/search.js-committed-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {"templates/search.html": "search-template-v2"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add templates/search.html",
                            'git commit --amend -m "Refine search results view"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Refine search results view"],
                                "contains_paths": ["src/search.js", "templates/search.html"],
                            },
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_amend_replaced_commit",
                                    "value": "c2",
                                },
                                {"type": "branch_tip_replaces_commit", "old": "c2"},
                                {"type": "commit_replaced_by_amend", "old": "c2"},
                            ],
                        },
                    },
                ],
            },
            "hard": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "Fix latest commit message and content together.",
                "task": "Repair both the message and missing content in the latest commit.",
                "min_counted_commands": 2,
                "cases": [
                    {
                        "case_id": "amend-hard-convention",
                        "label": "Correct a verbose passive-voice commit message",
                        "context": "Your last commit message is 'terraform configs have been updated for staging env' — passive voice, lowercase, too verbose. Correct it to follow Git imperative convention. No file content changes needed.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "terraform configs have been updated for staging env",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "terraform/staging.tf": "terraform/staging.tf-committed-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            'git commit --amend -m "Update Terraform staging environment configuration"'
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": [
                                    "Update Terraform staging environment configuration"
                                ],
                                "contains_paths": ["terraform/staging.tf"],
                            },
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_amend_replaced_commit",
                                    "value": "c2",
                                },
                                {"type": "branch_tip_replaces_commit", "old": "c2"},
                                {"type": "commit_replaced_by_amend", "old": "c2"},
                            ],
                        },
                    },
                    {
                        "case_id": "amend-hard-profile-message-and-layout",
                        "label": "Add missing CSS and correct the commit message",
                        "context": "Your last commit has two problems: the message 'Update profile stuff' is too vague, and styles/profile-layout.css was left out by mistake. Fix both — correct the message and add the missing file in one amend.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Update profile stuff",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/profile-card.js": "src/profile-card.js-committed-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {"styles/profile-layout.css": "profile-layout-css-v3"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add styles/profile-layout.css",
                            'git commit --amend -m "Polish profile card layout"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Polish profile card layout"],
                                "contains_paths": [
                                    "src/profile-card.js",
                                    "styles/profile-layout.css",
                                ],
                            },
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_amend_replaced_commit",
                                    "value": "c2",
                                },
                                {"type": "branch_tip_replaces_commit", "old": "c2"},
                                {"type": "commit_replaced_by_amend", "old": "c2"},
                            ],
                        },
                    },
                    {
                        "case_id": "amend-hard-auth-message-and-test",
                        "label": "Add missing test and correct the commit message",
                        "context": "Your last commit message is 'Auth changes' (too vague) and it's missing tests/test_auth.py. Fix both issues in one amend: correct the message and add the missing test file.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Auth changes",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/auth.py": "src/auth.py-committed-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {"tests/test_auth.py": "auth-test-v2"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add tests/test_auth.py",
                            'git commit --amend -m "Add auth validation coverage"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Add auth validation coverage"],
                                "contains_paths": ["src/auth.py", "tests/test_auth.py"],
                            },
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_amend_replaced_commit",
                                    "value": "c2",
                                },
                                {"type": "branch_tip_replaces_commit", "old": "c2"},
                                {"type": "commit_replaced_by_amend", "old": "c2"},
                            ],
                        },
                    },
                    {
                        "case_id": "amend-hard-export-message-and-doc",
                        "label": "Add missing docs and correct the commit message",
                        "context": "Your last commit message is 'Export update' (too vague) and docs/export.md is missing from the commit. Fix both: add the documentation file and correct the message in a single amend.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Export update",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/export.py": "src/export.py-committed-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "working_tree": {"docs/export.md": "export-docs-v3"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git add docs/export.md",
                            'git commit --amend -m "Document export validation behavior"',
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "latest_commit": {
                                "branch": "main",
                                "message_contains": ["Document export validation behavior"],
                                "contains_paths": ["src/export.py", "docs/export.md"],
                            },
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_amend_replaced_commit",
                                    "value": "c2",
                                },
                                {"type": "branch_tip_replaces_commit", "old": "c2"},
                                {"type": "commit_replaced_by_amend", "old": "c2"},
                            ],
                        },
                    },
                ],
            },
        },
    },
    {
        "sort_order": 6,
        "slug": "unstaging-and-discarding-changes",
        "title": "Unstaging and Discarding Changes",
        "description": "Move changes out of the index and safely discard unwanted work.",
        "tiers": {
            "easy": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "Unstage one file while keeping its working-tree change.",
                "task": "Move the staged file back to the working tree without discarding it.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "restore-easy-unstage",
                        "label": "Unstage notes.txt without discarding it",
                        "context": "You ran git add . and accidentally staged notes.txt along with your intended files. The commit isn't ready yet. Unstage notes.txt while keeping your working-tree changes.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {"notes.txt": "notes-draft"},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git restore --staged notes.txt"],
                        "state_requirements": {
                            "head_branch": "main",
                            "branch_points_to": {"main": "c1"},
                            "staging_empty": True,
                            "working_tree_contains": ["notes.txt"],
                            "rules": [{"type": "commit_count_equals", "count": 1}],
                        },
                    },
                    {
                        "case_id": "restore-easy-discard",
                        "label": "Discard experimental config.py changes",
                        "context": "You made some experimental edits to config.py trying out a new approach that didn't work. Discard all working-tree changes to config.py and get back to the last committed state.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {"config.py": "config-wrong-v2"},
                            "conflicts": [],
                        },
                        "solution_commands": ["git restore config.py"],
                        "state_requirements": {
                            "head_branch": "main",
                            "branch_points_to": {"main": "c1"},
                            "staging_empty": True,
                            "working_tree_absent": ["config.py"],
                            "rules": [{"type": "commit_count_equals", "count": 1}],
                        },
                    },
                    {
                        "case_id": "restore-easy-unstage-app",
                        "label": "Unstage src/app.py without discarding it",
                        "context": "You staged src/app.py but realize you're not ready to commit it yet. Unstage it so it stays as a working-tree change without being discarded.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {"src/app.py": "app-change-v2"},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git restore --staged src/app.py"],
                        "state_requirements": {
                            "head_branch": "main",
                            "branch_points_to": {"main": "c1"},
                            "staging_empty": True,
                            "working_tree_contains": ["src/app.py"],
                            "rules": [{"type": "commit_count_equals", "count": 1}],
                        },
                    },
                    {
                        "case_id": "restore-easy-unstage-guide",
                        "label": "Unstage docs/guide.md without discarding it",
                        "context": "You staged docs/guide.md, but you want to revise it more before committing. Unstage it — your edits should remain in the working tree, not be discarded.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {"docs/guide.md": "guide-change-v2"},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git restore --staged docs/guide.md"],
                        "state_requirements": {
                            "head_branch": "main",
                            "branch_points_to": {"main": "c1"},
                            "staging_empty": True,
                            "working_tree_contains": ["docs/guide.md"],
                            "rules": [{"type": "commit_count_equals", "count": 1}],
                        },
                    },
                    {
                        "case_id": "restore-easy-unstage-css",
                        "label": "Unstage styles/site.css without discarding it",
                        "context": "You staged styles/site.css but then realized another CSS change needs to be grouped with it. Unstage it for now so you can re-stage everything together later.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {"styles/site.css": "css-change-v2"},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git restore --staged styles/site.css"],
                        "state_requirements": {
                            "head_branch": "main",
                            "branch_points_to": {"main": "c1"},
                            "staging_empty": True,
                            "working_tree_contains": ["styles/site.css"],
                            "rules": [{"type": "commit_count_equals", "count": 1}],
                        },
                    },
                ],
            },
            "medium": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "Unstage one file and discard another working-tree change.",
                "task": "Keep the staged work as a working-tree change and remove the unwanted file.",
                "min_counted_commands": 2,
                "cases": [
                    {
                        "case_id": "restore-med-unstage-discard",
                        "label": "Unstage experimental.py, discard README.md changes",
                        "context": "You staged experimental.py (keep it as a working-tree change, not in the next commit) and also have working-tree edits to README.md that you want to throw away entirely. First unstage experimental.py, then discard the README changes.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {"experimental.py": "experimental-v1"},
                            "working_tree": {"README.md": "readme-wrong-v2"},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git restore --staged experimental.py",
                            "git restore README.md",
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "branch_points_to": {"main": "c1"},
                            "staging_empty": True,
                            "working_tree_contains": ["experimental.py"],
                            "working_tree_absent": ["README.md"],
                            "rules": [{"type": "commit_count_equals", "count": 1}],
                        },
                    },
                    {
                        "case_id": "restore-medium-app-debug",
                        "label": "Preserve app.py, discard debug.log",
                        "context": "You staged src/app.py but aren't ready to commit it yet, and you also have a debug.log in the working tree that you want to get rid of. Unstage app.py to preserve your work, then discard debug.log.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {"src/app.py": "app-change-v2"},
                            "working_tree": {"debug.log": "debug-draft"},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git restore --staged src/app.py",
                            "git restore debug.log",
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "branch_points_to": {"main": "c1"},
                            "staging_empty": True,
                            "working_tree_contains": ["src/app.py"],
                            "working_tree_absent": ["debug.log"],
                            "rules": [{"type": "commit_count_equals", "count": 1}],
                        },
                    },
                    {
                        "case_id": "restore-medium-docs-scratch",
                        "label": "Preserve guide.md, discard scratch.txt",
                        "context": "You staged docs/guide.md for a later commit and also have a tmp/scratch.txt that was just temporary notes. Unstage the guide to continue editing it, and discard the scratch file entirely.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {"docs/guide.md": "guide-change-v2"},
                            "working_tree": {"tmp/scratch.txt": "scratch-draft"},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git restore --staged docs/guide.md",
                            "git restore tmp/scratch.txt",
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "branch_points_to": {"main": "c1"},
                            "staging_empty": True,
                            "working_tree_contains": ["docs/guide.md"],
                            "working_tree_absent": ["tmp/scratch.txt"],
                            "rules": [{"type": "commit_count_equals", "count": 1}],
                        },
                    },
                    {
                        "case_id": "restore-medium-css-build",
                        "label": "Preserve source CSS, discard generated dist CSS",
                        "context": "You staged styles/site.css for revision and also have a generated dist/site.css in your working tree from an old build. Unstage the source CSS to keep working on it, and discard the generated dist file.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {"styles/site.css": "css-change-v2"},
                            "working_tree": {"dist/site.css": "dist-generated"},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git restore --staged styles/site.css",
                            "git restore dist/site.css",
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "branch_points_to": {"main": "c1"},
                            "staging_empty": True,
                            "working_tree_contains": ["styles/site.css"],
                            "working_tree_absent": ["dist/site.css"],
                            "rules": [{"type": "commit_count_equals", "count": 1}],
                        },
                    },
                ],
            },
            "hard": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "Clean a noisy mixed state.",
                "task": "Preserve the requested path and discard the unwanted path without making a commit.",
                "min_counted_commands": 2,
                "cases": [
                    {
                        "case_id": "restore-hard-cleanup",
                        "label": "Unstage two files, discard experimental.py",
                        "context": "You have a noisy mixed state: debug.log and scratch/notes.txt are staged (unstage them — don't discard, just move back to working tree), and api/experimental.py has working-tree changes you want to throw away. Clean up without making a commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {
                                "debug.log": "debug-draft",
                                "scratch/notes.txt": "notes-draft",
                            },
                            "working_tree": {"api/experimental.py": "experimental-wrong-v1"},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git restore --staged debug.log scratch/notes.txt",
                            "git restore api/experimental.py",
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "branch_points_to": {"main": "c1"},
                            "staging_empty": True,
                            "working_tree_contains": ["debug.log", "scratch/notes.txt"],
                            "working_tree_absent": ["api/experimental.py"],
                            "rules": [{"type": "commit_count_equals", "count": 1}],
                        },
                    },
                    {
                        "case_id": "restore-hard-mixed-profile",
                        "label": "Unstage two files, discard debug log",
                        "context": "Two files are staged: src/profile-card.js (keep your edits as a working-tree change) and notes/profile-ideas.md (also keep, just unstage). A debug/profile.log in the working tree should be discarded entirely. Clean up without committing.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {
                                "src/profile-card.js": "profile-js-v2",
                                "notes/profile-ideas.md": "notes-draft",
                            },
                            "working_tree": {"debug/profile.log": "debug-draft"},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git restore --staged src/profile-card.js notes/profile-ideas.md",
                            "git restore debug/profile.log",
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "branch_points_to": {"main": "c1"},
                            "staging_empty": True,
                            "working_tree_contains": [
                                "src/profile-card.js",
                                "notes/profile-ideas.md",
                            ],
                            "working_tree_absent": ["debug/profile.log"],
                            "rules": [{"type": "commit_count_equals", "count": 1}],
                        },
                    },
                    {
                        "case_id": "restore-hard-mixed-export",
                        "label": "Unstage two files, discard generated output",
                        "context": "Two files are staged: src/export.py (keep the edits as a working-tree change) and notes/export-plan.md (also keep, just unstage). A tmp/export-output.txt generated file is in the working tree and should be discarded. No commit needed.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {
                                "src/export.py": "export-code-v2",
                                "notes/export-plan.md": "notes-draft",
                            },
                            "working_tree": {"tmp/export-output.txt": "generated-output"},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git restore --staged src/export.py notes/export-plan.md",
                            "git restore tmp/export-output.txt",
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "branch_points_to": {"main": "c1"},
                            "staging_empty": True,
                            "working_tree_contains": ["src/export.py", "notes/export-plan.md"],
                            "working_tree_absent": ["tmp/export-output.txt"],
                            "rules": [{"type": "commit_count_equals", "count": 1}],
                        },
                    },
                    {
                        "case_id": "restore-hard-mixed-search",
                        "label": "Unstage two files, discard debug search log",
                        "context": "Two files are staged: src/search.js (preserve your edits, just unstage) and notes/search.md (also keep, just unstage). A debug/search.log in the working tree should be discarded entirely. Clean up without making a commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/app.py": "app-v1",
                                        "styles/site.css": "style-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {
                                "src/search.js": "search-js-v2",
                                "notes/search.md": "notes-draft",
                            },
                            "working_tree": {"debug/search.log": "search-debug"},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git restore --staged src/search.js notes/search.md",
                            "git restore debug/search.log",
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "branch_points_to": {"main": "c1"},
                            "staging_empty": True,
                            "working_tree_contains": ["src/search.js", "notes/search.md"],
                            "working_tree_absent": ["debug/search.log"],
                            "rules": [{"type": "commit_count_equals", "count": 1}],
                        },
                    },
                ],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Module 2 - Branching and Collaboration
#
# Source: seed_module2_scenarios.py. SESSION_COUNTS = {easy:3, medium:2,
# hard:2}; NO overrides anywhere in this file - every tier uses the plain
# default. All 9 anchors are wired (no dead scenarios in this module).
# ---------------------------------------------------------------------------

MODULE_2_SESSION_COUNTS_DEFAULT = {"easy": 3, "medium": 2, "hard": 2}

MODULE_2_LEVELS: list[dict[str, Any]] = [
    {
        "sort_order": 1,
        "slug": "creating-and-switching-branches",
        "title": "Creating and Switching Branches",
        "description": "Isolate work by creating branches from the right commit and moving HEAD to them.",
        "tiers": {
            "easy": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "Create a branch at the current HEAD and make it your working context.",
                "task": "Your team needs a dedicated line of work separated from main. Set up the branch and move to it.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "v21e-auth",
                        "label": "Create feature/auth and switch to it",
                        "context": "Your ticketing-app team lead just assigned you a new feature. Before writing any code, create an isolated branch so your work doesn't touch main until it's reviewed.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/app.py": "app-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch -c feature/auth"],
                        "state_requirements": {
                            "head_branch": "feature/auth",
                            "branch_exists": ["feature/auth"],
                            "branch_points_to": {"feature/auth": "c1"},
                        },
                    },
                    {
                        "case_id": "v21e-login",
                        "label": "Create bugfix/login and switch to it",
                        "context": "A bug was reported in the login flow of auth-service. You need a dedicated branch to contain the fix without disturbing the stable main line.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/app.py": "app-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch -c bugfix/login"],
                        "state_requirements": {
                            "head_branch": "bugfix/login",
                            "branch_exists": ["bugfix/login"],
                            "branch_points_to": {"bugfix/login": "c1"},
                        },
                    },
                    {
                        "case_id": "v21e-ui",
                        "label": "Create experiment/ui and switch to it",
                        "context": "You want to try a bold UI experiment on dashboard-frontend. Create a throwaway branch so you can iterate freely without risking the main codebase.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/app.py": "app-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch -c experiment/ui"],
                        "state_requirements": {
                            "head_branch": "experiment/ui",
                            "branch_exists": ["experiment/ui"],
                            "branch_points_to": {"experiment/ui": "c1"},
                        },
                    },
                    {
                        "case_id": "bc-easy-capstone-db",
                        "label": "Create feature/database-models and switch to it",
                        "context": 'Your group just initialized the capstone repo. The main branch has one commit. Your group lead says: "Before we start coding, everyone creates their own feature branch from main." Create feature/database-models and start working there.',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/app.py": "app-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch -c feature/database-models"],
                        "state_requirements": {
                            "head_branch": "feature/database-models",
                            "branch_exists": ["feature/database-models"],
                            "branch_points_to": {"feature/database-models": "c1"},
                        },
                    },
                    {
                        "case_id": "bc-easy-corp-hotfix",
                        "label": "Create hotfix/session-timeout and switch to it",
                        "context": 'A production incident was just reported. Your team lead pings you: "Branch off main right now and start the hotfix." You are already on main at the latest commit. Create hotfix/session-timeout and move to it immediately.',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/app.py": "app-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch -c hotfix/session-timeout"],
                        "state_requirements": {
                            "head_branch": "hotfix/session-timeout",
                            "branch_exists": ["hotfix/session-timeout"],
                            "branch_points_to": {"hotfix/session-timeout": "c1"},
                        },
                    },
                ],
            },
            "medium": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "Create a branch at the current HEAD of a multi-commit repository.",
                "task": "Inspect the history to confirm your starting point, then create the branch and move to it.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "v21m-payments",
                        "label": "Create feature/payments from the 2-commit main tip",
                        "context": "The e-commerce team's backlog just moved feature/payments to in-progress. Main has two commits of foundation work. Branch off the current tip to start the payments feature.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap e-commerce app",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Add product catalog",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/catalog.py": "catalog-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch -c feature/payments"],
                        "state_requirements": {
                            "head_branch": "feature/payments",
                            "branch_exists": ["feature/payments"],
                            "branch_points_to": {"feature/payments": "c2"},
                        },
                    },
                    {
                        "case_id": "v21m-notifications",
                        "label": "Create feature/notifications from the 3-commit main tip",
                        "context": "The messaging-app product roadmap calls for push notifications this sprint. Main has three commits of core infrastructure. Create your feature branch from the current tip.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap messaging app",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Add message queue",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/queue.py": "queue-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Add delivery tracking",
                                    "parents": ["c2"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/queue.py": "queue-v1",
                                        "src/tracking.py": "tracking-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c3"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch -c feature/notifications"],
                        "state_requirements": {
                            "head_branch": "feature/notifications",
                            "branch_exists": ["feature/notifications"],
                            "branch_points_to": {"feature/notifications": "c3"},
                        },
                    },
                    {
                        "case_id": "v21m-export",
                        "label": "Create feature/export from the 4-commit main tip",
                        "context": "The report-generator team needs a CSV export feature for the next release. Main has four commits of existing renderer work. Branch from the tip to begin.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap report generator",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Add data ingest",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/ingest.py": "ingest-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Add aggregation",
                                    "parents": ["c2"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/ingest.py": "ingest-v1",
                                        "src/aggregate.py": "aggregate-v1",
                                    },
                                },
                                {
                                    "id": "c4",
                                    "message": "Add renderer",
                                    "parents": ["c3"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/ingest.py": "ingest-v1",
                                        "src/aggregate.py": "aggregate-v1",
                                        "src/render.py": "render-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c4"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch -c feature/export"],
                        "state_requirements": {
                            "head_branch": "feature/export",
                            "branch_exists": ["feature/export"],
                            "branch_points_to": {"feature/export": "c4"},
                        },
                    },
                    {
                        "case_id": "bc-med-oss-develop",
                        "label": "Create feature/docs-update from develop's tip",
                        "context": "You've forked an OSS project and cloned it locally. The active development branch is develop, not main. Your mentor told you to branch off develop to start your contribution. You are currently on develop.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap OSS project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Refactor core",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/core.py": "core-v2"},
                                },
                            ],
                            "branches": {"develop": "c2", "main": "c1"},
                            "head": {"type": "branch", "name": "develop"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch -c feature/docs-update"],
                        "state_requirements": {
                            "head_branch": "feature/docs-update",
                            "branch_exists": ["feature/docs-update"],
                            "branch_points_to": {"feature/docs-update": "c2"},
                        },
                    },
                ],
            },
            "hard": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "Create a branch that starts at a specific commit — not necessarily the current HEAD.",
                "task": "Read the repository history carefully to identify the correct starting point before creating the branch.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "v21h-hotfix-c1",
                        "label": "Create hotfix/critical at c1 (not HEAD)",
                        "context": "A critical regression was found in order-service that only affects the v1.0 release code. Main has moved on since then. You need to branch off the v1.0 snapshot commit, not the current tip.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Release v1.0 snapshot",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/orders.py": "orders-v1",
                                    },
                                },
                                {
                                    "id": "c2",
                                    "message": "Add bulk order support",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/orders.py": "orders-v2",
                                        "src/bulk.py": "bulk-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch -c hotfix/critical c1"],
                        "state_requirements": {
                            "rules": [
                                {"type": "head_branch_equals", "branch": "hotfix/critical"},
                                {
                                    "type": "branch_points_to",
                                    "branch": "hotfix/critical",
                                    "commit": "c1",
                                },
                            ]
                        },
                    },
                    {
                        "case_id": "v21h-detach-save",
                        "label": "Create saved-work at the detached HEAD position",
                        "context": "You ran git checkout on an older commit to inspect it and ended up in detached HEAD state. Your work isn't lost — create a branch here to preserve this position before switching back.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial experiment setup",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Experimental changes at detached HEAD",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/experiment.py": "exp-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Latest main progress",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v2", "src/main.py": "main-v1"},
                                },
                            ],
                            "branches": {"main": "c3"},
                            "head": {"type": "detached", "target": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch -c saved-work"],
                        "state_requirements": {
                            "rules": [
                                {"type": "head_branch_equals", "branch": "saved-work"},
                                {
                                    "type": "branch_points_to",
                                    "branch": "saved-work",
                                    "commit": "c2",
                                },
                            ]
                        },
                    },
                    {
                        "case_id": "v21h-from-develop",
                        "label": "Create feature/workspace from develop's tip",
                        "context": "Your OSS project uses develop as the active integration branch, not main. You need to branch off develop's tip to start your contribution, not main.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap ide platform",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Stable main snapshot",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "editor.py": "editor-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Develop: add plugin system",
                                    "parents": ["c2"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "editor.py": "editor-v1",
                                        "src/plugins.py": "plugins-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c2", "develop": "c3"},
                            "head": {"type": "branch", "name": "develop"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch -c feature/workspace"],
                        "state_requirements": {
                            "rules": [
                                {"type": "head_branch_equals", "branch": "feature/workspace"},
                                {
                                    "type": "branch_points_to",
                                    "branch": "feature/workspace",
                                    "commit": "c3",
                                },
                            ]
                        },
                    },
                    {
                        "case_id": "bc-hard-review-snap",
                        "label": "Create review/v1-snapshot at c1, then return to main",
                        "context": "You needed to review an older commit and ran git checkout c1 -- now you are in detached HEAD state. You realize you should have just created a branch called review/v1-snapshot at that older commit to review it properly, so you can switch back to main later without losing the pointer.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial release snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Latest main work",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v2", "src/app.py": "app-v1"},
                                },
                            ],
                            "branches": {"main": "c2"},
                            "head": {"type": "detached", "target": "c1"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git switch -c review/v1-snapshot",
                            "git switch main",
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "branch_exists": ["review/v1-snapshot"],
                        },
                    },
                ],
            },
        },
    },
    {
        "sort_order": 2,
        "slug": "branch-naming-and-housekeeping",
        "title": "Branch Naming Conventions",
        "description": "Apply team branch naming conventions correctly and recognize names that violate them.",
        "tiers": {
            "easy": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "Create a branch whose exact name is given — apply the convention precisely.",
                "task": "Your team lead has told you both the convention and the required branch name. Create it exactly as specified — wrong casing, wrong separators, or wrong order will fail.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "bn-easy-corp-jira",
                        "label": "Create PROJ-418/password-reset",
                        "context": 'It\'s your first week at a software company. Your team lead sends you a message: "We name all branches PROJ-{ticket-number}/{kebab-case-description}. No exceptions -- the CI pipeline uses this pattern to link branches to tickets. Your first task is PROJ-418: implement the password reset flow. Branch name: PROJ-418/password-reset."',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/app.py": "app-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch -c PROJ-418/password-reset"],
                        "state_requirements": {
                            "head_branch": "PROJ-418/password-reset",
                            "branch_exists": ["PROJ-418/password-reset"],
                            "branch_points_to": {"PROJ-418/password-reset": "c1"},
                        },
                    },
                    {
                        "case_id": "bn-easy-startup-feat",
                        "label": "Create feature/shopping-cart",
                        "context": 'Your tech lead explains during onboarding: "We use type/description -- type is one of feature, bugfix, hotfix, or chore, separated by a slash, description in kebab-case. You\'re starting work on the shopping cart. Branch: feature/shopping-cart."',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/app.py": "app-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch -c feature/shopping-cart"],
                        "state_requirements": {
                            "head_branch": "feature/shopping-cart",
                            "branch_exists": ["feature/shopping-cart"],
                            "branch_points_to": {"feature/shopping-cart": "c1"},
                        },
                    },
                    {
                        "case_id": "bn-easy-oss-user",
                        "label": "Create jdelacruz/fix-parser-edge-case",
                        "context": 'The project\'s CONTRIBUTING.md states: "All branches from contributors must follow <github-username>/<kebab-case-description>. This lets maintainers identify whose work is whose at a glance." Your GitHub username is jdelacruz. You are fixing a parser edge case. Required branch: jdelacruz/fix-parser-edge-case.',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/app.py": "app-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch -c jdelacruz/fix-parser-edge-case"],
                        "state_requirements": {
                            "head_branch": "jdelacruz/fix-parser-edge-case",
                            "branch_exists": ["jdelacruz/fix-parser-edge-case"],
                            "branch_points_to": {"jdelacruz/fix-parser-edge-case": "c1"},
                        },
                    },
                    {
                        "case_id": "bn-easy-cap-initials",
                        "label": "Create feature/jm/database-models",
                        "context": "Your group agreed on a naming convention during your first sprint meeting: feature/<member-initials>/<short-description>. Your initials are jm. You are starting the database models module. Required branch: feature/jm/database-models.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/app.py": "app-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch -c feature/jm/database-models"],
                        "state_requirements": {
                            "head_branch": "feature/jm/database-models",
                            "branch_exists": ["feature/jm/database-models"],
                            "branch_points_to": {"feature/jm/database-models": "c1"},
                        },
                    },
                    {
                        "case_id": "bn-easy-free-client",
                        "label": "Create client/55-contact-form-redesign",
                        "context": 'Your client\'s project manager sends you the repo access with a note: "Please follow our branch naming: client/{ticket-id}-{description}. Your task is ticket #55: redesign the contact form. Branch: client/55-contact-form-redesign."',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/app.py": "app-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch -c client/55-contact-form-redesign"],
                        "state_requirements": {
                            "head_branch": "client/55-contact-form-redesign",
                            "branch_exists": ["client/55-contact-form-redesign"],
                            "branch_points_to": {"client/55-contact-form-redesign": "c1"},
                        },
                    },
                ],
            },
            "medium": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "Construct the correct branch name from the convention and task description.",
                "task": "You know the convention and the task. Derive the branch name yourself — there is only one correct slug. Abbreviations, wrong casing, and wrong type prefixes all fail.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "bn-med-corp-notif",
                        "label": "Construct and create PROJ-512/email-notification",
                        "context": 'Your team lead reminds you: "Convention is PROJ-{ticket}/{kebab-case-description}." Your new task is PROJ-512: implement the email notification service. Create the branch -- the description component must be email-notification.',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/app.py": "app-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch -c PROJ-512/email-notification"],
                        "state_requirements": {
                            "head_branch": "PROJ-512/email-notification",
                            "branch_exists": ["PROJ-512/email-notification"],
                            "branch_points_to": {"PROJ-512/email-notification": "c1"},
                        },
                    },
                    {
                        "case_id": "bn-med-startup-bugfix",
                        "label": "Construct and create bugfix/login-redirect",
                        "context": "Convention: type/kebab-case-description where type is feature, bugfix, hotfix, or chore. You have been assigned to fix a broken login redirect. The description to use is login-redirect.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/app.py": "app-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch -c bugfix/login-redirect"],
                        "state_requirements": {
                            "head_branch": "bugfix/login-redirect",
                            "branch_exists": ["bugfix/login-redirect"],
                            "branch_points_to": {"bugfix/login-redirect": "c1"},
                        },
                    },
                    {
                        "case_id": "bn-med-devops-scope",
                        "label": "Construct and create infra/api-gateway/log-rotation",
                        "context": "Convention: <type>/<scope>/<description> where type is feat, fix, chore, or infra, and scope is the service name. You are adding log rotation to the api-gateway service. Description: log-rotation.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/app.py": "app-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch -c infra/api-gateway/log-rotation"],
                        "state_requirements": {
                            "head_branch": "infra/api-gateway/log-rotation",
                            "branch_exists": ["infra/api-gateway/log-rotation"],
                            "branch_points_to": {"infra/api-gateway/log-rotation": "c1"},
                        },
                    },
                    {
                        "case_id": "bn-med-oss-infer",
                        "label": "Infer the convention and create fix/tokenizer-crash",
                        "context": "No one told you the naming convention. You run git branch -a and see: origin/fix/lexer-null-check, origin/fix/parser-overflow, origin/feat/dark-mode, origin/feat/keyboard-shortcuts. You are fixing a crash in the tokenizer. The description to use is tokenizer-crash.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial project snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/app.py": "app-v1"},
                                }
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                            "remote_branches": {
                                "origin/fix/lexer-null-check": "c1",
                                "origin/fix/parser-overflow": "c1",
                                "origin/feat/dark-mode": "c1",
                                "origin/feat/keyboard-shortcuts": "c1",
                            },
                        },
                        "solution_commands": ["git switch -c fix/tokenizer-crash"],
                        "state_requirements": {
                            "head_branch": "fix/tokenizer-crash",
                            "branch_exists": ["fix/tokenizer-crash"],
                            "branch_points_to": {"fix/tokenizer-crash": "c1"},
                        },
                    },
                ],
            },
            "hard": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "Identify a branch name that violates the convention and correct it.",
                "task": "A branch already exists with the wrong name. Figure out what the violation is, delete the non-compliant branch, and create a correctly-named replacement.",
                "min_counted_commands": 2,
                "cases": [
                    {
                        "case_id": "bn-hard-oss-rename",
                        "label": "Delete myFix, create fix/renderer-memory-leak",
                        "context": 'A contributor created myFix before reading the project\'s CONTRIBUTING.md, which states: "Branch names must follow fix/<kebab-case-description> for bug fixes and feat/<kebab-case-description> for features. CamelCase and generic names are rejected by our CI check." The branch is for a memory leak in the renderer. The description is renderer-memory-leak. You are on main.',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap OSS project",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/renderer.py": "rend-v1",
                                    },
                                }
                            ],
                            "branches": {"main": "c1", "myFix": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git branch -D myFix",
                            "git switch -c fix/renderer-memory-leak",
                        ],
                        "state_requirements": {
                            "head_branch": "fix/renderer-memory-leak",
                            "branch_exists": ["fix/renderer-memory-leak"],
                            "branch_absent": ["myFix"],
                        },
                    },
                    {
                        "case_id": "bn-hard-corp-rename",
                        "label": "Delete auth-update, create PROJ-301/auth-module-update",
                        "context": "A new teammate created auth-update for ticket PROJ-301. Your team's CI pipeline requires PROJ-{ticket}/{description} -- branches that don't match are blocked from merging. Your team lead asks you to fix it before the PR review. The correct description is auth-module-update. The branch has no commits of its own yet. You are on main.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "auth-v1"},
                                }
                            ],
                            "branches": {"main": "c1", "auth-update": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git branch -D auth-update",
                            "git switch -c PROJ-301/auth-module-update",
                        ],
                        "state_requirements": {
                            "head_branch": "PROJ-301/auth-module-update",
                            "branch_exists": ["PROJ-301/auth-module-update"],
                            "branch_absent": ["auth-update"],
                        },
                    },
                    {
                        "case_id": "bn-hard-startup-prefix",
                        "label": "Delete fix/cart-total, create bugfix/cart-total",
                        "context": "Convention is feature/, bugfix/, hotfix/, or chore/ -- no other prefixes are valid. A branch called fix/cart-total exists (wrong prefix -- fix is not in the allowed list; should be bugfix). You are on main. The description stays cart-total.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap e-commerce app",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/cart.py": "cart-v1"},
                                }
                            ],
                            "branches": {"main": "c1", "fix/cart-total": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git branch -D fix/cart-total",
                            "git switch -c bugfix/cart-total",
                        ],
                        "state_requirements": {
                            "head_branch": "bugfix/cart-total",
                            "branch_exists": ["bugfix/cart-total"],
                            "branch_absent": ["fix/cart-total"],
                        },
                    },
                    {
                        "case_id": "bn-hard-qa-camel",
                        "label": "Delete test/LoginFlow, create test/login-flow",
                        "context": "Your QA team's convention (documented in the repo's README) is test/<kebab-case-description>. A branch test/LoginFlow was pushed by a junior tester -- the CamelCase violates the convention and breaks your test runner's branch name parser. You need to correct it. You are on main. The correct description is login-flow.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap QA suite",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "tests/login.py": "test-v1"},
                                }
                            ],
                            "branches": {"main": "c1", "test/LoginFlow": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git branch -D test/LoginFlow",
                            "git switch -c test/login-flow",
                        ],
                        "state_requirements": {
                            "head_branch": "test/login-flow",
                            "branch_exists": ["test/login-flow"],
                            "branch_absent": ["test/LoginFlow"],
                        },
                    },
                ],
            },
        },
    },
    {
        "sort_order": 3,
        "slug": "stashing-work-in-progress",
        "title": "Stashing Work in Progress",
        "description": "Temporarily shelve uncommitted changes to switch context and restore work cleanly.",
        "tiers": {
            "easy": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "Shelve your in-progress work and switch to another branch.",
                "task": "You have uncommitted changes and need to move to a different branch. Save your work first.",
                "min_counted_commands": 2,
                "cases": [
                    {
                        "case_id": "v23e-auth",
                        "label": "Stash auth work and switch to main",
                        "context": "You're mid-feature on the auth-service when an urgent bug report comes in on a different branch. Your current changes aren't ready to commit. Stash them and switch context.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial ticketing-app snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"feature/auth": "c1", "main": "c1"},
                            "head": {"type": "branch", "name": "feature/auth"},
                            "working_tree": {"src/auth.py": "auth-wip"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git stash", "git switch main"],
                        "state_requirements": {"working_tree_clean": True, "head_branch": "main"},
                    },
                    {
                        "case_id": "v23e-notify",
                        "label": "Stash notify work and switch to develop",
                        "context": "You've been editing notification templates when your team lead asks you to check something on another branch immediately. Stash your in-progress work first.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial messaging-service snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"feature/notify": "c1", "develop": "c1"},
                            "head": {"type": "branch", "name": "feature/notify"},
                            "working_tree": {"src/notify.py": "notify-wip"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git stash", "git switch develop"],
                        "state_requirements": {
                            "working_tree_clean": True,
                            "head_branch": "develop",
                        },
                    },
                    {
                        "case_id": "v23e-cache",
                        "label": "Stash cache work and switch to release/v2",
                        "context": "You're halfway through a cache refactor when a production alert fires. Stash what you have and switch to the hotfix branch.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial data-store snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"feature/cache": "c1", "release/v2": "c1"},
                            "head": {"type": "branch", "name": "feature/cache"},
                            "working_tree": {"src/cache.py": "cache-wip"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git stash", "git switch release/v2"],
                        "state_requirements": {
                            "working_tree_clean": True,
                            "head_branch": "release/v2",
                        },
                    },
                    {
                        "case_id": "stash-easy-cap-review",
                        "label": "Stash models work and switch to review/groupmate-branch",
                        "context": 'You are halfway through editing src/models.py on feature/models when your groupmate messages: "Can you review my branch?" Your changes are not ready to commit. Stash them and switch to review/groupmate-branch.',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial capstone-system snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"feature/models": "c1", "review/groupmate-branch": "c1"},
                            "head": {"type": "branch", "name": "feature/models"},
                            "working_tree": {"src/models.py": "models-wip"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git stash", "git switch review/groupmate-branch"],
                        "state_requirements": {
                            "working_tree_clean": True,
                            "head_branch": "review/groupmate-branch",
                            "rules": [{"type": "stash_stack_length_equals", "count": 1}],
                        },
                    },
                    {
                        "case_id": "stash-easy-docs-switch",
                        "label": "Stash docs work and switch to release/stable",
                        "context": "You are editing docs/api-reference.md on feature/api-docs. An urgent correction is needed on the release/stable branch right now. Your changes are not committed. Stash and switch to release/stable.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Initial docs-portal snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                }
                            ],
                            "branches": {"feature/api-docs": "c1", "release/stable": "c1"},
                            "head": {"type": "branch", "name": "feature/api-docs"},
                            "working_tree": {"docs/api-reference.md": "api-ref-wip"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git stash", "git switch release/stable"],
                        "state_requirements": {
                            "working_tree_clean": True,
                            "head_branch": "release/stable",
                            "rules": [{"type": "stash_stack_length_equals", "count": 1}],
                        },
                    },
                ],
            },
            "medium": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "Stash your work, check another branch, then return and restore.",
                "task": "An urgent context switch requires you to leave your feature branch temporarily. Preserve your work, check the other branch, then come back and pick up where you left off.",
                "min_counted_commands": 4,
                "cases": [
                    {
                        "case_id": "v23m-to-main",
                        "label": "Stash payments work, check main, restore",
                        "context": "You need to switch to main temporarily to review a teammate's commit. Stash your current work, switch, then come back and restore.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Payment feature in progress",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Main moves forward",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/app.py": "app-v1"},
                                },
                            ],
                            "branches": {"feature/payments": "c1", "main": "c2"},
                            "head": {"type": "branch", "name": "feature/payments"},
                            "working_tree": {"src/payments.py": "pay-wip"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git stash",
                            "git switch main",
                            "git switch feature/payments",
                            "git stash pop",
                        ],
                        "state_requirements": {
                            "rules": [{"type": "stash_stack_empty"}],
                            "head_branch": "feature/payments",
                            "working_tree_contains": ["src/payments.py"],
                        },
                    },
                    {
                        "case_id": "v23m-to-hotfix",
                        "label": "Stash orders work, check hotfix, restore",
                        "context": "A hotfix branch needs your attention right now. Stash your in-progress feature work, handle the hotfix, return to your branch, and restore your changes.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Orders feature base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Hotfix branch tip",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/tax.py": "tax-v1"},
                                },
                            ],
                            "branches": {"feature/orders": "c1", "hotfix/fix-tax": "c2"},
                            "head": {"type": "branch", "name": "feature/orders"},
                            "working_tree": {"src/orders.py": "ord-wip"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git stash",
                            "git switch hotfix/fix-tax",
                            "git switch feature/orders",
                            "git stash pop",
                        ],
                        "state_requirements": {
                            "rules": [{"type": "stash_stack_empty"}],
                            "head_branch": "feature/orders",
                            "working_tree_contains": ["src/orders.py"],
                        },
                    },
                    {
                        "case_id": "v23m-to-release",
                        "label": "Stash analytics work, check release/v2, restore",
                        "context": "The release branch needs a quick check before it goes out. Stash what you're working on, switch to release, then come back and pop.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Analytics feature base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Release v2 preparation",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/release.py": "release-v1",
                                    },
                                },
                            ],
                            "branches": {"feature/analytics": "c1", "release/v2": "c2"},
                            "head": {"type": "branch", "name": "feature/analytics"},
                            "working_tree": {"src/analytics.py": "ana-wip"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git stash",
                            "git switch release/v2",
                            "git switch feature/analytics",
                            "git stash pop",
                        ],
                        "state_requirements": {
                            "rules": [{"type": "stash_stack_empty"}],
                            "head_branch": "feature/analytics",
                            "working_tree_contains": ["src/analytics.py"],
                        },
                    },
                    {
                        "case_id": "stash-med-corp-named",
                        "label": "Stash billing work, check hotfix/tax-fix, restore",
                        "context": "You are mid-feature on feature/billing with changes to src/billing.py. An urgent request comes in to check hotfix/tax-fix. Stash your work with a descriptive message, check the hotfix branch, return to your feature branch, and restore your work.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Billing feature base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Hotfix branch tip",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/tax.py": "tax-v1"},
                                },
                            ],
                            "branches": {"feature/billing": "c1", "hotfix/tax-fix": "c2"},
                            "head": {"type": "branch", "name": "feature/billing"},
                            "working_tree": {"src/billing.py": "billing-wip"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git stash",
                            "git switch hotfix/tax-fix",
                            "git switch feature/billing",
                            "git stash pop",
                        ],
                        "state_requirements": {
                            "rules": [{"type": "stash_stack_empty"}],
                            "head_branch": "feature/billing",
                            "working_tree_contains": ["src/billing.py"],
                        },
                    },
                ],
            },
            "hard": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "Stash your work, inspect another branch, then discard the stashed changes.",
                "task": "After stashing your work and checking another branch, you learn the task has been cancelled. Return to your feature branch and clean up the stash.",
                "min_counted_commands": 4,
                "cases": [
                    {
                        "case_id": "v23h-dropped-auth",
                        "label": "Stash and drop cancelled auth rework",
                        "context": "You stashed auth work to help with a hotfix but have now decided to abandon that auth experiment entirely. Switch to the target branch and drop the stash instead of popping it.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Auth rework in progress",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Main moves forward",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/app.py": "app-v1"},
                                },
                            ],
                            "branches": {"feature/auth-rework": "c1", "main": "c2"},
                            "head": {"type": "branch", "name": "feature/auth-rework"},
                            "working_tree": {"src/auth.py": "auth-wip"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git stash",
                            "git switch main",
                            "git switch feature/auth-rework",
                            "git stash drop",
                        ],
                        "state_requirements": {
                            "rules": [{"type": "stash_stack_empty"}],
                            "head_branch": "feature/auth-rework",
                            "working_tree_clean": True,
                        },
                    },
                    {
                        "case_id": "v23h-dropped-api",
                        "label": "Stash and drop cancelled api-v2 work",
                        "context": "You stashed API changes but realized they conflict with the new architecture. Drop the stash -- don't restore it.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "API v2 prototype started",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Hotfix committed",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/fix.py": "fix-v1"},
                                },
                            ],
                            "branches": {"feature/api-v2": "c1", "hotfix/urgent": "c2"},
                            "head": {"type": "branch", "name": "feature/api-v2"},
                            "working_tree": {"src/api_v2.py": "api-wip"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git stash",
                            "git switch hotfix/urgent",
                            "git switch feature/api-v2",
                            "git stash drop",
                        ],
                        "state_requirements": {
                            "rules": [{"type": "stash_stack_empty"}],
                            "head_branch": "feature/api-v2",
                            "working_tree_clean": True,
                        },
                    },
                    {
                        "case_id": "v23h-dropped-refactor",
                        "label": "Stash and drop cancelled refactor",
                        "context": "You stashed a refactor mid-way but the team decided to go a different direction. Stash, switch, and drop.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Refactor started",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Release v1 stable",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/app.py": "app-v1"},
                                },
                            ],
                            "branches": {"feature/refactor": "c1", "release/v1": "c2"},
                            "head": {"type": "branch", "name": "feature/refactor"},
                            "working_tree": {"src/core.py": "core-wip"},
                            "staging": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git stash",
                            "git switch release/v1",
                            "git switch feature/refactor",
                            "git stash drop",
                        ],
                        "state_requirements": {
                            "rules": [{"type": "stash_stack_empty"}],
                            "head_branch": "feature/refactor",
                            "working_tree_clean": True,
                        },
                    },
                    {
                        "case_id": "stash-hard-oss-multi",
                        "label": "Drop stash@{0} and pop the remaining stash",
                        "context": "You have two entries in the stash from previous context switches. stash@{0} is a dead-end experiment you abandoned. stash@{1} is the work you actually need to restore on feature/lexer. Drop only stash@{0}, then pop the remaining entry.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Lexer feature base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                            ],
                            "branches": {"feature/lexer": "c1"},
                            "head": {"type": "branch", "name": "feature/lexer"},
                            "working_tree": {},
                            "staging": {},
                            "conflicts": [],
                            "stash_stack": [
                                {
                                    "working_tree": {"src/experiment.py": "exp-wip"},
                                    "staging": {},
                                    "conflicts": [],
                                },
                                {
                                    "working_tree": {"src/lexer.py": "lexer-wip"},
                                    "staging": {},
                                    "conflicts": [],
                                },
                            ],
                        },
                        "solution_commands": ["git stash drop stash@{0}", "git stash pop"],
                        "state_requirements": {
                            "rules": [{"type": "stash_stack_empty"}],
                            "head_branch": "feature/lexer",
                        },
                    },
                ],
            },
        },
    },
    {
        "sort_order": 4,
        "slug": "pushing-to-a-remote",
        "title": "Pushing to a Remote",
        "description": "Publish local commits to a shared remote repository and set up tracking.",
        "tiers": {
            "easy": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "Push a new local branch to origin for the first time.",
                "task": "Your feature work is ready to share. Publish the branch to the remote so teammates can access it.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "v24e-auth",
                        "label": "Push feature/auth to origin",
                        "context": "You finished the auth feature branch locally. Now publish it to origin so your teammates can review and pull it.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Implement feature",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/auth.py": "feat-auth-v1",
                                    },
                                },
                            ],
                            "branches": {"feature/auth": "c2", "main": "c1"},
                            "head": {"type": "branch", "name": "feature/auth"},
                            "remotes": {"origin": "https://github.com/team/ticketing-app.git"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git push origin feature/auth"],
                        "state_requirements": {
                            "remote_branch_matches_local": {"origin/feature/auth": "feature/auth"}
                        },
                    },
                    {
                        "case_id": "v24e-orders",
                        "label": "Push feature/orders to origin",
                        "context": "The orders feature is complete on your local branch. Push it to the shared remote so the team can access it.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Implement feature",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/orders.py": "feat-orders-v1",
                                    },
                                },
                            ],
                            "branches": {"feature/orders": "c2", "main": "c1"},
                            "head": {"type": "branch", "name": "feature/orders"},
                            "remotes": {"origin": "https://github.com/team/e-commerce.git"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git push origin feature/orders"],
                        "state_requirements": {
                            "remote_branch_matches_local": {
                                "origin/feature/orders": "feature/orders"
                            }
                        },
                    },
                    {
                        "case_id": "v24e-parser",
                        "label": "Push feature/parser to origin",
                        "context": "Your parser fix is committed locally. Share it by pushing the branch to origin.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Implement feature",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/parser.py": "feat-parser-v1",
                                    },
                                },
                            ],
                            "branches": {"feature/parser": "c2", "main": "c1"},
                            "head": {"type": "branch", "name": "feature/parser"},
                            "remotes": {"origin": "https://github.com/team/data-pipeline.git"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git push origin feature/parser"],
                        "state_requirements": {
                            "remote_branch_matches_local": {
                                "origin/feature/parser": "feature/parser"
                            }
                        },
                    },
                    {
                        "case_id": "push-easy-cap-auth",
                        "label": "Push feature/user-auth to origin",
                        "context": "Your group finished the feature/user-auth branch. Your repo has a remote origin set up. Push the branch so your groupmates can access it. No upstream tracking needed yet -- just share the commits.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Implement user auth",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "auth-v1"},
                                },
                            ],
                            "branches": {"feature/user-auth": "c2", "main": "c1"},
                            "head": {"type": "branch", "name": "feature/user-auth"},
                            "remotes": {"origin": "https://github.com/team/capstone-app.git"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git push origin feature/user-auth"],
                        "state_requirements": {
                            "remote_branch_matches_local": {
                                "origin/feature/user-auth": "feature/user-auth"
                            }
                        },
                    },
                    {
                        "case_id": "push-easy-free-landing",
                        "label": "Push feature/client-landing to origin",
                        "context": "You finished feature/client-landing. The client's repo is set as origin. Push the branch so the client can review it. No tracking setup needed.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Implement client landing page",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/landing.py": "landing-v1",
                                    },
                                },
                            ],
                            "branches": {"feature/client-landing": "c2", "main": "c1"},
                            "head": {"type": "branch", "name": "feature/client-landing"},
                            "remotes": {"origin": "https://github.com/client/client-site.git"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git push origin feature/client-landing"],
                        "state_requirements": {
                            "remote_branch_matches_local": {
                                "origin/feature/client-landing": "feature/client-landing"
                            }
                        },
                    },
                ],
            },
            "medium": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "Push and configure upstream tracking so future pushes and pulls work without arguments.",
                "task": "Push the branch and link it to its remote counterpart so you can sync with just git push or git pull.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "v24m-auth",
                        "label": "Push feature/auth with -u",
                        "context": "You want future git push calls to work without specifying the remote. Push the auth branch to origin and set up upstream tracking at the same time.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Implement feature",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/auth.py": "feat-auth-v1",
                                    },
                                },
                            ],
                            "branches": {"feature/auth": "c2", "main": "c1"},
                            "head": {"type": "branch", "name": "feature/auth"},
                            "remotes": {"origin": "https://github.com/team/ticketing-app.git"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git push -u origin feature/auth"],
                        "state_requirements": {
                            "remote_branch_matches_local": {"origin/feature/auth": "feature/auth"},
                            "upstream_tracking_set": ["feature/auth"],
                        },
                    },
                    {
                        "case_id": "v24m-orders",
                        "label": "Push feature/orders with -u",
                        "context": "Push the orders branch and configure tracking so your local branch automatically syncs with origin/orders-feature on future operations.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Implement feature",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/orders.py": "feat-orders-v1",
                                    },
                                },
                            ],
                            "branches": {"feature/orders": "c2", "main": "c1"},
                            "head": {"type": "branch", "name": "feature/orders"},
                            "remotes": {"origin": "https://github.com/team/e-commerce.git"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git push -u origin feature/orders"],
                        "state_requirements": {
                            "remote_branch_matches_local": {
                                "origin/feature/orders": "feature/orders"
                            },
                            "upstream_tracking_set": ["feature/orders"],
                        },
                    },
                    {
                        "case_id": "v24m-parser",
                        "label": "Push feature/parser with -u",
                        "context": "Set up tracking while pushing the parser branch so you can run git push and git pull without arguments going forward.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Implement feature",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/parser.py": "feat-parser-v1",
                                    },
                                },
                            ],
                            "branches": {"feature/parser": "c2", "main": "c1"},
                            "head": {"type": "branch", "name": "feature/parser"},
                            "remotes": {"origin": "https://github.com/team/data-pipeline.git"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git push -u origin feature/parser"],
                        "state_requirements": {
                            "remote_branch_matches_local": {
                                "origin/feature/parser": "feature/parser"
                            },
                            "upstream_tracking_set": ["feature/parser"],
                        },
                    },
                    {
                        "case_id": "push-med-docs-track",
                        "label": "Push feature/v2-migration-guide with -u",
                        "context": "You finished the feature/v2-migration-guide documentation branch. Push it to origin AND set up upstream tracking so future syncs use just git push.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Add v2 migration guide",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "docs/migration.md": "migration-v1",
                                    },
                                },
                            ],
                            "branches": {"feature/v2-migration-guide": "c2", "main": "c1"},
                            "head": {"type": "branch", "name": "feature/v2-migration-guide"},
                            "remotes": {"origin": "https://github.com/team/docs-portal.git"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git push -u origin feature/v2-migration-guide"],
                        "state_requirements": {
                            "remote_branch_matches_local": {
                                "origin/feature/v2-migration-guide": "feature/v2-migration-guide"
                            },
                            "upstream_tracking_set": ["feature/v2-migration-guide"],
                        },
                    },
                ],
            },
            "hard": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "Publish a rebased branch whose history diverges from the remote.",
                "task": "After rebasing, a normal push is rejected because the remote history no longer matches. Use the safe force-push option.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "v24h-auth",
                        "label": "Force-push rebased feature/auth safely",
                        "context": "You rebased the auth branch to clean up the commit history before the PR. The remote still has the original linear history. A normal push is rejected -- use the safe force-push option.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common ancestor",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Original feature commit (remote still here)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "old-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Rebased feature commit (local, diverged from remote)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "new-v1"},
                                },
                            ],
                            "branches": {"feature/auth": "c3", "main": "c1"},
                            "head": {"type": "branch", "name": "feature/auth"},
                            "remotes": {"origin": "https://github.com/team/ticketing-app.git"},
                            "remote_branches": {"origin/feature/auth": "c2"},
                            "upstream_tracking": {"feature/auth": "origin/feature/auth"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git push --force-with-lease origin feature/auth"],
                        "state_requirements": {
                            "remote_branch_matches_local": {"origin/feature/auth": "feature/auth"}
                        },
                    },
                    {
                        "case_id": "v24h-orders",
                        "label": "Force-push rebased feature/orders safely",
                        "context": "After an interactive rebase on the orders branch, the remote history diverged. Force-push safely without risking someone else's work getting overwritten.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common ancestor",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Original feature commit (remote still here)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/orders.py": "old-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Rebased feature commit (local, diverged from remote)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/orders.py": "new-v1"},
                                },
                            ],
                            "branches": {"feature/orders": "c3", "main": "c1"},
                            "head": {"type": "branch", "name": "feature/orders"},
                            "remotes": {"origin": "https://github.com/team/e-commerce.git"},
                            "remote_branches": {"origin/feature/orders": "c2"},
                            "upstream_tracking": {"feature/orders": "origin/feature/orders"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git push --force-with-lease origin feature/orders"],
                        "state_requirements": {
                            "remote_branch_matches_local": {
                                "origin/feature/orders": "feature/orders"
                            }
                        },
                    },
                    {
                        "case_id": "v24h-parser",
                        "label": "Force-push rebased feature/parser safely",
                        "context": "You squashed commits on the parser branch during rebase cleanup. The remote branch has the pre-squash history. Use force-with-lease to push safely.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common ancestor",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Original feature commit (remote still here)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/parser.py": "old-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Rebased feature commit (local, diverged from remote)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/parser.py": "new-v1"},
                                },
                            ],
                            "branches": {"feature/parser": "c3", "main": "c1"},
                            "head": {"type": "branch", "name": "feature/parser"},
                            "remotes": {"origin": "https://github.com/team/data-pipeline.git"},
                            "remote_branches": {"origin/feature/parser": "c2"},
                            "upstream_tracking": {"feature/parser": "origin/feature/parser"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git push --force-with-lease origin feature/parser"],
                        "state_requirements": {
                            "remote_branch_matches_local": {
                                "origin/feature/parser": "feature/parser"
                            }
                        },
                    },
                    {
                        "case_id": "push-hard-devops-fwl",
                        "label": "Force-push rebased feature/pipeline-config safely",
                        "context": "Your CI team required you to rebase feature/pipeline-config to squash debug commits before merging. You've done the rebase locally. The remote origin/feature/pipeline-config still has the original linear history. A normal git push is rejected. Use the safe force-push option -- do not use bare --force.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common ancestor",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Original pipeline commit (remote still here)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/pipeline.py": "old-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Rebased pipeline commit (local, diverged from remote)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/pipeline.py": "new-v1"},
                                },
                            ],
                            "branches": {"feature/pipeline-config": "c3", "main": "c1"},
                            "head": {"type": "branch", "name": "feature/pipeline-config"},
                            "remotes": {"origin": "https://github.com/team/devops-infra.git"},
                            "remote_branches": {"origin/feature/pipeline-config": "c2"},
                            "upstream_tracking": {
                                "feature/pipeline-config": "origin/feature/pipeline-config"
                            },
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git push --force-with-lease origin feature/pipeline-config"
                        ],
                        "state_requirements": {
                            "remote_branch_matches_local": {
                                "origin/feature/pipeline-config": "feature/pipeline-config"
                            }
                        },
                    },
                ],
            },
        },
    },
    {
        "sort_order": 5,
        "slug": "fetching-and-pulling",
        "title": "Fetching and Pulling from a Remote",
        "description": "Bring remote changes into the local repository and keep local branches up to date.",
        "tiers": {
            "easy": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "Update remote tracking refs by fetching from origin.",
                "task": "Your remote tracking refs may be stale. Fetch to see what your teammates have pushed, without modifying your local branches.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "v25e-main",
                        "label": "Fetch to update origin/main tracking",
                        "context": "Your teammate says they just pushed to main. Before you pull, you want to see what arrived on origin/main without merging anything yet.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Baseline snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "New remote work not yet fetched",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/feature.py": "remote-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "remotes": {"origin": "https://github.com/team/ticketing-app.git"},
                            "remote_branches": {"origin/main": "c1"},
                            "remote_updates": {"origin/main": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git fetch origin"],
                        "state_requirements": {
                            "remote_tracking_updated": True,
                            "remote_branch_points_to": {"origin/main": "c2"},
                        },
                    },
                    {
                        "case_id": "v25e-feature",
                        "label": "Fetch to update origin/feature/auth tracking",
                        "context": "Someone pushed a new commit to the shared feature branch. Fetch to update your remote-tracking refs so you can inspect what changed.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Baseline snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "New remote work not yet fetched",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "remote-v1"},
                                },
                            ],
                            "branches": {"feature/auth": "c1"},
                            "head": {"type": "branch", "name": "feature/auth"},
                            "remotes": {"origin": "https://github.com/team/auth-service.git"},
                            "remote_branches": {"origin/feature/auth": "c1"},
                            "remote_updates": {"origin/feature/auth": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git fetch origin"],
                        "state_requirements": {
                            "remote_tracking_updated": True,
                            "remote_branch_points_to": {"origin/feature/auth": "c2"},
                        },
                    },
                    {
                        "case_id": "v25e-develop",
                        "label": "Fetch to update origin/develop tracking",
                        "context": "The develop branch on origin has been updated by another team member. Fetch to bring your remote tracking refs up to date.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Baseline snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "New remote work not yet fetched",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/api.py": "remote-v1"},
                                },
                            ],
                            "branches": {"develop": "c1"},
                            "head": {"type": "branch", "name": "develop"},
                            "remotes": {"origin": "https://github.com/team/api-gateway.git"},
                            "remote_branches": {"origin/develop": "c1"},
                            "remote_updates": {"origin/develop": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git fetch origin"],
                        "state_requirements": {
                            "remote_tracking_updated": True,
                            "remote_branch_points_to": {"origin/develop": "c2"},
                        },
                    },
                    {
                        "case_id": "fetch-easy-cap-check",
                        "label": "Fetch to update origin/feature/models tracking",
                        "context": 'Your groupmate says "I pushed our model classes to the feature/models branch." You want to see what was pushed to origin/feature/models before deciding whether to pull. Run fetch to update your remote tracking refs without touching your local branches.',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Baseline snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Groupmate pushed model classes",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/models.py": "models-v1",
                                    },
                                },
                            ],
                            "branches": {"feature/models": "c1"},
                            "head": {"type": "branch", "name": "feature/models"},
                            "remotes": {"origin": "https://github.com/team/capstone-app.git"},
                            "remote_branches": {"origin/feature/models": "c1"},
                            "remote_updates": {"origin/feature/models": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git fetch origin"],
                        "state_requirements": {
                            "remote_tracking_updated": True,
                            "remote_branch_points_to": {"origin/feature/models": "c2"},
                        },
                    },
                    {
                        "case_id": "fetch-easy-corp-list",
                        "label": "Fetch to update origin/release/v2 tracking",
                        "context": "A new release branch release/v2 was pushed to the remote by the release engineer. You want to see it in your local remote-tracking refs. Fetch from origin.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Baseline snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Release v2 preparation",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/audit.py": "audit-v1"},
                                },
                            ],
                            "branches": {"release/v2": "c1"},
                            "head": {"type": "branch", "name": "release/v2"},
                            "remotes": {"origin": "https://github.com/team/corp-backend.git"},
                            "remote_branches": {"origin/release/v2": "c1"},
                            "remote_updates": {"origin/release/v2": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git fetch origin"],
                        "state_requirements": {
                            "remote_tracking_updated": True,
                            "remote_branch_points_to": {"origin/release/v2": "c2"},
                        },
                    },
                ],
            },
            "medium": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "Pull remote commits to fast-forward the local branch.",
                "task": "A teammate has pushed new commits. Pull to integrate them into your local branch.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "v25m-main",
                        "label": "Pull origin/main into local main",
                        "context": "Origin/main has new commits from your team. Pull them into your local main branch to stay in sync.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Baseline snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Teammate committed to remote",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/feature.py": "remote-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "remotes": {"origin": "https://github.com/team/ticketing-app.git"},
                            "remote_branches": {"origin/main": "c1"},
                            "upstream_tracking": {"main": "origin/main"},
                            "remote_updates": {"origin/main": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git pull origin main"],
                        "state_requirements": {
                            "remote_branch_matches_local": {"origin/main": "main"}
                        },
                    },
                    {
                        "case_id": "v25m-feature",
                        "label": "Pull origin/feature/auth into local feature/auth",
                        "context": "The shared feature branch has new commits from a teammate. Pull to integrate them into your local copy.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Baseline snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Teammate committed to remote",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "remote-v1"},
                                },
                            ],
                            "branches": {"feature/auth": "c1"},
                            "head": {"type": "branch", "name": "feature/auth"},
                            "remotes": {"origin": "https://github.com/team/auth-service.git"},
                            "remote_branches": {"origin/feature/auth": "c1"},
                            "upstream_tracking": {"feature/auth": "origin/feature/auth"},
                            "remote_updates": {"origin/feature/auth": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git pull origin feature/auth"],
                        "state_requirements": {
                            "remote_branch_matches_local": {"origin/feature/auth": "feature/auth"}
                        },
                    },
                    {
                        "case_id": "v25m-develop",
                        "label": "Pull origin/develop into local develop",
                        "context": "The develop branch on origin has moved ahead. Pull to fast-forward your local develop to match.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Baseline snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Teammate committed to remote",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/api.py": "remote-v1"},
                                },
                            ],
                            "branches": {"develop": "c1"},
                            "head": {"type": "branch", "name": "develop"},
                            "remotes": {"origin": "https://github.com/team/api-gateway.git"},
                            "remote_branches": {"origin/develop": "c1"},
                            "upstream_tracking": {"develop": "origin/develop"},
                            "remote_updates": {"origin/develop": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git pull origin develop"],
                        "state_requirements": {
                            "remote_branch_matches_local": {"origin/develop": "develop"}
                        },
                    },
                    {
                        "case_id": "pull-med-free-client",
                        "label": "Pull origin/staging into local staging",
                        "context": "Your client pushed new content to origin/staging. You need it in your local staging branch before you continue. Your upstream tracking is already set. Pull to integrate.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Baseline snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Client pushed new content",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/content.py": "content-v1",
                                    },
                                },
                            ],
                            "branches": {"staging": "c1"},
                            "head": {"type": "branch", "name": "staging"},
                            "remotes": {"origin": "https://github.com/client/client-site.git"},
                            "remote_branches": {"origin/staging": "c1"},
                            "upstream_tracking": {"staging": "origin/staging"},
                            "remote_updates": {"origin/staging": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git pull origin staging"],
                        "state_requirements": {
                            "remote_branch_matches_local": {"origin/staging": "staging"}
                        },
                    },
                ],
            },
            "hard": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "Fetch first to inspect what changed, then pull to integrate.",
                "task": "You want to see what is on the remote before integrating it. Fetch to update remote tracking refs, review, then pull.",
                "min_counted_commands": 2,
                "cases": [
                    {
                        "case_id": "v25h-main",
                        "label": "Fetch then pull origin/main",
                        "context": "Before integrating the latest main changes, you want to inspect what arrived. Fetch first to see the remote state, then pull to integrate.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Baseline snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Teammate committed to remote",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/feature.py": "remote-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "remotes": {"origin": "https://github.com/team/ticketing-app.git"},
                            "remote_branches": {"origin/main": "c1"},
                            "remote_updates": {"origin/main": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git fetch origin", "git pull origin main"],
                        "state_requirements": {
                            "remote_branch_matches_local": {"origin/main": "main"}
                        },
                    },
                    {
                        "case_id": "v25h-feature",
                        "label": "Fetch then pull origin/feature/auth",
                        "context": "You want to review origin/feature before merging it locally. Fetch to update tracking refs, review, then pull to integrate.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Baseline snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Teammate committed to remote",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "remote-v1"},
                                },
                            ],
                            "branches": {"feature/auth": "c1"},
                            "head": {"type": "branch", "name": "feature/auth"},
                            "remotes": {"origin": "https://github.com/team/auth-service.git"},
                            "remote_branches": {"origin/feature/auth": "c1"},
                            "remote_updates": {"origin/feature/auth": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git fetch origin", "git pull origin feature/auth"],
                        "state_requirements": {
                            "remote_branch_matches_local": {"origin/feature/auth": "feature/auth"}
                        },
                    },
                    {
                        "case_id": "v25h-develop",
                        "label": "Fetch then pull origin/develop",
                        "context": "The develop branch has several new upstream commits. Fetch first to inspect, then pull to integrate into your local develop.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Baseline snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Teammate committed to remote",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/api.py": "remote-v1"},
                                },
                            ],
                            "branches": {"develop": "c1"},
                            "head": {"type": "branch", "name": "develop"},
                            "remotes": {"origin": "https://github.com/team/api-gateway.git"},
                            "remote_branches": {"origin/develop": "c1"},
                            "remote_updates": {"origin/develop": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git fetch origin", "git pull origin develop"],
                        "state_requirements": {
                            "remote_branch_matches_local": {"origin/develop": "develop"}
                        },
                    },
                    {
                        "case_id": "fetch-hard-oss-review",
                        "label": "Fetch then pull origin/release/next",
                        "context": "The upstream maintainer just merged a large PR into release/next. Before integrating their changes into your local release/next branch, you want to fetch first and inspect what changed before deciding to pull. Fetch, then pull to integrate.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Baseline snapshot",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Upstream merged large PR",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/core.py": "core-v2"},
                                },
                            ],
                            "branches": {"release/next": "c1"},
                            "head": {"type": "branch", "name": "release/next"},
                            "remotes": {"origin": "https://github.com/upstream/oss-contrib.git"},
                            "remote_branches": {"origin/release/next": "c1"},
                            "upstream_tracking": {"release/next": "origin/release/next"},
                            "remote_updates": {"origin/release/next": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git fetch origin", "git pull origin release/next"],
                        "state_requirements": {
                            "remote_branch_matches_local": {"origin/release/next": "release/next"}
                        },
                    },
                ],
            },
        },
    },
    {
        "sort_order": 6,
        "slug": "reconciling-diverged-histories",
        "title": "Reconciling Diverged Local and Remote Histories",
        "description": "Integrate remote commits that blocked your push, then complete the push successfully.",
        "tiers": {
            "easy": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "Pull to reconcile the diverged remote, then push.",
                "task": "Your push was rejected because a teammate committed to the same branch. Pull to integrate their work, then push.",
                "min_counted_commands": 2,
                "cases": [
                    {
                        "case_id": "v26e-auth",
                        "label": "Reconcile and push feature/auth",
                        "context": "You tried to push your auth changes but the push was rejected -- a teammate pushed to the same branch while you were working. Pull to reconcile, then push.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Local work (non-overlapping)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "local-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Teammate pushed to remote (non-overlapping)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/tests.py": "remote-v1"},
                                },
                            ],
                            "branches": {"feature/auth": "c2"},
                            "head": {"type": "branch", "name": "feature/auth"},
                            "remotes": {"origin": "https://github.com/team/ticketing-app.git"},
                            "remote_branches": {"origin/feature/auth": "c1"},
                            "upstream_tracking": {"feature/auth": "origin/feature/auth"},
                            "remote_updates": {"origin/feature/auth": "c3"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git pull origin feature/auth",
                            "git push origin feature/auth",
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "feature/auth",
                            "remote_branch_matches_local": {"origin/feature/auth": "feature/auth"},
                        },
                    },
                    {
                        "case_id": "v26e-payments",
                        "label": "Reconcile and push feature/payments",
                        "context": "Your push to the payments branch was rejected because someone else pushed first. Pull their changes in and then re-push.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Local work (non-overlapping)",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/payments.py": "local-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Teammate pushed to remote (non-overlapping)",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/invoice.py": "remote-v1",
                                    },
                                },
                            ],
                            "branches": {"feature/payments": "c2"},
                            "head": {"type": "branch", "name": "feature/payments"},
                            "remotes": {"origin": "https://github.com/team/e-commerce.git"},
                            "remote_branches": {"origin/feature/payments": "c1"},
                            "upstream_tracking": {"feature/payments": "origin/feature/payments"},
                            "remote_updates": {"origin/feature/payments": "c3"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git pull origin feature/payments",
                            "git push origin feature/payments",
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "feature/payments",
                            "remote_branch_matches_local": {
                                "origin/feature/payments": "feature/payments"
                            },
                        },
                    },
                    {
                        "case_id": "v26e-hotfix",
                        "label": "Reconcile and push hotfix/critical",
                        "context": "The hotfix branch push was rejected. Another engineer pushed a commit to it. Pull and push to reconcile.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Local work (non-overlapping)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/fix.py": "local-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Teammate pushed to remote (non-overlapping)",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/hotfix_tests.py": "remote-v1",
                                    },
                                },
                            ],
                            "branches": {"hotfix/critical": "c2"},
                            "head": {"type": "branch", "name": "hotfix/critical"},
                            "remotes": {"origin": "https://github.com/team/order-service.git"},
                            "remote_branches": {"origin/hotfix/critical": "c1"},
                            "upstream_tracking": {"hotfix/critical": "origin/hotfix/critical"},
                            "remote_updates": {"origin/hotfix/critical": "c3"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git pull origin hotfix/critical",
                            "git push origin hotfix/critical",
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "hotfix/critical",
                            "remote_branch_matches_local": {
                                "origin/hotfix/critical": "hotfix/critical"
                            },
                        },
                    },
                    {
                        "case_id": "rec-easy-cap-ui",
                        "label": "Reconcile and push feature/ui-layout",
                        "context": "You tried to push feature/ui-layout to origin, but it was rejected because your groupmate pushed a new commit to the same branch while you were working. No overlapping files -- no conflict will occur. Pull to reconcile, then push.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Local UI work",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/ui.py": "ui-local-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Groupmate pushed component",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/component.py": "remote-v1",
                                    },
                                },
                            ],
                            "branches": {"feature/ui-layout": "c2"},
                            "head": {"type": "branch", "name": "feature/ui-layout"},
                            "remotes": {"origin": "https://github.com/team/capstone-app.git"},
                            "remote_branches": {"origin/feature/ui-layout": "c1"},
                            "upstream_tracking": {"feature/ui-layout": "origin/feature/ui-layout"},
                            "remote_updates": {"origin/feature/ui-layout": "c3"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git pull origin feature/ui-layout",
                            "git push origin feature/ui-layout",
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "feature/ui-layout",
                            "remote_branch_matches_local": {
                                "origin/feature/ui-layout": "feature/ui-layout"
                            },
                        },
                    },
                    {
                        "case_id": "rec-easy-docs-chapter",
                        "label": "Reconcile and push main",
                        "context": "You and a colleague are both editing the docs repo. Your push to main was rejected -- your colleague pushed a new chapter while you were writing. No overlap. Pull then push.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Your new chapter",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "docs/chapter-3.md": "ch3-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Colleague's chapter",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "docs/chapter-4.md": "remote-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "remotes": {"origin": "https://github.com/team/docs-portal.git"},
                            "remote_branches": {"origin/main": "c1"},
                            "upstream_tracking": {"main": "origin/main"},
                            "remote_updates": {"origin/main": "c3"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git pull origin main", "git push origin main"],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "main",
                            "remote_branch_matches_local": {"origin/main": "main"},
                        },
                    },
                ],
            },
            "medium": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "Fetch, inspect, merge the remote tracking branch, then push.",
                "task": "Your push was rejected. Fetch to update remote tracking refs, merge origin/<branch> into your local branch, then push.",
                "min_counted_commands": 3,
                "cases": [
                    {
                        "case_id": "v26m-auth",
                        "label": "Fetch, merge, push feature/auth",
                        "context": "Your push was rejected. You prefer the explicit fetch-then-merge workflow over a plain pull. Fetch, merge origin/auth into your local auth branch, then push.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Local work (non-overlapping)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "local-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Teammate pushed to remote (non-overlapping)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/tests.py": "remote-v1"},
                                },
                            ],
                            "branches": {"feature/auth": "c2"},
                            "head": {"type": "branch", "name": "feature/auth"},
                            "remotes": {"origin": "https://github.com/team/ticketing-app.git"},
                            "remote_branches": {"origin/feature/auth": "c1"},
                            "upstream_tracking": {"feature/auth": "origin/feature/auth"},
                            "remote_updates": {"origin/feature/auth": "c3"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git fetch origin",
                            "git merge origin/feature/auth",
                            "git push origin feature/auth",
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "feature/auth",
                            "remote_branch_matches_local": {"origin/feature/auth": "feature/auth"},
                        },
                    },
                    {
                        "case_id": "v26m-payments",
                        "label": "Fetch, merge, push feature/payments",
                        "context": "Push rejected on payments. Use the manual reconcile path: fetch, merge remote tracking branch, then push.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Local work (non-overlapping)",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/payments.py": "local-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Teammate pushed to remote (non-overlapping)",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/invoice.py": "remote-v1",
                                    },
                                },
                            ],
                            "branches": {"feature/payments": "c2"},
                            "head": {"type": "branch", "name": "feature/payments"},
                            "remotes": {"origin": "https://github.com/team/e-commerce.git"},
                            "remote_branches": {"origin/feature/payments": "c1"},
                            "upstream_tracking": {"feature/payments": "origin/feature/payments"},
                            "remote_updates": {"origin/feature/payments": "c3"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git fetch origin",
                            "git merge origin/feature/payments",
                            "git push origin feature/payments",
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "feature/payments",
                            "remote_branch_matches_local": {
                                "origin/feature/payments": "feature/payments"
                            },
                        },
                    },
                    {
                        "case_id": "v26m-hotfix",
                        "label": "Fetch, merge, push hotfix/critical",
                        "context": "Hotfix push rejected. Fetch the remote state first, merge explicitly, then push.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Local work (non-overlapping)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/fix.py": "local-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Teammate pushed to remote (non-overlapping)",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/hotfix_tests.py": "remote-v1",
                                    },
                                },
                            ],
                            "branches": {"hotfix/critical": "c2"},
                            "head": {"type": "branch", "name": "hotfix/critical"},
                            "remotes": {"origin": "https://github.com/team/order-service.git"},
                            "remote_branches": {"origin/hotfix/critical": "c1"},
                            "upstream_tracking": {"hotfix/critical": "origin/hotfix/critical"},
                            "remote_updates": {"origin/hotfix/critical": "c3"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git fetch origin",
                            "git merge origin/hotfix/critical",
                            "git push origin hotfix/critical",
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "hotfix/critical",
                            "remote_branch_matches_local": {
                                "origin/hotfix/critical": "hotfix/critical"
                            },
                        },
                    },
                    {
                        "case_id": "rec-med-qa-testrunner",
                        "label": "Fetch, merge, push feature/test-runner-v2",
                        "context": "Your push of feature/test-runner-v2 was rejected. A teammate pushed fixes to the same branch. You prefer to inspect before integrating. Fetch, then explicitly merge origin/feature/test-runner-v2, then push.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Local test runner work",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/runner.py": "runner-local-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Teammate pushed fixes",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/reporter.py": "remote-v1",
                                    },
                                },
                            ],
                            "branches": {"feature/test-runner-v2": "c2"},
                            "head": {"type": "branch", "name": "feature/test-runner-v2"},
                            "remotes": {"origin": "https://github.com/team/qa-suite.git"},
                            "remote_branches": {"origin/feature/test-runner-v2": "c1"},
                            "upstream_tracking": {
                                "feature/test-runner-v2": "origin/feature/test-runner-v2"
                            },
                            "remote_updates": {"origin/feature/test-runner-v2": "c3"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git fetch origin",
                            "git merge origin/feature/test-runner-v2",
                            "git push origin feature/test-runner-v2",
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "feature/test-runner-v2",
                            "remote_branch_matches_local": {
                                "origin/feature/test-runner-v2": "feature/test-runner-v2"
                            },
                        },
                    },
                ],
            },
            "hard": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "Switch to the correct branch, then fetch, merge, and push.",
                "task": "You are on the wrong branch. Switch to the branch that was rejected, then reconcile with the remote and push.",
                "min_counted_commands": 4,
                "cases": [
                    {
                        "case_id": "v26h-auth",
                        "label": "Switch, fetch, merge, push feature/auth",
                        "context": "You need to reconcile and push the auth branch -- but you're currently on a different branch. Switch first, then fetch, merge, and push.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Local work on target branch (non-overlapping)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "local-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Teammate pushed to remote (non-overlapping)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/tests.py": "remote-v1"},
                                },
                            ],
                            "branches": {"feature/current": "c1", "feature/auth": "c2"},
                            "head": {"type": "branch", "name": "feature/current"},
                            "remotes": {"origin": "https://github.com/team/ticketing-app.git"},
                            "remote_branches": {"origin/feature/auth": "c1"},
                            "upstream_tracking": {"feature/auth": "origin/feature/auth"},
                            "remote_updates": {"origin/feature/auth": "c3"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git switch feature/auth",
                            "git fetch origin",
                            "git merge origin/feature/auth",
                            "git push origin feature/auth",
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "feature/auth",
                            "remote_branch_matches_local": {"origin/feature/auth": "feature/auth"},
                        },
                    },
                    {
                        "case_id": "v26h-payments",
                        "label": "Switch, fetch, merge, push feature/payments",
                        "context": "You're on the wrong branch when you try to reconcile payments. Switch to the right branch, fetch, merge, and push.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Local work on target branch (non-overlapping)",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/payments.py": "local-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Teammate pushed to remote (non-overlapping)",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/invoice.py": "remote-v1",
                                    },
                                },
                            ],
                            "branches": {"feature/current": "c1", "feature/payments": "c2"},
                            "head": {"type": "branch", "name": "feature/current"},
                            "remotes": {"origin": "https://github.com/team/e-commerce.git"},
                            "remote_branches": {"origin/feature/payments": "c1"},
                            "upstream_tracking": {"feature/payments": "origin/feature/payments"},
                            "remote_updates": {"origin/feature/payments": "c3"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git switch feature/payments",
                            "git fetch origin",
                            "git merge origin/feature/payments",
                            "git push origin feature/payments",
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "feature/payments",
                            "remote_branch_matches_local": {
                                "origin/feature/payments": "feature/payments"
                            },
                        },
                    },
                    {
                        "case_id": "v26h-hotfix",
                        "label": "Switch, fetch, merge, push hotfix/critical",
                        "context": "You're not on the hotfix branch when the push rejection happens. Switch to it, fetch, merge origin tracking, and push.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Local work on target branch (non-overlapping)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/fix.py": "local-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Teammate pushed to remote (non-overlapping)",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/hotfix_tests.py": "remote-v1",
                                    },
                                },
                            ],
                            "branches": {"feature/current": "c1", "hotfix/critical": "c2"},
                            "head": {"type": "branch", "name": "feature/current"},
                            "remotes": {"origin": "https://github.com/team/order-service.git"},
                            "remote_branches": {"origin/hotfix/critical": "c1"},
                            "upstream_tracking": {"hotfix/critical": "origin/hotfix/critical"},
                            "remote_updates": {"origin/hotfix/critical": "c3"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git switch hotfix/critical",
                            "git fetch origin",
                            "git merge origin/hotfix/critical",
                            "git push origin hotfix/critical",
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "hotfix/critical",
                            "remote_branch_matches_local": {
                                "origin/hotfix/critical": "hotfix/critical"
                            },
                        },
                    },
                    {
                        "case_id": "rec-hard-corp-audit",
                        "label": "Switch, fetch, merge, push feature/compliance-audit",
                        "context": "You need to reconcile and push feature/compliance-audit, but you are currently on develop. The push to feature/compliance-audit was rejected. Switch to the right branch, fetch, merge, and push.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Local audit work",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/audit.py": "audit-local-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Teammate pushed audit fix",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/compliance.py": "remote-v1",
                                    },
                                },
                            ],
                            "branches": {"develop": "c1", "feature/compliance-audit": "c2"},
                            "head": {"type": "branch", "name": "develop"},
                            "remotes": {"origin": "https://github.com/team/corp-backend.git"},
                            "remote_branches": {"origin/feature/compliance-audit": "c1"},
                            "upstream_tracking": {
                                "feature/compliance-audit": "origin/feature/compliance-audit"
                            },
                            "remote_updates": {"origin/feature/compliance-audit": "c3"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git switch feature/compliance-audit",
                            "git fetch origin",
                            "git merge origin/feature/compliance-audit",
                            "git push origin feature/compliance-audit",
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "feature/compliance-audit",
                            "remote_branch_matches_local": {
                                "origin/feature/compliance-audit": "feature/compliance-audit"
                            },
                        },
                    },
                ],
            },
        },
    },
    {
        "sort_order": 7,
        "slug": "completing-branch-merges",
        "title": "Completing Branch Merges",
        "description": "Choose the right merge strategy to produce the history shape the team requires.",
        "tiers": {
            "easy": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "Merge a feature branch that is a linear descendant of the target.",
                "task": "The feature branch has no divergence from the target. Merge it in, allowing a fast-forward.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "v27e-auth",
                        "label": "Fast-forward merge feature/auth into main",
                        "context": "The auth feature branch is a direct linear descendant of main -- no divergence. Merge it in. A fast-forward is fine.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Project base commit",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch complete",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "auth-v1"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/auth": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git merge feature/auth"],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "main",
                            "rules": [
                                {"type": "min_commits_on_branch", "branch": "main", "minimum": 2}
                            ],
                        },
                    },
                    {
                        "case_id": "v27e-payments",
                        "label": "Fast-forward merge feature/payments into develop",
                        "context": "The payments branch is linear from main. Merge it using fast-forward -- no merge commit needed.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Project base commit",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch complete",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/payments.py": "pay-v1"},
                                },
                            ],
                            "branches": {"develop": "c1", "feature/payments": "c2"},
                            "head": {"type": "branch", "name": "develop"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git merge feature/payments"],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "develop",
                            "rules": [
                                {"type": "min_commits_on_branch", "branch": "develop", "minimum": 2}
                            ],
                        },
                    },
                    {
                        "case_id": "v27e-hotfix",
                        "label": "Fast-forward merge hotfix/fix-critical into release/v2",
                        "context": "The hotfix branch is ahead of main in a straight line. Fast-forward main to include it.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Project base commit",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch complete",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/fix.py": "fix-v1"},
                                },
                            ],
                            "branches": {"release/v2": "c1", "hotfix/fix-critical": "c2"},
                            "head": {"type": "branch", "name": "release/v2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git merge hotfix/fix-critical"],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "release/v2",
                            "rules": [
                                {
                                    "type": "min_commits_on_branch",
                                    "branch": "release/v2",
                                    "minimum": 2,
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "merge-easy-cap-docs",
                        "label": "Fast-forward merge docs/readme-update into staging",
                        "context": 'docs/readme-update is a direct linear descendant of staging -- no divergence. Your group lead says "just merge it in." You are on staging. Fast-forward is fine.',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Project base commit",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "README update complete",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v2"},
                                },
                            ],
                            "branches": {"staging": "c1", "docs/readme-update": "c2"},
                            "head": {"type": "branch", "name": "staging"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git merge docs/readme-update"],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "staging",
                            "rules": [
                                {"type": "min_commits_on_branch", "branch": "staging", "minimum": 2}
                            ],
                        },
                    },
                    {
                        "case_id": "merge-easy-free-contact",
                        "label": "Fast-forward merge feature/contact-form into integration",
                        "context": "feature/contact-form is complete and is a linear descendant of integration. You are on integration. Merge it in -- fast-forward is acceptable.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Project base commit",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Contact form complete",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/contact.py": "contact-v1",
                                    },
                                },
                            ],
                            "branches": {"integration": "c1", "feature/contact-form": "c2"},
                            "head": {"type": "branch", "name": "integration"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git merge feature/contact-form"],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "integration",
                            "rules": [
                                {
                                    "type": "min_commits_on_branch",
                                    "branch": "integration",
                                    "minimum": 2,
                                }
                            ],
                        },
                    },
                ],
            },
            "medium": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "Force a merge commit on a linear branch to preserve branch history.",
                "task": "The feature branch is ahead of the target with no divergence, but team policy requires an explicit merge commit.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "v27m-auth",
                        "label": "No-ff merge feature/auth into main",
                        "context": "The auth branch is linear from main but your team's policy requires an explicit merge commit for every feature. Use --no-ff.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Project base commit",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch complete",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "auth-v1"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/auth": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git merge --no-ff feature/auth"],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "main",
                            "rules": [
                                {"type": "min_commits_on_branch", "branch": "main", "minimum": 3}
                            ],
                        },
                    },
                    {
                        "case_id": "v27m-payments",
                        "label": "No-ff merge feature/payments into develop",
                        "context": "Even though payments could fast-forward, team policy requires a merge commit to preserve a clear audit trail. Merge with --no-ff.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Project base commit",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch complete",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/payments.py": "pay-v1"},
                                },
                            ],
                            "branches": {"develop": "c1", "feature/payments": "c2"},
                            "head": {"type": "branch", "name": "develop"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git merge --no-ff feature/payments"],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "develop",
                            "rules": [
                                {"type": "min_commits_on_branch", "branch": "develop", "minimum": 3}
                            ],
                        },
                    },
                    {
                        "case_id": "v27m-hotfix",
                        "label": "No-ff merge hotfix/fix-critical into release/v2",
                        "context": "The hotfix could be fast-forwarded but policy requires a merge commit. Use --no-ff.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Project base commit",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch complete",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/fix.py": "fix-v1"},
                                },
                            ],
                            "branches": {"release/v2": "c1", "hotfix/fix-critical": "c2"},
                            "head": {"type": "branch", "name": "release/v2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git merge --no-ff hotfix/fix-critical"],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "release/v2",
                            "rules": [
                                {
                                    "type": "min_commits_on_branch",
                                    "branch": "release/v2",
                                    "minimum": 3,
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "merge-med-corp-sso",
                        "label": "No-ff merge feature/sso-integration into release/v1",
                        "context": "feature/sso-integration is a linear descendant of release/v1 but your team's policy requires an explicit merge commit for every feature branch to maintain a clear audit trail. You are on release/v1. Use --no-ff.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Project base commit",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "SSO integration complete",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/sso.py": "sso-v1"},
                                },
                            ],
                            "branches": {"release/v1": "c1", "feature/sso-integration": "c2"},
                            "head": {"type": "branch", "name": "release/v1"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git merge --no-ff feature/sso-integration"],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "release/v1",
                            "rules": [
                                {
                                    "type": "min_commits_on_branch",
                                    "branch": "release/v1",
                                    "minimum": 3,
                                }
                            ],
                        },
                    },
                ],
            },
            "hard": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "Switch to the target branch and no-ff merge a diverged feature.",
                "task": "You are currently on a different branch and histories have diverged. Move to the correct target first, then merge with an explicit merge commit.",
                "min_counted_commands": 2,
                "cases": [
                    {
                        "case_id": "v27h-auth",
                        "label": "Switch to main, no-ff merge feature/auth",
                        "context": "You need to merge auth into main with an explicit commit, but you're on auth right now. Switch to main first, then merge with --no-ff.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Auth feature diverged",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "auth-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Main diverged",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/app.py": "app-v1"},
                                },
                            ],
                            "branches": {
                                "feature/current": "c1",
                                "main": "c3",
                                "feature/auth": "c2",
                            },
                            "head": {"type": "branch", "name": "feature/current"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git switch main", "git merge --no-ff feature/auth"],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "main",
                            "rules": [
                                {"type": "min_commits_on_branch", "branch": "main", "minimum": 4}
                            ],
                        },
                    },
                    {
                        "case_id": "v27h-payments",
                        "label": "Switch to develop, no-ff merge feature/payments",
                        "context": "You're not on the target branch. Switch to main, then merge the payments branch with --no-ff per team policy.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Payments diverged",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/payments.py": "pay-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Develop diverged",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/core.py": "core-v1"},
                                },
                            ],
                            "branches": {
                                "feature/current": "c1",
                                "develop": "c3",
                                "feature/payments": "c2",
                            },
                            "head": {"type": "branch", "name": "feature/current"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git switch develop",
                            "git merge --no-ff feature/payments",
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "develop",
                            "rules": [
                                {"type": "min_commits_on_branch", "branch": "develop", "minimum": 4}
                            ],
                        },
                    },
                    {
                        "case_id": "v27h-hotfix",
                        "label": "Switch to release/v1, no-ff merge hotfix/critical",
                        "context": "The hotfix needs to go into release/stable -- but you're on main. Switch to the right target branch and no-ff merge the hotfix.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Hotfix diverged",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/fix.py": "fix-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Release diverged",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/release.py": "rel-v1"},
                                },
                            ],
                            "branches": {
                                "feature/current": "c1",
                                "release/v1": "c3",
                                "hotfix/critical": "c2",
                            },
                            "head": {"type": "branch", "name": "feature/current"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git switch release/v1",
                            "git merge --no-ff hotfix/critical",
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "release/v1",
                            "rules": [
                                {
                                    "type": "min_commits_on_branch",
                                    "branch": "release/v1",
                                    "minimum": 4,
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "merge-hard-devops-cert",
                        "label": "Switch to release/stable, no-ff merge hotfix/cert-renewal",
                        "context": "You are on feature/current-work. hotfix/cert-renewal needs to be merged into release/stable with an explicit merge commit (team policy). Switch to the target branch, then merge with --no-ff.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Common base",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Cert renewal hotfix",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/certs.py": "cert-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Release stable diverged",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/release.py": "rel-v1"},
                                },
                            ],
                            "branches": {
                                "feature/current-work": "c1",
                                "release/stable": "c3",
                                "hotfix/cert-renewal": "c2",
                            },
                            "head": {"type": "branch", "name": "feature/current-work"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git switch release/stable",
                            "git merge --no-ff hotfix/cert-renewal",
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "release/stable",
                            "rules": [
                                {
                                    "type": "min_commits_on_branch",
                                    "branch": "release/stable",
                                    "minimum": 4,
                                }
                            ],
                        },
                    },
                ],
            },
        },
    },
    {
        "sort_order": 8,
        "slug": "squash-merging",
        "title": "Squash Merging",
        "description": "Land a feature branch as a single tidy commit on the target branch.",
        "tiers": {
            "easy": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "Squash a local feature branch onto the target branch.",
                "task": "The feature branch has several intermediate commits. Land them as a single clean commit on the target.",
                "min_counted_commands": 2,
                "cases": [
                    {
                        "case_id": "v28e-auth",
                        "label": "Squash-merge feature/auth into main",
                        "context": "The auth feature branch has several WIP commits. Land it on main as a single clean commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Auth: add login",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "auth-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Auth: add logout",
                                    "parents": ["c2"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "auth-v2"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/auth": "c3"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge --squash feature/auth",
                            'git commit -m "Squash auth feature into main"',
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "main",
                            "working_tree_clean": True,
                            "rules": [
                                {"type": "min_commits_on_branch", "branch": "main", "minimum": 2}
                            ],
                        },
                    },
                    {
                        "case_id": "v28e-orders",
                        "label": "Squash-merge feature/orders into develop",
                        "context": "The orders branch has multiple incremental commits. Squash-merge them into a single commit on main.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Orders: add create",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/orders.py": "ord-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Orders: add cancel",
                                    "parents": ["c2"],
                                    "tree": {"README.md": "readme-v1", "src/orders.py": "ord-v2"},
                                },
                            ],
                            "branches": {"develop": "c1", "feature/orders": "c3"},
                            "head": {"type": "branch", "name": "develop"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge --squash feature/orders",
                            'git commit -m "Squash orders feature into develop"',
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "develop",
                            "working_tree_clean": True,
                            "rules": [
                                {"type": "min_commits_on_branch", "branch": "develop", "minimum": 2}
                            ],
                        },
                    },
                    {
                        "case_id": "v28e-parser",
                        "label": "Squash-merge feature/parser into release/v2",
                        "context": "The parser feature has many small commits. Squash the branch onto main as one tidy commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Parser: initial impl",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/parser.py": "par-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Parser: add error handling",
                                    "parents": ["c2"],
                                    "tree": {"README.md": "readme-v1", "src/parser.py": "par-v2"},
                                },
                            ],
                            "branches": {"release/v2": "c1", "feature/parser": "c3"},
                            "head": {"type": "branch", "name": "release/v2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge --squash feature/parser",
                            'git commit -m "Squash parser feature into release/v2"',
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "release/v2",
                            "working_tree_clean": True,
                            "rules": [
                                {
                                    "type": "min_commits_on_branch",
                                    "branch": "release/v2",
                                    "minimum": 2,
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "squash-easy-cap-report",
                        "label": "Squash-merge feature/report-generator into integration",
                        "context": 'feature/report-generator has 3 messy WIP commits your group accumulated while iterating. Before submitting, your group lead wants a single clean commit on integration. You are on integration. Squash-merge and commit with "Add report generator module".',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Report: initial impl",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/report.py": "rep-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Report: add filters",
                                    "parents": ["c2"],
                                    "tree": {"README.md": "readme-v1", "src/report.py": "rep-v2"},
                                },
                                {
                                    "id": "c4",
                                    "message": "Report: fix edge case",
                                    "parents": ["c3"],
                                    "tree": {"README.md": "readme-v1", "src/report.py": "rep-v3"},
                                },
                            ],
                            "branches": {"integration": "c1", "feature/report-generator": "c4"},
                            "head": {"type": "branch", "name": "integration"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge --squash feature/report-generator",
                            'git commit -m "Add report generator module"',
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "integration",
                            "working_tree_clean": True,
                            "rules": [
                                {
                                    "type": "min_commits_on_branch",
                                    "branch": "integration",
                                    "minimum": 2,
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "squash-easy-free-payment",
                        "label": "Squash-merge feature/payment-flow into staging",
                        "context": 'feature/payment-flow has 4 intermediate commits with messages like "wip", "fix again", "ok this time". Your client\'s repo policy is one commit per feature. You are on staging. Squash and commit with "Add payment flow".',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "wip",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/payment.py": "pay-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "fix again",
                                    "parents": ["c2"],
                                    "tree": {"README.md": "readme-v1", "src/payment.py": "pay-v2"},
                                },
                                {
                                    "id": "c4",
                                    "message": "ok this time",
                                    "parents": ["c3"],
                                    "tree": {"README.md": "readme-v1", "src/payment.py": "pay-v3"},
                                },
                            ],
                            "branches": {"staging": "c1", "feature/payment-flow": "c4"},
                            "head": {"type": "branch", "name": "staging"},
                            "staging_area": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge --squash feature/payment-flow",
                            'git commit -m "Add payment flow"',
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "staging",
                            "working_tree_clean": True,
                            "rules": [
                                {"type": "min_commits_on_branch", "branch": "staging", "minimum": 2}
                            ],
                        },
                    },
                ],
            },
            "medium": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "Fetch a remote feature branch then squash-merge it.",
                "task": "The feature work is on the remote. Fetch it first, then squash-merge to land it as one commit on the target.",
                "min_counted_commands": 3,
                "cases": [
                    {
                        "case_id": "v28m-auth",
                        "label": "Fetch then squash-merge origin/feature/auth into main",
                        "context": "A teammate's auth branch is on the remote but hasn't been fetched locally. Fetch it first, then squash-merge origin/feature/auth onto main.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                            ],
                            "branches": {"main": "c1"},
                            "head": {"type": "branch", "name": "main"},
                            "remotes": {"origin": "https://github.com/team/ticketing-app.git"},
                            "remote_branches": {"origin/feature/auth": "c1"},
                            "remote_updates": {"origin/feature/auth": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git fetch origin",
                            "git merge --squash origin/feature/auth",
                            'git commit -m "Squash remote auth feature into main"',
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "main",
                            "working_tree_clean": True,
                            "rules": [
                                {"type": "min_commits_on_branch", "branch": "main", "minimum": 2}
                            ],
                        },
                    },
                    {
                        "case_id": "v28m-orders",
                        "label": "Fetch then squash-merge origin/feature/orders into develop",
                        "context": "The orders feature is only on the remote. Fetch it, then squash-merge the remote tracking branch onto main.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                            ],
                            "branches": {"develop": "c1"},
                            "head": {"type": "branch", "name": "develop"},
                            "remotes": {"origin": "https://github.com/team/e-commerce.git"},
                            "remote_branches": {"origin/feature/orders": "c1"},
                            "remote_updates": {"origin/feature/orders": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git fetch origin",
                            "git merge --squash origin/feature/orders",
                            'git commit -m "Squash remote orders feature into develop"',
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "develop",
                            "working_tree_clean": True,
                            "rules": [
                                {"type": "min_commits_on_branch", "branch": "develop", "minimum": 2}
                            ],
                        },
                    },
                    {
                        "case_id": "v28m-parser",
                        "label": "Fetch then squash-merge origin/feature/parser into release/v2",
                        "context": "The parser branch hasn't been fetched yet. Fetch origin first, then squash-merge origin/feature/parser.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                            ],
                            "branches": {"release/v2": "c1"},
                            "head": {"type": "branch", "name": "release/v2"},
                            "remotes": {"origin": "https://github.com/team/data-pipeline.git"},
                            "remote_branches": {"origin/feature/parser": "c1"},
                            "remote_updates": {"origin/feature/parser": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git fetch origin",
                            "git merge --squash origin/feature/parser",
                            'git commit -m "Squash remote parser feature into release/v2"',
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "release/v2",
                            "working_tree_clean": True,
                            "rules": [
                                {
                                    "type": "min_commits_on_branch",
                                    "branch": "release/v2",
                                    "minimum": 2,
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "squash-med-corp-gdpr",
                        "label": "Fetch then squash-merge origin/feature/gdpr-export into staging",
                        "context": "A colleague's feature/gdpr-export branch is on the remote but hasn't been fetched. Fetch it first, then squash-merge origin/feature/gdpr-export onto staging with the commit message \"Add GDPR data export endpoint\".",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                            ],
                            "branches": {"staging": "c1"},
                            "head": {"type": "branch", "name": "staging"},
                            "remotes": {"origin": "https://github.com/team/corp-backend.git"},
                            "remote_branches": {"origin/feature/gdpr-export": "c1"},
                            "remote_updates": {"origin/feature/gdpr-export": "c2"},
                            "staging_area": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git fetch origin",
                            "git merge --squash origin/feature/gdpr-export",
                            'git commit -m "Add GDPR data export endpoint"',
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "staging",
                            "working_tree_clean": True,
                            "rules": [
                                {"type": "min_commits_on_branch", "branch": "staging", "minimum": 2}
                            ],
                        },
                    },
                ],
            },
            "hard": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "Squash-merge the feature branch and clean up the source branch.",
                "task": "After landing the squash commit, the feature branch is no longer needed. Remove it to keep the branch list tidy.",
                "min_counted_commands": 3,
                "cases": [
                    {
                        "case_id": "v28h-auth",
                        "label": "Squash-merge and delete feature/auth",
                        "context": "Squash-merge the auth branch into main as a single commit, then delete the source branch -- it's no longer needed.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Auth: add login",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "auth-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Auth: add logout",
                                    "parents": ["c2"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "auth-v2"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/auth": "c3"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge --squash feature/auth",
                            'git commit -m "Squash auth feature into main"',
                            "git branch -D feature/auth",
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "main",
                            "working_tree_clean": True,
                            "branch_absent": ["feature/auth"],
                            "rules": [
                                {"type": "min_commits_on_branch", "branch": "main", "minimum": 2}
                            ],
                        },
                    },
                    {
                        "case_id": "v28h-orders",
                        "label": "Squash-merge and delete feature/orders",
                        "context": "Land the orders branch as one commit on main, then clean up by deleting the merged source branch.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Orders: add create",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/orders.py": "ord-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Orders: add cancel",
                                    "parents": ["c2"],
                                    "tree": {"README.md": "readme-v1", "src/orders.py": "ord-v2"},
                                },
                            ],
                            "branches": {"develop": "c1", "feature/orders": "c3"},
                            "head": {"type": "branch", "name": "develop"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge --squash feature/orders",
                            'git commit -m "Squash orders feature into develop"',
                            "git branch -D feature/orders",
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "develop",
                            "working_tree_clean": True,
                            "branch_absent": ["feature/orders"],
                            "rules": [
                                {"type": "min_commits_on_branch", "branch": "develop", "minimum": 2}
                            ],
                        },
                    },
                    {
                        "case_id": "v28h-parser",
                        "label": "Squash-merge and delete feature/parser",
                        "context": "Squash-merge parser onto main, commit, then remove the source branch.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Parser: initial impl",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/parser.py": "par-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Parser: add error handling",
                                    "parents": ["c2"],
                                    "tree": {"README.md": "readme-v1", "src/parser.py": "par-v2"},
                                },
                            ],
                            "branches": {"release/v2": "c1", "feature/parser": "c3"},
                            "head": {"type": "branch", "name": "release/v2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge --squash feature/parser",
                            'git commit -m "Squash parser feature into release/v2"',
                            "git branch -D feature/parser",
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "release/v2",
                            "working_tree_clean": True,
                            "branch_absent": ["feature/parser"],
                            "rules": [
                                {
                                    "type": "min_commits_on_branch",
                                    "branch": "release/v2",
                                    "minimum": 2,
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "squash-hard-devops-log",
                        "label": "Squash-merge and delete feature/log-rotation",
                        "context": 'feature/log-rotation is complete with several intermediate commits. Land it on main as a single commit with message "Add log rotation configuration", then delete the source branch -- it is no longer needed. You are on main.',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Bootstrap project",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Log rotation: add cron",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/log.py": "log-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Log rotation: add retention",
                                    "parents": ["c2"],
                                    "tree": {"README.md": "readme-v1", "src/log.py": "log-v2"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/log-rotation": "c3"},
                            "head": {"type": "branch", "name": "main"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge --squash feature/log-rotation",
                            'git commit -m "Add log rotation configuration"',
                            "git branch -D feature/log-rotation",
                        ],
                        "state_requirements": {
                            "conflict_free": True,
                            "head_branch": "main",
                            "working_tree_clean": True,
                            "branch_absent": ["feature/log-rotation"],
                            "rules": [
                                {"type": "min_commits_on_branch", "branch": "main", "minimum": 2}
                            ],
                        },
                    },
                ],
            },
        },
    },
    {
        "sort_order": 9,
        "slug": "deleting-and-recovering-remote-branches",
        "title": "Deleting and Recovering Remote Branches",
        "description": "Manage remote branch lifecycle: remove finished branches and restore accidentally deleted ones.",
        "tiers": {
            "easy": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "Delete a merged remote branch.",
                "task": "The feature branch was merged and is no longer needed on the remote. Remove it.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "v29e-auth",
                        "label": "Delete origin/feature/auth",
                        "context": "The auth branch was merged via PR and is no longer needed on the remote. Delete it from origin.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Merge commit on main",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "auth-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature tip (still on remote)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "auth-v1"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/auth": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "remote_branches": {"origin/feature/auth": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git push origin --delete feature/auth"],
                        "state_requirements": {"remote_branch_absent": ["origin/feature/auth"]},
                    },
                    {
                        "case_id": "v29e-orders",
                        "label": "Delete origin/feature/orders",
                        "context": "The orders feature was merged. Clean up by removing the remote branch from origin.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Merge commit on main",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/orders.py": "ord-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature tip (still on remote)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/orders.py": "ord-v1"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/orders": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "remote_branches": {"origin/feature/orders": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git push origin --delete feature/orders"],
                        "state_requirements": {"remote_branch_absent": ["origin/feature/orders"]},
                    },
                    {
                        "case_id": "v29e-parser",
                        "label": "Delete origin/feature/parser",
                        "context": "Parser work is merged and done. Delete the remote branch to keep origin tidy.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Merge commit on main",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/parser.py": "par-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature tip (still on remote)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/parser.py": "par-v1"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/parser": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "remote_branches": {"origin/feature/parser": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git push origin --delete feature/parser"],
                        "state_requirements": {"remote_branch_absent": ["origin/feature/parser"]},
                    },
                    {
                        "case_id": "rb-easy-cap-group",
                        "label": "Delete origin/feature/group-auth",
                        "context": "Your group merged feature/group-auth into main on GitHub yesterday. The remote branch is still there. Remove it from origin.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Merge commit on main",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "auth-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature tip (still on remote)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "auth-v1"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/group-auth": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "remote_branches": {"origin/feature/group-auth": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git push origin --delete feature/group-auth"],
                        "state_requirements": {
                            "remote_branch_absent": ["origin/feature/group-auth"]
                        },
                    },
                    {
                        "case_id": "rb-easy-corp-sprint",
                        "label": "Delete origin/feature/sprint12-compliance",
                        "context": "Sprint 12's feature/sprint12-compliance branch was merged and closed in your project tracker. Remove the remote branch.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Merge commit on main",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/compliance.py": "comp-v1",
                                    },
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature tip (still on remote)",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/compliance.py": "comp-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c1", "feature/sprint12-compliance": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "remote_branches": {"origin/feature/sprint12-compliance": "c2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git push origin --delete feature/sprint12-compliance"
                        ],
                        "state_requirements": {
                            "remote_branch_absent": ["origin/feature/sprint12-compliance"]
                        },
                    },
                ],
            },
            "medium": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "Prune a stale remote tracking ref that no longer exists on the remote.",
                "task": "A teammate deleted the remote branch. Your local remote tracking ref is stale. Clean it up with fetch --prune.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "v29m-auth",
                        "label": "Prune stale origin/feature/auth ref",
                        "context": "Origin still shows a tracking ref for auth, but the branch was deleted on the remote. Run fetch --prune to clean up the stale local tracking ref.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Main at latest",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "auth-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature tip (already deleted on remote)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "auth-v1"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/auth": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "remotes": {"origin": "https://github.com/team/ticketing-app.git"},
                            "remote_branches": {"origin/feature/auth": "c2"},
                            "remote_stale_branches": ["origin/feature/auth"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git fetch --prune origin"],
                        "state_requirements": {"remote_branch_absent": ["origin/feature/auth"]},
                    },
                    {
                        "case_id": "v29m-orders",
                        "label": "Prune stale origin/feature/orders ref",
                        "context": "Your local remote-tracking refs are stale -- origin deleted some branches. Use fetch --prune to sync.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Main at latest",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/orders.py": "ord-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature tip (already deleted on remote)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/orders.py": "ord-v1"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/orders": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "remotes": {"origin": "https://github.com/team/e-commerce.git"},
                            "remote_branches": {"origin/feature/orders": "c2"},
                            "remote_stale_branches": ["origin/feature/orders"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git fetch --prune origin"],
                        "state_requirements": {"remote_branch_absent": ["origin/feature/orders"]},
                    },
                    {
                        "case_id": "v29m-parser",
                        "label": "Prune stale origin/feature/parser ref",
                        "context": "The parser remote tracking ref is stale. Prune it with fetch --prune.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Main at latest",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1", "src/parser.py": "par-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature tip (already deleted on remote)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/parser.py": "par-v1"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/parser": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "remotes": {"origin": "https://github.com/team/data-pipeline.git"},
                            "remote_branches": {"origin/feature/parser": "c2"},
                            "remote_stale_branches": ["origin/feature/parser"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git fetch --prune origin"],
                        "state_requirements": {"remote_branch_absent": ["origin/feature/parser"]},
                    },
                    {
                        "case_id": "rb-med-free-prune",
                        "label": "Prune stale origin/feature/old-landing ref",
                        "context": "Your client deleted feature/old-landing from the remote -- they no longer need it. Your local remote tracking ref origin/feature/old-landing is now stale. Run fetch with pruning to clean it up.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Main at latest",
                                    "parents": [],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/landing.py": "landing-v1",
                                    },
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature tip (already deleted on remote)",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/landing.py": "landing-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c1", "feature/old-landing": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "remotes": {"origin": "https://github.com/client/client-site.git"},
                            "remote_branches": {"origin/feature/old-landing": "c2"},
                            "remote_stale_branches": ["origin/feature/old-landing"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git fetch --prune origin"],
                        "state_requirements": {
                            "remote_branch_absent": ["origin/feature/old-landing"]
                        },
                    },
                ],
            },
            "hard": {
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "Delete the remote branch and clean up the local branch.",
                "task": "After a feature is merged, remove both the remote branch and the local branch to keep the repository tidy.",
                "min_counted_commands": 2,
                "cases": [
                    {
                        "case_id": "v29h-auth",
                        "label": "Delete origin/feature/auth and local feature/auth",
                        "context": "The auth branch has been merged and deleted on origin. You also have the local branch. Delete the remote tracking ref via prune, then delete the local branch too.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature work (merged)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "auth-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Merge feature into main",
                                    "parents": ["c1", "c2"],
                                    "tree": {"README.md": "readme-v1", "src/auth.py": "auth-v1"},
                                },
                            ],
                            "branches": {"main": "c3", "feature/auth": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "remote_branches": {"origin/feature/auth": "c2"},
                            "upstream_tracking": {"feature/auth": "origin/feature/auth"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git push origin --delete feature/auth",
                            "git branch -d feature/auth",
                        ],
                        "state_requirements": {
                            "remote_branch_absent": ["origin/feature/auth"],
                            "branch_absent": ["feature/auth"],
                        },
                    },
                    {
                        "case_id": "v29h-orders",
                        "label": "Delete origin/feature/orders and local feature/orders",
                        "context": "Clean up orders completely: prune the stale remote tracking ref and delete your local orders branch.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature work (merged)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/orders.py": "ord-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Merge feature into main",
                                    "parents": ["c1", "c2"],
                                    "tree": {"README.md": "readme-v1", "src/orders.py": "ord-v1"},
                                },
                            ],
                            "branches": {"main": "c3", "feature/orders": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "remote_branches": {"origin/feature/orders": "c2"},
                            "upstream_tracking": {"feature/orders": "origin/feature/orders"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git push origin --delete feature/orders",
                            "git branch -d feature/orders",
                        ],
                        "state_requirements": {
                            "remote_branch_absent": ["origin/feature/orders"],
                            "branch_absent": ["feature/orders"],
                        },
                    },
                    {
                        "case_id": "v29h-parser",
                        "label": "Delete origin/feature/parser and local feature/parser",
                        "context": "Full cleanup of the parser branch: prune stale remote ref, then delete local branch.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature work (merged)",
                                    "parents": ["c1"],
                                    "tree": {"README.md": "readme-v1", "src/parser.py": "par-v1"},
                                },
                                {
                                    "id": "c3",
                                    "message": "Merge feature into main",
                                    "parents": ["c1", "c2"],
                                    "tree": {"README.md": "readme-v1", "src/parser.py": "par-v1"},
                                },
                            ],
                            "branches": {"main": "c3", "feature/parser": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "remote_branches": {"origin/feature/parser": "c2"},
                            "upstream_tracking": {"feature/parser": "origin/feature/parser"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git push origin --delete feature/parser",
                            "git branch -d feature/parser",
                        ],
                        "state_requirements": {
                            "remote_branch_absent": ["origin/feature/parser"],
                            "branch_absent": ["feature/parser"],
                        },
                    },
                    {
                        "case_id": "rb-hard-oss-full",
                        "label": "Delete origin/feature/oss-contribution and local feature/oss-contribution",
                        "context": "The OSS project maintainer merged your PR and the remote feature/oss-contribution branch has been deleted on origin. You also have the local branch. Clean up completely: prune the stale remote tracking ref, then delete your local copy.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c1",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"README.md": "readme-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "OSS contribution (merged)",
                                    "parents": ["c1"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/contrib.py": "contrib-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Merge contribution into main",
                                    "parents": ["c1", "c2"],
                                    "tree": {
                                        "README.md": "readme-v1",
                                        "src/contrib.py": "contrib-v1",
                                    },
                                },
                            ],
                            "branches": {"main": "c3", "feature/oss-contribution": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "remote_branches": {"origin/feature/oss-contribution": "c2"},
                            "upstream_tracking": {
                                "feature/oss-contribution": "origin/feature/oss-contribution"
                            },
                            "remote_stale_branches": ["origin/feature/oss-contribution"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git push origin --delete feature/oss-contribution",
                            "git branch -d feature/oss-contribution",
                        ],
                        "state_requirements": {
                            "remote_branch_absent": ["origin/feature/oss-contribution"],
                            "branch_absent": ["feature/oss-contribution"],
                        },
                    },
                ],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Module 3 - Conflict Resolution
#
# Source: seed_module3_scenarios.py. NO SESSION_COUNTS constant - each of the
# 9 scenario/difficulty required_successful_attempts values is a hardcoded
# literal at its own diff()/call site (see extraction). Confirmed dead code
# excluded per prior agreement: prevention_case, capstone_case,
# accept_ours_easy/theirs_medium/side_hard, merge_abort_easy/medium/hard,
# diagnostic_easy/medium/hard, and their unused target rules - none of these
# are referenced by any scenario actually returned from
# module_three_scenarios() in the source, so they are not ported.
# ---------------------------------------------------------------------------

MODULE_3_LEVELS: list[dict[str, Any]] = [
    {
        "sort_order": 1,
        "slug": "resolving-conflicts-manually",
        "title": "Resolving Merge Conflicts Manually",
        "description": "Resolve conflict content, stage it, and complete the merge.",
        "tiers": {
            "easy": {
                "required_successful_attempts": 3,
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "Complete a single-file manual conflict resolution.",
                "task": "Stage the resolved file and complete the merge commit.",
                "min_counted_commands": 2,
                "cases": [
                    {
                        "case_id": "manual-easy-auth-copy",
                        "label": "Resolve src/auth.js",
                        "context": "Your team is merging feature/auth-timeout into main on auth-service, and src/auth.js has conflicting timeout settings. Resolve the conflict, stage it, and complete the merge.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"src/auth.js": "timeout=3000"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"src/auth.js": "timeout=5000"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"src/auth.js": "timeout=2500"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/auth-timeout": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["src/auth.js"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/auth-timeout",
                            "git add src/auth.js",
                            'git commit -m "Resolve conflict cleanly"',
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "src/auth.js",
                                "content": "timeout=5000\nretry=enabled",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {"src/auth.js": "timeout=5000\nretry=enabled"},
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "manual-easy-profile-copy",
                        "label": "Resolve src/profile.tsx",
                        "context": "The profile-ui team is merging feature/profile-copy into main, and src/profile.tsx has conflicting title/subtitle copy. Resolve the conflict, stage it, and complete the merge.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"src/profile.tsx": "title=Profile"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"src/profile.tsx": "title=Account profile"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"src/profile.tsx": "title=Member profile"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/profile-copy": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["src/profile.tsx"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/profile-copy",
                            "git add src/profile.tsx",
                            'git commit -m "Resolve conflict cleanly"',
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "src/profile.tsx",
                                "content": "title=Account profile\nsubtitle=Member profile",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {
                                        "src/profile.tsx": "title=Account profile\nsubtitle=Member profile"
                                    },
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "manual-easy-billing-copy",
                        "label": "Resolve src/billing.py",
                        "context": "billing-api's feature/regional-currency branch conflicts with main in src/billing.py over supported currencies. Resolve the conflict, stage it, and complete the merge.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"src/billing.py": "currency='USD'"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"src/billing.py": "currency='PHP'"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"src/billing.py": "currency='EUR'"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/regional-currency": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["src/billing.py"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/regional-currency",
                            "git add src/billing.py",
                            'git commit -m "Resolve conflict cleanly"',
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "src/billing.py",
                                "content": "currency='PHP'\nsupported=['PHP','EUR']",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {
                                        "src/billing.py": "currency='PHP'\nsupported=['PHP','EUR']"
                                    },
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "manual-easy-config-copy",
                        "label": "Resolve src/config.py",
                        "context": "config-service's feature/debug-config branch conflicts with main in src/config.py over debug/log settings. Resolve the conflict, stage it, and complete the merge.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"src/config.py": "debug=False"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"src/config.py": "debug=False\nlog_level=INFO"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"src/config.py": "debug=True\nlog_level=DEBUG"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/debug-config": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["src/config.py"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/debug-config",
                            "git add src/config.py",
                            'git commit -m "Resolve conflict cleanly"',
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "src/config.py",
                                "content": "debug=False\nlog_level=INFO\nverbose_errors=True",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {
                                        "src/config.py": "debug=False\nlog_level=INFO\nverbose_errors=True"
                                    },
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "manual-easy-navbar-copy",
                        "label": "Resolve src/components/Navbar.tsx",
                        "context": "frontend-app's feature/navbar-rebrand branch conflicts with main in the Navbar component over brand/tagline. Resolve the conflict, stage it, and complete the merge.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"src/components/Navbar.tsx": "brand=AppName"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"src/components/Navbar.tsx": "brand=MyApp"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"src/components/Navbar.tsx": "brand=BetaApp"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/navbar-rebrand": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["src/components/Navbar.tsx"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/navbar-rebrand",
                            "git add src/components/Navbar.tsx",
                            'git commit -m "Resolve conflict cleanly"',
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "src/components/Navbar.tsx",
                                "content": "brand=MyApp\ntagline=Beta",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {
                                        "src/components/Navbar.tsx": "brand=MyApp\ntagline=Beta"
                                    },
                                }
                            ],
                        },
                    },
                ],
            },
            "medium": {
                "required_successful_attempts": 3,
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "Resolve conflict content in a slightly larger branch context.",
                "task": "Commit the clean resolved content with the requested message.",
                "min_counted_commands": 2,
                "cases": [
                    {
                        "case_id": "manual-medium-router",
                        "label": "Resolve src/routes.ts",
                        "context": 'support-portal\'s integration branch conflicts with main in src/routes.ts. Resolve the conflict and commit with message "Resolve integration conflict".',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"src/routes.ts": "route-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"src/routes.ts": "route-main"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"src/routes.ts": "route-feature"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/routes": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["src/routes.ts"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/routes",
                            "git add src/routes.ts",
                            'git commit -m "Resolve integration conflict"',
                        ],
                        "solution_workspace_files": [
                            {"mode": "write", "path": "src/routes.ts", "content": "route-resolved"}
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {"src/routes.ts": "route-resolved"},
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "manual-medium-policy",
                        "label": "Resolve src/policy.yml",
                        "context": 'policy-engine\'s integration branch conflicts with main in src/policy.yml. Resolve the conflict and commit with message "Resolve integration conflict".',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"src/policy.yml": "policy-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"src/policy.yml": "policy-main"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"src/policy.yml": "policy-feature"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/policy": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["src/policy.yml"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/policy",
                            "git add src/policy.yml",
                            'git commit -m "Resolve integration conflict"',
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "src/policy.yml",
                                "content": "policy-resolved",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {"src/policy.yml": "policy-resolved"},
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "manual-medium-gateway",
                        "label": "Resolve config/gateway.yml",
                        "context": 'api-gateway\'s integration branch conflicts with main in config/gateway.yml. Resolve the conflict and commit with message "Resolve integration conflict".',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"config/gateway.yml": "gateway-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"config/gateway.yml": "gateway-main"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"config/gateway.yml": "gateway-feature"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/gateway": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["config/gateway.yml"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/gateway",
                            "git add config/gateway.yml",
                            'git commit -m "Resolve integration conflict"',
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "config/gateway.yml",
                                "content": "gateway-resolved",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {"config/gateway.yml": "gateway-resolved"},
                                }
                            ],
                        },
                    },
                ],
            },
            "hard": {
                "required_successful_attempts": 2,
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "Resolve conflict situations based on the requested outcome.",
                "task": "Produce the clean target state for the conflicted merge.",
                "min_counted_commands": 2,
                "cases": [
                    {
                        "case_id": "manual-hard-pricing",
                        "label": "Resolve src/pricing.rb",
                        "context": 'pricing-service\'s release branch conflicts with main in src/pricing.rb. Resolve the conflict and commit with message "Resolve release conflict".',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"src/pricing.rb": "pricing-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"src/pricing.rb": "pricing-main"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"src/pricing.rb": "pricing-feature"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/pricing": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["src/pricing.rb"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/pricing",
                            "git add src/pricing.rb",
                            'git commit -m "Resolve release conflict"',
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "src/pricing.rb",
                                "content": "pricing-resolved",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {"src/pricing.rb": "pricing-resolved"},
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "manual-hard-schema",
                        "label": "Resolve schema/orders.sql",
                        "context": 'warehouse-sync\'s release branch conflicts with main in schema/orders.sql. Resolve the conflict and commit with message "Resolve release conflict".',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"schema/orders.sql": "schema-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"schema/orders.sql": "schema-main"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"schema/orders.sql": "schema-feature"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/schema": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["schema/orders.sql"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/schema",
                            "git add schema/orders.sql",
                            'git commit -m "Resolve release conflict"',
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "schema/orders.sql",
                                "content": "schema-resolved",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {"schema/orders.sql": "schema-resolved"},
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "manual-hard-migration",
                        "label": "Resolve db/migrations/001_users.sql",
                        "context": 'user-service\'s release branch conflicts with main in db/migrations/001_users.sql. Resolve the conflict and commit with message "Resolve release conflict".',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"db/migrations/001_users.sql": "migration-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"db/migrations/001_users.sql": "migration-main"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"db/migrations/001_users.sql": "migration-feature"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/migration": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["db/migrations/001_users.sql"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/migration",
                            "git add db/migrations/001_users.sql",
                            'git commit -m "Resolve release conflict"',
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "db/migrations/001_users.sql",
                                "content": "migration-resolved",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {"db/migrations/001_users.sql": "migration-resolved"},
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "manual-hard-medium-carryover",
                        "label": "Resolve src/routes.ts (hard)",
                        "context": 'The routing conflict reappears with less scaffolding: resolve src/routes.ts on support-portal\'s integration branch and commit with message "Resolve release conflict".',
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"src/routes.ts": "route('/help')"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"src/routes.ts": "route('/support')"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"src/routes.ts": "route('/help-center')"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/help-center": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["src/routes.ts"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/help-center",
                            "git add src/routes.ts",
                            'git commit -m "Resolve release conflict"',
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "src/routes.ts",
                                "content": "route('/support')\nroute('/help-center')",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {
                                        "src/routes.ts": "route('/support')\nroute('/help-center')"
                                    },
                                }
                            ],
                        },
                    },
                ],
            },
        },
    },
    {
        "sort_order": 2,
        "slug": "using-a-merge-tool",
        "title": "Resolving Conflicts Using a Merge Tool",
        "description": "Configure and run a merge tool to resolve conflicts.",
        "tiers": {
            "easy": {
                "required_successful_attempts": 2,
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "Resolve the conflict and finish the merge with the shortest valid workflow.",
                "task": "Merge the named source branch, resolve the conflicted file, stage it, and commit.",
                "min_counted_commands": 3,
                "cases": [
                    {
                        "case_id": "mergetool-easy-auth-copy",
                        "label": "Merge tool resolve src/auth.js",
                        "context": "Use a merge tool workflow to resolve src/auth.js on auth-service's feature/auth-timeout branch, stage it, and commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"src/auth.js": "timeout=3000"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"src/auth.js": "timeout=5000"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"src/auth.js": "timeout=2500"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/auth-timeout": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["src/auth.js"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/auth-timeout",
                            "git add src/auth.js",
                            "git commit",
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "src/auth.js",
                                "content": "timeout=5000\nretry=enabled",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {"src/auth.js": "timeout=5000\nretry=enabled"},
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "mergetool-easy-profile-copy",
                        "label": "Merge tool resolve src/profile.tsx",
                        "context": "Use a merge tool workflow to resolve src/profile.tsx on profile-ui's feature/profile-copy branch, stage it, and commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"src/profile.tsx": "title=Profile"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"src/profile.tsx": "title=Account profile"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"src/profile.tsx": "title=Member profile"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/profile-copy": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["src/profile.tsx"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/profile-copy",
                            "git add src/profile.tsx",
                            "git commit",
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "src/profile.tsx",
                                "content": "title=Account profile\nsubtitle=Member profile",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {
                                        "src/profile.tsx": "title=Account profile\nsubtitle=Member profile"
                                    },
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "mergetool-easy-billing-copy",
                        "label": "Merge tool resolve src/billing.py",
                        "context": "Use a merge tool workflow to resolve src/billing.py on billing-api's feature/regional-currency branch, stage it, and commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"src/billing.py": "currency='USD'"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"src/billing.py": "currency='PHP'"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"src/billing.py": "currency='EUR'"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/regional-currency": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["src/billing.py"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/regional-currency",
                            "git add src/billing.py",
                            "git commit",
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "src/billing.py",
                                "content": "currency='PHP'\nsupported=['PHP','EUR']",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {
                                        "src/billing.py": "currency='PHP'\nsupported=['PHP','EUR']"
                                    },
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "mergetool-easy-config-copy",
                        "label": "Merge tool resolve src/config.py",
                        "context": "Use a merge tool workflow to resolve src/config.py on config-service's feature/debug-config branch, stage it, and commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"src/config.py": "debug=False"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"src/config.py": "debug=False\nlog_level=INFO"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"src/config.py": "debug=True\nlog_level=DEBUG"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/debug-config": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["src/config.py"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/debug-config",
                            "git add src/config.py",
                            "git commit",
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "src/config.py",
                                "content": "debug=False\nlog_level=INFO\nverbose_errors=True",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {
                                        "src/config.py": "debug=False\nlog_level=INFO\nverbose_errors=True"
                                    },
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "mergetool-easy-navbar-copy",
                        "label": "Merge tool resolve src/components/Navbar.tsx",
                        "context": "Use a merge tool workflow to resolve the Navbar component on frontend-app's feature/navbar-rebrand branch, stage it, and commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"src/components/Navbar.tsx": "brand=AppName"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"src/components/Navbar.tsx": "brand=MyApp"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"src/components/Navbar.tsx": "brand=BetaApp"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/navbar-rebrand": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["src/components/Navbar.tsx"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/navbar-rebrand",
                            "git add src/components/Navbar.tsx",
                            "git commit",
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "src/components/Navbar.tsx",
                                "content": "brand=MyApp\ntagline=Beta",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {
                                        "src/components/Navbar.tsx": "brand=MyApp\ntagline=Beta"
                                    },
                                }
                            ],
                        },
                    },
                ],
            },
            "medium": {
                "required_successful_attempts": 2,
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "Resolve branch conflicts with different file types.",
                "task": "Merge the named source branch, resolve the conflicted file, stage it, and commit.",
                "min_counted_commands": 3,
                "cases": [
                    {
                        "case_id": "mergetool-medium-router",
                        "label": "Merge tool resolve src/routes.ts",
                        "context": "Use a merge tool workflow to resolve src/routes.ts on support-portal's feature/routes branch, stage it, and commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"src/routes.ts": "route-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"src/routes.ts": "route-main"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"src/routes.ts": "route-feature"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/routes": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["src/routes.ts"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/routes",
                            "git add src/routes.ts",
                            "git commit",
                        ],
                        "solution_workspace_files": [
                            {"mode": "write", "path": "src/routes.ts", "content": "route-resolved"}
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {"src/routes.ts": "route-resolved"},
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "mergetool-medium-policy",
                        "label": "Merge tool resolve src/policy.yml",
                        "context": "Use a merge tool workflow to resolve src/policy.yml on policy-engine's feature/policy branch, stage it, and commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"src/policy.yml": "policy-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"src/policy.yml": "policy-main"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"src/policy.yml": "policy-feature"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/policy": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["src/policy.yml"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/policy",
                            "git add src/policy.yml",
                            "git commit",
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "src/policy.yml",
                                "content": "policy-resolved",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {"src/policy.yml": "policy-resolved"},
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "mergetool-medium-gateway",
                        "label": "Merge tool resolve config/gateway.yml",
                        "context": "Use a merge tool workflow to resolve config/gateway.yml on api-gateway's feature/gateway branch, stage it, and commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"config/gateway.yml": "gateway-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"config/gateway.yml": "gateway-main"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"config/gateway.yml": "gateway-feature"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/gateway": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["config/gateway.yml"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/gateway",
                            "git add config/gateway.yml",
                            "git commit",
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "config/gateway.yml",
                                "content": "gateway-resolved",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {"config/gateway.yml": "gateway-resolved"},
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "mergetool-medium-easy-carryover",
                        "label": "Merge tool resolve src/auth.js (medium)",
                        "context": "The auth timeout conflict reappears with a different file type mix: use a merge tool workflow to resolve src/auth.js, stage it, and commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"src/auth.js": "timeout=3000"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"src/auth.js": "timeout=5000"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"src/auth.js": "timeout=2500"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/auth-timeout": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["src/auth.js"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/auth-timeout",
                            "git add src/auth.js",
                            "git commit",
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "src/auth.js",
                                "content": "timeout=5000\nretry=enabled",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {"src/auth.js": "timeout=5000\nretry=enabled"},
                                }
                            ],
                        },
                    },
                ],
            },
            "hard": {
                "required_successful_attempts": 2,
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "Resolve the merge conflict without extra scaffolding.",
                "task": "Merge the named source branch, resolve the conflicted file, stage it, and commit.",
                "min_counted_commands": 3,
                "cases": [
                    {
                        "case_id": "mergetool-hard-pricing",
                        "label": "Merge tool resolve src/pricing.rb",
                        "context": "Use a merge tool workflow to resolve src/pricing.rb on pricing-service's feature/pricing branch, stage it, and commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"src/pricing.rb": "pricing-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"src/pricing.rb": "pricing-main"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"src/pricing.rb": "pricing-feature"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/pricing": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["src/pricing.rb"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/pricing",
                            "git add src/pricing.rb",
                            "git commit",
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "src/pricing.rb",
                                "content": "pricing-resolved",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {"src/pricing.rb": "pricing-resolved"},
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "mergetool-hard-schema",
                        "label": "Merge tool resolve schema/orders.sql",
                        "context": "Use a merge tool workflow to resolve schema/orders.sql on warehouse-sync's feature/schema branch, stage it, and commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"schema/orders.sql": "schema-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"schema/orders.sql": "schema-main"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"schema/orders.sql": "schema-feature"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/schema": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["schema/orders.sql"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/schema",
                            "git add schema/orders.sql",
                            "git commit",
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "schema/orders.sql",
                                "content": "schema-resolved",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {"schema/orders.sql": "schema-resolved"},
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "mergetool-hard-migration",
                        "label": "Merge tool resolve db/migrations/001_users.sql",
                        "context": "Use a merge tool workflow to resolve db/migrations/001_users.sql on user-service's feature/migration branch, stage it, and commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"db/migrations/001_users.sql": "migration-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"db/migrations/001_users.sql": "migration-main"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"db/migrations/001_users.sql": "migration-feature"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/migration": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["db/migrations/001_users.sql"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/migration",
                            "git add db/migrations/001_users.sql",
                            "git commit",
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "db/migrations/001_users.sql",
                                "content": "migration-resolved",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {"db/migrations/001_users.sql": "migration-resolved"},
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "mergetool-hard-medium-carryover",
                        "label": "Merge tool resolve src/routes.ts (hard)",
                        "context": "The routing conflict reappears without scaffolding: use a merge tool workflow to resolve src/routes.ts on support-portal's feature/help-center branch, stage it, and commit.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Base commit",
                                    "parents": [],
                                    "tree": {"src/routes.ts": "route('/help')"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Main update",
                                    "parents": ["c0"],
                                    "tree": {"src/routes.ts": "route('/support')"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Feature branch update",
                                    "parents": ["c0"],
                                    "tree": {"src/routes.ts": "route('/help-center')"},
                                },
                            ],
                            "branches": {"main": "c1", "feature/help-center": "c2"},
                            "head": {"type": "branch", "name": "main"},
                            "conflict_on_merge": True,
                            "conflict_files": ["src/routes.ts"],
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": [
                            "git merge feature/help-center",
                            "git add src/routes.ts",
                            "git commit",
                        ],
                        "solution_workspace_files": [
                            {
                                "mode": "write",
                                "path": "src/routes.ts",
                                "content": "route('/support')\nroute('/help-center')",
                            }
                        ],
                        "state_requirements": {
                            "head_branch": "main",
                            "staging_empty": True,
                            "working_tree_clean": True,
                            "conflict_free": True,
                            "rules": [
                                {
                                    "type": "merge_commit_contains_tree",
                                    "tree": {
                                        "src/routes.ts": "route('/support')\nroute('/help-center')"
                                    },
                                }
                            ],
                        },
                    },
                ],
            },
        },
    },
    {
        "sort_order": 3,
        "slug": "cherry-picking-commits",
        "title": "Cherry-Picking Commits",
        "description": "Apply selected commits without merging an entire branch.",
        "tiers": {
            "easy": {
                "required_successful_attempts": 3,
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "Cherry-pick one named fix onto the current release branch.",
                "task": "Apply the selected commit as a new commit on the current branch.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "cherry-easy-login-timeout",
                        "label": "Cherry-pick c1 onto release-1.0",
                        "context": "release-1.0 needs the login timeout fix (commit c1) applied directly, without merging all of main.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Baseline",
                                    "parents": [],
                                    "tree": {"src/login.js": "login-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Fix login timeout",
                                    "parents": ["c0"],
                                    "tree": {"src/login.js": "timeout-fix-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Main continues",
                                    "parents": ["c1"],
                                    "tree": {
                                        "src/login.js": "timeout-fix-v1",
                                        "src/other.js": "other-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Release branch base",
                                    "parents": ["c0"],
                                    "tree": {"src/login.js": "login-base"},
                                },
                            ],
                            "branches": {"main": "c2", "release-1.0": "c3"},
                            "head": {"type": "branch", "name": "release-1.0"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git cherry-pick c1"],
                        "state_requirements": {
                            "head_branch": "release-1.0",
                            "rules": [
                                {"type": "cherry_pick_created_new_commit"},
                                {"type": "cherry_pick_copied_changes_from", "commit": "c1"},
                                {
                                    "type": "commit_tree_contains_tokens",
                                    "tokens": ["timeout-fix-v1"],
                                },
                            ],
                        },
                    },
                    {
                        "case_id": "cherry-easy-invoice-rounding",
                        "label": "Cherry-pick c1 onto release-1.1",
                        "context": "release-1.1 needs the invoice rounding fix (commit c1) applied directly.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Baseline",
                                    "parents": [],
                                    "tree": {"src/invoice.py": "invoice-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Fix rounding",
                                    "parents": ["c0"],
                                    "tree": {"src/invoice.py": "rounding-fix-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Main continues",
                                    "parents": ["c1"],
                                    "tree": {
                                        "src/invoice.py": "rounding-fix-v1",
                                        "src/other.py": "other-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Release branch base",
                                    "parents": ["c0"],
                                    "tree": {"src/invoice.py": "invoice-base"},
                                },
                            ],
                            "branches": {"main": "c2", "release-1.1": "c3"},
                            "head": {"type": "branch", "name": "release-1.1"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git cherry-pick c1"],
                        "state_requirements": {
                            "head_branch": "release-1.1",
                            "rules": [
                                {"type": "cherry_pick_created_new_commit"},
                                {"type": "cherry_pick_copied_changes_from", "commit": "c1"},
                                {
                                    "type": "commit_tree_contains_tokens",
                                    "tokens": ["rounding-fix-v1"],
                                },
                            ],
                        },
                    },
                    {
                        "case_id": "cherry-easy-export-null",
                        "label": "Cherry-pick c1 onto release-2.0",
                        "context": "release-2.0 needs the export null-check fix (commit c1) applied directly.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Baseline",
                                    "parents": [],
                                    "tree": {"src/export.ts": "export-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Fix null export",
                                    "parents": ["c0"],
                                    "tree": {"src/export.ts": "null-export-fix"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Main continues",
                                    "parents": ["c1"],
                                    "tree": {
                                        "src/export.ts": "null-export-fix",
                                        "src/other.ts": "other-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Release branch base",
                                    "parents": ["c0"],
                                    "tree": {"src/export.ts": "export-base"},
                                },
                            ],
                            "branches": {"main": "c2", "release-2.0": "c3"},
                            "head": {"type": "branch", "name": "release-2.0"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git cherry-pick c1"],
                        "state_requirements": {
                            "head_branch": "release-2.0",
                            "rules": [
                                {"type": "cherry_pick_created_new_commit"},
                                {"type": "cherry_pick_copied_changes_from", "commit": "c1"},
                                {
                                    "type": "commit_tree_contains_tokens",
                                    "tokens": ["null-export-fix"],
                                },
                            ],
                        },
                    },
                    {
                        "case_id": "cherry-easy-rate-limit",
                        "label": "Cherry-pick c1 onto release-1.2",
                        "context": "release-1.2 needs the rate-limit fix (commit c1) applied directly.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Baseline",
                                    "parents": [],
                                    "tree": {"src/ratelimit.py": "ratelimit-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Fix rate limit",
                                    "parents": ["c0"],
                                    "tree": {"src/ratelimit.py": "rate-limit-fix-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Main continues",
                                    "parents": ["c1"],
                                    "tree": {
                                        "src/ratelimit.py": "rate-limit-fix-v1",
                                        "src/other.py": "other-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Release branch base",
                                    "parents": ["c0"],
                                    "tree": {"src/ratelimit.py": "ratelimit-base"},
                                },
                            ],
                            "branches": {"main": "c2", "release-1.2": "c3"},
                            "head": {"type": "branch", "name": "release-1.2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git cherry-pick c1"],
                        "state_requirements": {
                            "head_branch": "release-1.2",
                            "rules": [
                                {"type": "cherry_pick_created_new_commit"},
                                {"type": "cherry_pick_copied_changes_from", "commit": "c1"},
                                {
                                    "type": "commit_tree_contains_tokens",
                                    "tokens": ["rate-limit-fix-v1"],
                                },
                            ],
                        },
                    },
                    {
                        "case_id": "cherry-easy-null-check",
                        "label": "Cherry-pick c1 onto release-2.1",
                        "context": "release-2.1 needs the parser null-check fix (commit c1) applied directly.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Baseline",
                                    "parents": [],
                                    "tree": {"src/parser.ts": "parser-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Fix null check",
                                    "parents": ["c0"],
                                    "tree": {"src/parser.ts": "null-check-fix-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Main continues",
                                    "parents": ["c1"],
                                    "tree": {
                                        "src/parser.ts": "null-check-fix-v1",
                                        "src/other.ts": "other-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Release branch base",
                                    "parents": ["c0"],
                                    "tree": {"src/parser.ts": "parser-base"},
                                },
                            ],
                            "branches": {"main": "c2", "release-2.1": "c3"},
                            "head": {"type": "branch", "name": "release-2.1"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git cherry-pick c1"],
                        "state_requirements": {
                            "head_branch": "release-2.1",
                            "rules": [
                                {"type": "cherry_pick_created_new_commit"},
                                {"type": "cherry_pick_copied_changes_from", "commit": "c1"},
                                {
                                    "type": "commit_tree_contains_tokens",
                                    "tokens": ["null-check-fix-v1"],
                                },
                            ],
                        },
                    },
                ],
            },
            "medium": {
                "required_successful_attempts": 3,
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "Cherry-pick either directly or into the index for review.",
                "task": "Reach the requested cherry-pick state.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "cherry-medium-login-timeout",
                        "label": "Cherry-pick c1 onto release-1.0 (medium)",
                        "context": "The login timeout fix needs to reach release-1.0 with less guidance this time.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Baseline",
                                    "parents": [],
                                    "tree": {"src/login.js": "login-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Fix login timeout",
                                    "parents": ["c0"],
                                    "tree": {"src/login.js": "timeout-fix-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Main continues",
                                    "parents": ["c1"],
                                    "tree": {
                                        "src/login.js": "timeout-fix-v1",
                                        "src/other.js": "other-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Release branch base",
                                    "parents": ["c0"],
                                    "tree": {"src/login.js": "login-base"},
                                },
                            ],
                            "branches": {"main": "c2", "release-1.0": "c3"},
                            "head": {"type": "branch", "name": "release-1.0"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git cherry-pick c1"],
                        "state_requirements": {
                            "head_branch": "release-1.0",
                            "rules": [
                                {"type": "cherry_pick_created_new_commit"},
                                {"type": "cherry_pick_copied_changes_from", "commit": "c1"},
                                {
                                    "type": "commit_tree_contains_tokens",
                                    "tokens": ["timeout-fix-v1"],
                                },
                            ],
                        },
                    },
                    {
                        "case_id": "cherry-medium-invoice-rounding",
                        "label": "Cherry-pick c1 onto release-1.1 (medium)",
                        "context": "The rounding fix needs to reach release-1.1 with less guidance this time.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Baseline",
                                    "parents": [],
                                    "tree": {"src/invoice.py": "invoice-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Fix rounding",
                                    "parents": ["c0"],
                                    "tree": {"src/invoice.py": "rounding-fix-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Main continues",
                                    "parents": ["c1"],
                                    "tree": {
                                        "src/invoice.py": "rounding-fix-v1",
                                        "src/other.py": "other-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Release branch base",
                                    "parents": ["c0"],
                                    "tree": {"src/invoice.py": "invoice-base"},
                                },
                            ],
                            "branches": {"main": "c2", "release-1.1": "c3"},
                            "head": {"type": "branch", "name": "release-1.1"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git cherry-pick c1"],
                        "state_requirements": {
                            "head_branch": "release-1.1",
                            "rules": [
                                {"type": "cherry_pick_created_new_commit"},
                                {"type": "cherry_pick_copied_changes_from", "commit": "c1"},
                                {
                                    "type": "commit_tree_contains_tokens",
                                    "tokens": ["rounding-fix-v1"],
                                },
                            ],
                        },
                    },
                    {
                        "case_id": "cherry-medium-no-commit",
                        "label": "Cherry-pick c1 into the index (no commit) on release-review",
                        "context": "release-review wants the report hotfix (commit c1) staged for review before committing -- cherry-pick without committing.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Baseline",
                                    "parents": [],
                                    "tree": {"src/report.ts": "report-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Fix report hotfix",
                                    "parents": ["c0"],
                                    "tree": {"src/report.ts": "report-hotfix"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Main continues",
                                    "parents": ["c1"],
                                    "tree": {
                                        "src/report.ts": "report-hotfix",
                                        "src/other.ts": "other-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Review branch base",
                                    "parents": ["c0"],
                                    "tree": {"src/report.ts": "report-base"},
                                },
                            ],
                            "branches": {"main": "c2", "release-review": "c3"},
                            "head": {"type": "branch", "name": "release-review"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git cherry-pick --no-commit c1"],
                        "state_requirements": {
                            "head_branch": "release-review",
                            "staging_contains": ["src/report.ts"],
                            "staging_contains_tokens": ["report-hotfix"],
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_cherry_pick_source",
                                    "value": "c1",
                                }
                            ],
                        },
                    },
                    {
                        "case_id": "cherry-medium-staged-review",
                        "label": "Cherry-pick c1 into the index (no commit) on release-staged",
                        "context": "release-staged wants the cache hotfix (commit c1) staged for review before committing -- cherry-pick without committing.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Baseline",
                                    "parents": [],
                                    "tree": {"src/cache.py": "cache-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Fix cache hotfix",
                                    "parents": ["c0"],
                                    "tree": {"src/cache.py": "cache-hotfix"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Main continues",
                                    "parents": ["c1"],
                                    "tree": {
                                        "src/cache.py": "cache-hotfix",
                                        "src/other.py": "other-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Staged branch base",
                                    "parents": ["c0"],
                                    "tree": {"src/cache.py": "cache-base"},
                                },
                            ],
                            "branches": {"main": "c2", "release-staged": "c3"},
                            "head": {"type": "branch", "name": "release-staged"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git cherry-pick --no-commit c1"],
                        "state_requirements": {
                            "head_branch": "release-staged",
                            "staging_contains": ["src/cache.py"],
                            "staging_contains_tokens": ["cache-hotfix"],
                            "rules": [
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_cherry_pick_source",
                                    "value": "c1",
                                }
                            ],
                        },
                    },
                ],
            },
            "hard": {
                "required_successful_attempts": 2,
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "Choose between completing and aborting cherry-pick states.",
                "task": "Reach the requested selective-application outcome.",
                "min_counted_commands": 1,
                "cases": [
                    {
                        "case_id": "cherry-hard-export-null",
                        "label": "Cherry-pick c1 onto release-2.0 (hard)",
                        "context": "The export null-check fix needs to reach release-2.0 with minimal scaffolding.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Baseline",
                                    "parents": [],
                                    "tree": {"src/export.ts": "export-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Fix null export",
                                    "parents": ["c0"],
                                    "tree": {"src/export.ts": "null-export-fix"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Main continues",
                                    "parents": ["c1"],
                                    "tree": {
                                        "src/export.ts": "null-export-fix",
                                        "src/other.ts": "other-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Release branch base",
                                    "parents": ["c0"],
                                    "tree": {"src/export.ts": "export-base"},
                                },
                            ],
                            "branches": {"main": "c2", "release-2.0": "c3"},
                            "head": {"type": "branch", "name": "release-2.0"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git cherry-pick c1"],
                        "state_requirements": {
                            "head_branch": "release-2.0",
                            "rules": [
                                {"type": "cherry_pick_created_new_commit"},
                                {"type": "cherry_pick_copied_changes_from", "commit": "c1"},
                                {
                                    "type": "commit_tree_contains_tokens",
                                    "tokens": ["null-export-fix"],
                                },
                            ],
                        },
                    },
                    {
                        "case_id": "cherry-hard-abort",
                        "label": "Abort a cherry-pick in progress on release-abort",
                        "context": "A cherry-pick of the search hotfix (commit c1) is in progress on release-abort but should be abandoned. Abort it and restore the original checkout.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Baseline",
                                    "parents": [],
                                    "tree": {"src/search.ts": "search-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Fix search hotfix",
                                    "parents": ["c0"],
                                    "tree": {"src/search.ts": "search-hotfix"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Main continues",
                                    "parents": ["c1"],
                                    "tree": {
                                        "src/search.ts": "search-hotfix",
                                        "src/other.ts": "other-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Abort branch base",
                                    "parents": ["c0"],
                                    "tree": {"src/search.ts": "search-base"},
                                },
                            ],
                            "branches": {"main": "c2", "release-abort": "c3"},
                            "head": {"type": "branch", "name": "release-abort"},
                            "cherry_pick_in_progress": True,
                            "cherry_pick_original_head": "c3",
                            "staging": {
                                "src/search.ts": {"status": "modified", "content": "search-hotfix"}
                            },
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git cherry-pick --abort"],
                        "state_requirements": {
                            "head_branch": "release-abort",
                            "rules": [
                                {
                                    "type": "branch_points_to",
                                    "branch": "release-abort",
                                    "commit": "c3",
                                },
                                {
                                    "type": "operation_metadata_equals",
                                    "key": "last_cherry_pick_aborted",
                                    "value": True,
                                },
                            ],
                        },
                    },
                    {
                        "case_id": "cherry-hard-queue-finalize",
                        "label": "Cherry-pick c1 onto release-finalize",
                        "context": "The queue hotfix (commit c1) needs to finalize onto release-finalize.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Baseline",
                                    "parents": [],
                                    "tree": {"src/queue.ts": "queue-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Fix queue hotfix",
                                    "parents": ["c0"],
                                    "tree": {"src/queue.ts": "queue-hotfix"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Main continues",
                                    "parents": ["c1"],
                                    "tree": {
                                        "src/queue.ts": "queue-hotfix",
                                        "src/other.ts": "other-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Finalize branch base",
                                    "parents": ["c0"],
                                    "tree": {"src/queue.ts": "queue-base"},
                                },
                            ],
                            "branches": {"main": "c2", "release-finalize": "c3"},
                            "head": {"type": "branch", "name": "release-finalize"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git cherry-pick c1"],
                        "state_requirements": {
                            "head_branch": "release-finalize",
                            "rules": [
                                {"type": "cherry_pick_created_new_commit"},
                                {"type": "cherry_pick_copied_changes_from", "commit": "c1"},
                                {"type": "commit_tree_contains_tokens", "tokens": ["queue-hotfix"]},
                            ],
                        },
                    },
                    {
                        "case_id": "cherry-hard-rate-limit",
                        "label": "Cherry-pick c1 onto release-1.2 (hard)",
                        "context": "The rate-limit fix needs to reach release-1.2 with minimal scaffolding.",
                        "initial_state": {
                            "repository_initialized": True,
                            "commits": [
                                {
                                    "id": "c0",
                                    "message": "Baseline",
                                    "parents": [],
                                    "tree": {"src/ratelimit.py": "ratelimit-base"},
                                },
                                {
                                    "id": "c1",
                                    "message": "Fix rate limit",
                                    "parents": ["c0"],
                                    "tree": {"src/ratelimit.py": "rate-limit-fix-v1"},
                                },
                                {
                                    "id": "c2",
                                    "message": "Main continues",
                                    "parents": ["c1"],
                                    "tree": {
                                        "src/ratelimit.py": "rate-limit-fix-v1",
                                        "src/other.py": "other-v1",
                                    },
                                },
                                {
                                    "id": "c3",
                                    "message": "Release branch base",
                                    "parents": ["c0"],
                                    "tree": {"src/ratelimit.py": "ratelimit-base"},
                                },
                            ],
                            "branches": {"main": "c2", "release-1.2": "c3"},
                            "head": {"type": "branch", "name": "release-1.2"},
                            "staging": {},
                            "working_tree": {},
                            "conflicts": [],
                        },
                        "solution_commands": ["git cherry-pick c1"],
                        "state_requirements": {
                            "head_branch": "release-1.2",
                            "rules": [
                                {"type": "cherry_pick_created_new_commit"},
                                {"type": "cherry_pick_copied_changes_from", "commit": "c1"},
                                {
                                    "type": "commit_tree_contains_tokens",
                                    "tokens": ["rate-limit-fix-v1"],
                                },
                            ],
                        },
                    },
                ],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Module 4 - Advanced Recovery and History
#
# Source: seed_module4_scenarios.py. NO SESSION_COUNTS constant - each of the
# 9 scenario/difficulty required_successful_attempts values is a hardcoded
# literal at its own difficulty_spec(..., required_attempts=N) call site (see
# extraction). Each difficulty has exactly one template with 5 generated
# cases (range(1, 6)) sharing the difficulty's target_rule/solution_commands
# shape; only per-case identifiers vary (reset depth suffix, bad_commit,
# rebase suffix). Generated here the same way, rather than hand-transcribing
# 45 near-identical dicts, since the source itself is a generator loop.
# ---------------------------------------------------------------------------


def _module_4_hard_reset_case(index: int, *, depth: int, tier_prefix: str) -> dict[str, Any]:
    case_id = f"{tier_prefix}{index}"
    recovery_branch = f"recovery-4-1-{tier_prefix}{index}"
    incident_variants = [
        "You accidentally ran a hard reset and lost recent commits on main.",
        "A teammate's script ran git reset --hard on your branch by mistake.",
        "You meant to discard one bad commit but reset further back than intended.",
        "A merge attempt went wrong and you reset --hard to recover, losing more than expected.",
        "You reset --hard while debugging and now need to recover the lost tip.",
    ]
    context = incident_variants[(index - 1) % len(incident_variants)]
    return {
        "case_id": case_id,
        "label": f"Recover {recovery_branch}",
        "context": context,
        "initial_state": {
            "repository_initialized": True,
            "commits": [
                {
                    "id": "c0",
                    "message": "Initial commit",
                    "parents": [],
                    "tree": {"README.md": "readme-v0"},
                },
                {
                    "id": "c1",
                    "message": "Add feature groundwork",
                    "parents": ["c0"],
                    "tree": {"README.md": "readme-v1"},
                },
                {
                    "id": "c2",
                    "message": "Continue feature work",
                    "parents": ["c1"],
                    "tree": {"README.md": "readme-v2"},
                },
                {
                    "id": "c3",
                    "message": "Complete feature work (lost tip)",
                    "parents": ["c2"],
                    "tree": {"README.md": "readme-v3"},
                },
            ],
            "branches": {"main": f"c{3 - depth}"},
            "head": {"type": "branch", "name": "main"},
            "reflog": [
                {"ref": "main", "commit": "c3", "action": "commit"},
                {
                    "ref": "main",
                    "commit": f"c{3 - depth}",
                    "action": f"reset: moving to HEAD~{depth}",
                },
            ],
            "staging": {},
            "working_tree": {},
            "conflicts": [],
        },
        "solution_commands": ["git reflog", "git show c3", f"git switch -c {recovery_branch} c3"],
        "state_requirements": {
            "skip_required_commands": True,
            "branch_exists": [recovery_branch],
            "branch_points_to": {recovery_branch: "c3"},
            "staging_empty": True,
            "working_tree_clean": True,
        },
    }


def _module_4_revert_case(index: int, *, bad_commit: str, tier_prefix: str) -> dict[str, Any]:
    case_id = f"{tier_prefix}{index}"
    return {
        "case_id": case_id,
        "label": f"Revert {bad_commit} safely",
        "context": (
            "You are a backend developer in a software company. A risky configuration "
            "change was already pushed to main before QA flagged it as breaking "
            "production behavior."
        ),
        "initial_state": {
            "repository_initialized": True,
            "commits": [
                {
                    "id": "c0",
                    "message": "Initial commit",
                    "parents": [],
                    "tree": {"README.md": "readme-v0"},
                },
                {
                    "id": "c1",
                    "message": "Add config module",
                    "parents": ["c0"],
                    "tree": {"README.md": "readme-v0", "config.py": "config-v1"},
                },
                {
                    "id": "c2",
                    "message": "Risky config change",
                    "parents": ["c1"],
                    "tree": {"README.md": "readme-v0", "config.py": "config-v2-risky"},
                },
                {
                    "id": "c3",
                    "message": "Unrelated follow-up",
                    "parents": ["c2"],
                    "tree": {
                        "README.md": "readme-v0",
                        "config.py": "config-v2-risky",
                        "notes.md": "notes-v1",
                    },
                },
            ],
            "branches": {"main": "c3"},
            "head": {"type": "branch", "name": "main"},
            "remotes": {"origin": "https://example.test/backend-service.git"},
            "remote_branches": {"origin/main": "c3"},
            "upstream_tracking": {"main": "origin/main"},
            "staging": {},
            "working_tree": {},
            "conflicts": [],
        },
        "solution_commands": [f"git revert {bad_commit}", "git push"],
        "state_requirements": {
            "head_branch": "main",
            "working_tree_clean": True,
            "staging_empty": True,
            "conflict_free": True,
            "required_commands": ["git revert", "git push"],
            "rules": [
                {"type": "new_revert_commit_exists"},
                {"type": "revert_preserves_history", "commit": bad_commit, "branch": "main"},
                {
                    "type": "push_moved_remote_to_local_tip",
                    "branch": "main",
                    "remote_branch": "origin/main",
                },
            ],
        },
    }


def _module_4_rebase_case(index: int, *, tier_prefix: str) -> dict[str, Any]:
    case_id = f"{tier_prefix}{index}"
    return {
        "case_id": case_id,
        "label": f"Rebase {case_id}",
        "context": (
            "You are a feature owner in a software company. Your branch diverged while "
            "main moved, and a teammate needs a clean history before code freeze."
        ),
        "initial_state": {
            "repository_initialized": True,
            "commits": [
                {
                    "id": "c0",
                    "message": "Common base",
                    "parents": [],
                    "tree": {"src/app.ts": "app-base", "src/feature.ts": "feature-base"},
                },
                {
                    "id": "c1",
                    "message": "Main update",
                    "parents": ["c0"],
                    "tree": {"src/app.ts": "app-v2", "src/feature.ts": "feature-base"},
                },
                {
                    "id": "c2",
                    "message": "Feature work part 1",
                    "parents": ["c0"],
                    "tree": {"src/app.ts": "app-base", "src/feature.ts": "feature-v2"},
                },
                {
                    "id": "c3",
                    "message": "Feature work part 2",
                    "parents": ["c2"],
                    "tree": {"src/app.ts": "app-base", "src/feature.ts": "feature-v3"},
                },
            ],
            "branches": {"main": "c1", "feature/recovery": "c3"},
            "head": {"type": "branch", "name": "feature/recovery"},
            "staging": {},
            "working_tree": {},
            "conflicts": [],
        },
        "solution_commands": ["git rebase main", "git log --oneline --graph --all"],
        "state_requirements": {
            "skip_required_commands": True,
            "head_branch": "feature/recovery",
            "staging_empty": True,
            "working_tree_clean": True,
            "conflict_free": True,
            "rules": [
                {"type": "branch_moved_back_from_initial", "branch": "feature/recovery"},
                {"type": "min_commits_on_branch", "branch": "feature/recovery", "minimum": 2},
            ],
        },
    }


MODULE_4_LEVELS: list[dict[str, Any]] = [
    {
        "sort_order": 1,
        "slug": "recovering-from-hard-resets",
        "title": "Recovering from Hard Resets",
        "description": "Recover lost work after a destructive reset.",
        "tiers": {
            "easy": {
                "required_successful_attempts": 2,
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "You are a junior engineer handling a low-pressure rollback incident after a shallow mistaken reset.",
                "task": "Find the most recent lost tip and restore it to the requested recovery branch.",
                "min_counted_commands": 2,
                "cases": [
                    _module_4_hard_reset_case(i, depth=1, tier_prefix="e") for i in range(1, 6)
                ],
            },
            "medium": {
                "required_successful_attempts": 1,
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "You are the sprint lead responding to a deeper mistaken reset with limited guidance from teammates.",
                "task": "Trace the correct history entry and restore the branch to the requested recovery point.",
                "min_counted_commands": 2,
                "cases": [
                    _module_4_hard_reset_case(i, depth=2, tier_prefix="m") for i in range(1, 6)
                ],
            },
            "hard": {
                "required_successful_attempts": 1,
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "You are the incident commander recovering critical work from a noisy reset trail under release pressure.",
                "task": "Disambiguate noisy history evidence and recover exactly the requested lost tip branch.",
                "min_counted_commands": 2,
                "cases": [
                    _module_4_hard_reset_case(i, depth=3, tier_prefix="h") for i in range(1, 6)
                ],
            },
        },
    },
    {
        "sort_order": 2,
        "slug": "reversing-pushed-commits-safely",
        "title": "Reversing Pushed Commits Safely",
        "description": "Use revert to preserve shared history.",
        "tiers": {
            "easy": {
                "required_successful_attempts": 2,
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "You are a developer handling a straightforward rollback request right after a bad push.",
                "task": "Append the rollback commit for the target change and ensure remote main is updated.",
                "min_counted_commands": 2,
                "cases": [
                    _module_4_revert_case(i, bad_commit="c3", tier_prefix="re") for i in range(1, 6)
                ],
            },
            "medium": {
                "required_successful_attempts": 1,
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "You are supporting QA during regression triage, and the bad change is buried in published history.",
                "task": "Identify the correct published change to roll back and synchronize the shared branch.",
                "min_counted_commands": 2,
                "cases": [
                    _module_4_revert_case(i, bad_commit="c2", tier_prefix="rm") for i in range(1, 6)
                ],
            },
            "hard": {
                "required_successful_attempts": 1,
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "You are the release owner during a high-stakes deploy window with strict rollback constraints.",
                "task": "Execute the required rollback while preserving shared history integrity across local and remote.",
                "min_counted_commands": 2,
                "cases": [
                    _module_4_revert_case(i, bad_commit="c2", tier_prefix="rh") for i in range(1, 6)
                ],
            },
        },
    },
    {
        "sort_order": 3,
        "slug": "completing-rebase-recovery-sequences",
        "title": "Completing Rebase Recovery Sequences",
        "description": "Finish a full rebase recovery workflow.",
        "tiers": {
            "easy": {
                "required_successful_attempts": 2,
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["easy"],
                "story": "You are finishing a normal sprint task where your feature branch simply drifted from main.",
                "task": "Recover the branch onto the current main line and confirm the repository is clean.",
                "min_counted_commands": 1,
                "cases": [_module_4_rebase_case(i, tier_prefix="be") for i in range(1, 6)],
            },
            "medium": {
                "required_successful_attempts": 1,
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["medium"],
                "story": "You are coordinating with reviewers who need a refined commit sequence before acceptance.",
                "task": "Run an interactive recovery flow and verify no incomplete rebase state remains.",
                "min_counted_commands": 1,
                "cases": [_module_4_rebase_case(i, tier_prefix="bm") for i in range(1, 6)],
            },
            "hard": {
                "required_successful_attempts": 1,
                "max_counted_commands": DIFFICULTY_MAX_COUNTED_COMMANDS["hard"],
                "story": "You are driving final release cleanup, and branch integrity checks are stricter than usual.",
                "task": "Complete the full recovery sequence and validate branch integrity with all required checks.",
                "min_counted_commands": 1,
                "cases": [_module_4_rebase_case(i, tier_prefix="bh") for i in range(1, 6)],
            },
        },
    },
]


class Command(BaseCommand):
    help = "Seed the archived Module 0-4 content into a new Story/Chapter/Adventure tree."

    @transaction.atomic
    def handle(self, *args, **options):
        story = self._seed_story()
        chapters = self._seed_chapters(story)
        self._seed_orientation_lessons(chapters[0])
        self._seed_adventure_levels(chapters[1], MODULE_1_LEVELS, MODULE_1_SESSION_COUNTS_DEFAULT)
        self._seed_adventure_levels(chapters[2], MODULE_2_LEVELS, MODULE_2_SESSION_COUNTS_DEFAULT)
        # Module 3 has no SESSION_COUNTS constant in the source - every tier
        # sets its own required_successful_attempts explicitly. The fallback
        # dict below is never actually used (Python still evaluates
        # dict[key] eagerly as the .get() default arg, so it must contain
        # every difficulty key even though none of them are consulted).
        self._seed_adventure_levels(
            chapters[3], MODULE_3_LEVELS, {"easy": 0, "medium": 0, "hard": 0}
        )
        # Module 4 has no SESSION_COUNTS constant either - same reasoning as
        # Module 3's fallback dict above.
        self._seed_adventure_levels(
            chapters[4], MODULE_4_LEVELS, {"easy": 0, "medium": 0, "hard": 0}
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Seeded Story, Chapters, Module 0 orientation lessons, and Module 1-4 levels."
            )
        )

    def _seed_story(self) -> Story:
        story, _ = Story.objects.update_or_create(
            slug=STORY_SPEC["slug"],
            defaults={
                "title": STORY_SPEC["title"],
                "summary": STORY_SPEC["summary"],
                "price": STORY_SPEC["price"],
                "sort_order": STORY_SPEC["sort_order"],
                "is_published": STORY_SPEC["is_published"],
                "world_slug": STORY_SPEC["world_slug"],
                "difficulty": STORY_SPEC["difficulty"],
            },
        )
        return story

    def _seed_chapters(self, story: Story) -> list[Chapter]:
        chapters = []
        for spec in CHAPTER_SPECS:
            chapter, _ = Chapter.objects.update_or_create(
                slug=spec["slug"],
                defaults={
                    "story": story,
                    "number": spec["number"],
                    "title": spec["title"],
                    "description": spec["description"],
                    "is_orientation": spec["is_orientation"],
                    "is_published": True,
                    "is_playable": True,
                    "sort_order": spec["number"],
                },
            )
            chapters.append(chapter)
        return chapters

    def _seed_orientation_lessons(self, module_0_chapter: Chapter) -> None:
        for spec in ORIENTATION_LESSON_SPECS:
            ChapterOrientationLesson.objects.update_or_create(
                chapter=module_0_chapter,
                slug=spec["slug"],
                defaults={
                    "title": spec["title"],
                    "subtitle": spec["subtitle"],
                    "content_html": spec["content_html"].strip(),
                    "scoped_css": "",
                    "interaction_steps": spec["interaction_steps"],
                    "is_published": True,
                    "sort_order": spec["sort_order"],
                },
            )

    def _seed_adventure_levels(
        self,
        chapter: Chapter,
        level_specs: list[dict[str, Any]],
        session_counts_default: dict[str, int],
    ) -> None:
        for level_spec in level_specs:
            level, _ = AdventureLevel.objects.update_or_create(
                chapter=chapter,
                slug=level_spec["slug"],
                defaults={
                    "title": level_spec["title"],
                    "description": level_spec["description"],
                    "is_required": True,
                    "is_published": True,
                    "sort_order": level_spec["sort_order"],
                },
            )
            for difficulty, tier_spec in level_spec["tiers"].items():
                self._seed_tier(level, difficulty, tier_spec, session_counts_default)

    def _seed_tier(
        self,
        level: AdventureLevel,
        difficulty: str,
        tier_spec: dict[str, Any],
        session_counts_default: dict[str, int],
    ) -> None:
        tier, _ = AdventureLevelTier.objects.update_or_create(
            adventure_level=level,
            difficulty=difficulty,
            defaults={"is_published": True},
        )
        required_successful_attempts = tier_spec.get(
            "required_successful_attempts", session_counts_default[difficulty]
        )
        # One wave per tier: the old system tracked required *successful
        # attempts* of a single repeatable exercise (drawing a fresh variant
        # each attempt), not a sequence of distinct waves.
        wave, _ = AdventureLevelTierWave.objects.update_or_create(
            tier=tier,
            slug=f"{level.slug}-{difficulty}",
            defaults={
                "title": level.title,
                "sort_order": 0,
                "story": tier_spec["story"],
                "task": tier_spec["task"],
                "min_counted_commands": tier_spec["min_counted_commands"],
                "max_counted_commands": tier_spec["max_counted_commands"],
                "objective_checks": [],
                "required_successful_attempts": required_successful_attempts,
                "is_published": True,
            },
        )
        for case in tier_spec["cases"]:
            AdventureLevelTierWaveVariant.objects.update_or_create(
                wave=wave,
                slug=case["case_id"],
                defaults={
                    "label": case["label"],
                    "initial_state": case["initial_state"],
                    "evaluation_spec": ev(
                        case["state_requirements"],
                        required=case.get("required_commands", []),
                    ),
                    "target_state": {},
                    "solution_commands": case["solution_commands"],
                    "solution_workspace_files": case.get("solution_workspace_files", []),
                    "case_id": case["case_id"],
                    "semantic_key": case["case_id"],
                    "parameter_context": {},
                    "scenario_context": {
                        "schema_version": 3,
                        "story": tier_spec["story"],
                        "task": tier_spec["task"],
                        "details": [{"label": "", "value": case["context"]}],
                    },
                    "scaffold_policy": {},
                    "is_published": True,
                },
            )
