from rest_framework.test import APIClient

from curriculum.models import Story
from players.services import get_or_create_player
from progress.models import CoinTransaction, Wallet
from progress.wallet import WalletService
from shop.catalog import KIND_COMPANION, KIND_STORY
from shop.models import Entitlement, PlayerLoadout


def make_user(django_user_model, username: str = "shop-integrity"):
    return django_user_model.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="pass12345",
    )


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def create_story(slug="arcane-spire", *, price=0):
    return Story.objects.create(
        slug=slug,
        title="Arcane Spire" if slug == "arcane-spire" else slug.replace("-", " ").title(),
        price=price,
        world_slug=slug,
        is_published=True,
    )


def test_unknown_companion_purchase_is_rejected(db, django_user_model):
    user = make_user(django_user_model, "unknown-companion")
    client = authenticated_client(user)

    response = client.post(
        "/api/shop/catalog/purchase/",
        {"kind": KIND_COMPANION, "slug": "ghost"},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["slug"] == "Unknown companion 'ghost'."


def test_unknown_companion_equip_is_rejected(db, django_user_model):
    user = make_user(django_user_model, "unknown-companion-equip")
    client = authenticated_client(user)

    response = client.post(
        "/api/player/loadout/companion/",
        {"kind": KIND_COMPANION, "slug": "ghost"},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["slug"] == "Unknown companion 'ghost'."


def test_unowned_companion_equip_is_rejected(db, django_user_model):
    user = make_user(django_user_model, "unowned-companion")
    client = authenticated_client(user)

    response = client.post(
        "/api/player/loadout/companion/",
        {"kind": KIND_COMPANION, "slug": "blue"},
        format="json",
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "You do not own this shop item."
    assert not PlayerLoadout.objects.filter(player=get_or_create_player(user)).exists()


def test_story_equip_is_rejected_even_when_owned(db, django_user_model):
    story = create_story("premium-story", price=250)
    user = make_user(django_user_model, "story-equip")
    player = get_or_create_player(user)
    Entitlement.objects.create(player=player, kind=KIND_STORY, slug=story.slug)
    client = authenticated_client(user)

    response = client.post(
        "/api/player/loadout/companion/",
        {"kind": KIND_STORY, "slug": story.slug},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["kind"] == "Stories are selected by entering the story, not equipped."


def test_default_story_purchase_is_free_and_idempotent(db, django_user_model):
    create_story("git-it-legacy")
    user = make_user(django_user_model, "default-story-free")
    player = get_or_create_player(user)
    WalletService().award(
        player=player, amount=75, reason="test_seed", award_key="test-seed:default-story"
    )
    client = authenticated_client(user)

    first = client.post(
        "/api/shop/catalog/purchase/",
        {"kind": KIND_STORY, "slug": "git-it-legacy"},
        format="json",
    )
    second = client.post(
        "/api/shop/catalog/purchase/",
        {"kind": KIND_STORY, "slug": "git-it-legacy"},
        format="json",
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert Wallet.objects.get(player=player).balance == 75
    assert not Entitlement.objects.filter(
        player=player, kind=KIND_STORY, slug="git-it-legacy"
    ).exists()
    assert not CoinTransaction.objects.filter(player=player, reason="shop_purchase").exists()


def test_insufficient_funds_do_not_create_entitlement_or_charge(db, django_user_model):
    user = make_user(django_user_model, "insufficient-funds")
    player = get_or_create_player(user)
    client = authenticated_client(user)

    response = client.post(
        "/api/shop/catalog/purchase/",
        {"kind": KIND_COMPANION, "slug": "blue"},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["balance"] == "Insufficient GitCoins."
    wallet = Wallet.objects.filter(player=player).first()
    assert wallet is None or wallet.balance == 0
    assert not Entitlement.objects.filter(player=player, kind=KIND_COMPANION, slug="blue").exists()
    assert not CoinTransaction.objects.filter(player=player, reason="shop_purchase").exists()
