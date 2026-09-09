"""Shop catalog for story access and companions."""

from __future__ import annotations

KIND_STORY = "story"
KIND_COMPANION = "companion"
SHOP_KINDS = (KIND_STORY, KIND_COMPANION)

DEFAULT_STORY = "git-it-legacy"
# No companion is free anymore - every player must buy their first one.
DEFAULT_COMPANION = None

COMPANIONS: dict[str, dict] = {
    "blue": {"label": "Blue", "price": 150},
    "white": {"label": "White", "price": 150},
    "black": {"label": "Black", "price": 150},
}

DEFAULTS = {KIND_STORY: DEFAULT_STORY, KIND_COMPANION: DEFAULT_COMPANION}


def catalog(kind: str) -> dict[str, dict]:
    if kind == KIND_STORY:
        from curriculum.models import Story

        return {
            story.slug: {
                "label": story.title,
                "price": story.price,
                "world_slug": story.world_slug,
                "difficulty": story.difficulty,
                "prerequisite_story": (
                    story.prerequisite_story.slug if story.prerequisite_story_id else None
                ),
            }
            for story in Story.objects.filter(is_published=True)
            .select_related("prerequisite_story")
            .order_by("sort_order", "id")
        }
    if kind == KIND_COMPANION:
        return COMPANIONS
    return {}


def get(kind: str, slug: str) -> dict | None:
    return catalog(kind).get(slug)


def is_default(kind: str, slug: str) -> bool:
    default = DEFAULTS.get(kind)
    return default is not None and default == slug


def listings() -> list[dict]:
    out: list[dict] = []
    for kind in SHOP_KINDS:
        for slug, meta in catalog(kind).items():
            out.append(
                {
                    "kind": kind,
                    "slug": slug,
                    "label": meta["label"],
                    "price": meta["price"],
                }
            )
    return out
