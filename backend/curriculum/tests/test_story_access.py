from django.core.management import call_command
from rest_framework.test import APIClient

from curriculum.models import Chapter, Story
from curriculum.selectors import story_locked
from players.services import get_or_create_player
from progress.wallet import WalletService
from shop.models import Entitlement


def make_user(django_user_model, username: str = "climber"):
    return django_user_model.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="pass12345",
    )


def test_default_story_is_never_locked(db, django_user_model):
    call_command("seed_curriculum")
    user = make_user(django_user_model)
    player = get_or_create_player(user)
    story = Story.objects.get(slug="git-it-legacy")

    locked, _ = story_locked(player=player, story=story)

    assert locked is False


def test_paid_story_requires_story_entitlement(db, django_user_model):
    user = make_user(django_user_model)
    player = get_or_create_player(user)
    story = Story.objects.create(
        slug="premium-story",
        title="Premium Story",
        price=250,
        world_slug="premium-story",
    )

    locked, reason = story_locked(player=player, story=story)
    assert locked is True
    assert reason == "Buy Premium Story in the Shop to unlock this story."

    Entitlement.objects.create(player=player, kind="story", slug=story.slug)
    locked, reason = story_locked(player=player, story=story)
    assert locked is False
    assert reason == ""


def test_story_list_api_reports_lock_state_and_price(db, django_user_model):
    call_command("seed_curriculum")
    Story.objects.create(
        slug="premium-story",
        title="Premium Story",
        price=250,
        world_slug="premium-story",
        is_published=True,
    )
    user = make_user(django_user_model)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/stories/")

    assert response.status_code == 200
    by_slug = {row["slug"]: row for row in response.json()}
    assert by_slug["git-it-legacy"]["locked"] is False
    assert by_slug["arcane-spire"]["locked"] is True
    assert by_slug["arcane-spire"]["price"] == 0
    assert by_slug["arcane-spire"]["world_slug"] == "arcane-spire"
    assert by_slug["premium-story"]["locked"] is True
    assert by_slug["premium-story"]["price"] == 250


def test_buying_a_story_unlocks_its_chapters(db, django_user_model):
    story = Story.objects.create(
        slug="premium-story",
        title="Premium Story",
        price=200,
        world_slug="premium-story",
        is_published=True,
    )
    chapter = Chapter.objects.create(
        story=story,
        slug="premium-basics",
        number=900001,
        title="Premium Basics",
        description="Learn in the premium story.",
        is_published=True,
    )
    user = make_user(django_user_model)
    player = get_or_create_player(user)
    WalletService().award(
        player=player, amount=200, reason="test_seed", award_key="test-seed:story"
    )
    client = APIClient()
    client.force_authenticate(user=user)

    purchase = client.post(
        "/api/shop/catalog/purchase/",
        {"kind": "story", "slug": "premium-story"},
        format="json",
    )
    chapters = client.get("/api/chapters/?story=premium-story")

    assert purchase.status_code == 201
    assert Entitlement.objects.filter(player=player, kind="story", slug=story.slug).exists()
    assert chapters.status_code == 200
    assert chapters.json()[0]["id"] == chapter.id
    assert chapters.json()[0]["locked"] is False
