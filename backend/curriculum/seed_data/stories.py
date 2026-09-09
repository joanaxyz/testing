STORIES = [
    {
        "slug": "arcane-spire",
        "title": "The Arcane Spire",
        "summary": (
            "A beginner campaign about creating reliable repositories, shaping intentional snapshots, "
            "reading history, branching safely, integrating work, recovering from mistakes, and exchanging "
            "clean history with the Guild Archive."
        ),
        "price": 0,
        "sort_order": 1,
        "is_published": True,
        "world_slug": "arcane-spire",
        "difficulty": "beginner",
        "prerequisite_story": None,
    },
    {
        "slug": "frostbound-citadel",
        "title": "Frostbound Citadel",
        "summary": (
            "An intermediate winter campaign about coordinating many contributors, shaping patch series, "
            "resolving conflicts, debugging regressions, governing remotes, and delivering auditable releases."
        ),
        "price": 350,
        "sort_order": 2,
        "is_published": True,
        "world_slug": "frostbound-citadel",
        "difficulty": "intermediate",
        "prerequisite_story": "arcane-spire",
    },
    {
        "slug": "neon-backstreets",
        "title": "Neon Backstreets",
        "summary": (
            "An advanced neon street campaign about repository forensics, large-scale workspaces, automation, "
            "trust, server operations, maintenance, migration, and Git's object machinery."
        ),
        "price": 700,
        "sort_order": 3,
        "is_published": True,
        "world_slug": "neon-backstreets",
        "difficulty": "advanced",
        "prerequisite_story": "frostbound-citadel",
    },
    {
        "slug": "git-it-legacy",
        "title": "The Runebound Turret",
        "summary": (
            "Ascend a rune-lit tower while mastering Git fundamentals across five modules, "
            "from repository setup and branching to conflict resolution and history rewriting."
        ),
        "price": 0,
        "sort_order": 0,
        "is_published": True,
        "world_slug": "arcane-spire",
        "difficulty": "beginner",
        "prerequisite_story": None,
    },
]
