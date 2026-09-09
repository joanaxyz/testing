from adventures.models import (
    AdventureLevelTier,
    AdventureLevelTierRun,
    AdventureLevelTierWaveVariant,
)


class TierVariantSelectionService:
    """Picks a tier-wave-owned variant, rotating retries within the same tier.

    Mirrors challenges.services.variants.VariantSelectionService exactly:
    deterministic first pick (not random), novelty-preferring on retry.
    """

    def select_variant(
        self,
        *,
        player,
        tier: AdventureLevelTier,
        prior_run: AdventureLevelTierRun | None = None,
        published_variants: list[AdventureLevelTierWaveVariant] | None = None,
        tried_variant_keys: set[str] | None = None,
    ) -> AdventureLevelTierWaveVariant | None:
        variants = published_variants or self._published_variants(tier)
        if not variants:
            return None
        if prior_run is None:
            return variants[0]
        prior_key = self.variant_identity(prior_run.selected_variant)
        tried_keys = tried_variant_keys if tried_variant_keys is not None else set()
        for variant in variants:
            identity = self.variant_identity(variant)
            if identity != prior_key and identity not in tried_keys:
                return variant
        for variant in variants:
            if self.variant_identity(variant) != prior_key:
                return variant
        return variants[0]

    def changed_between(self, *, prior, current) -> bool:
        if prior is None or current is None:
            return False
        return self.variant_identity(prior) != self.variant_identity(current)

    def is_loopback_from_keys(
        self,
        *,
        variants: list[AdventureLevelTierWaveVariant],
        selected_variant,
        tried_keys: set[str],
    ) -> bool:
        if len(variants) <= 1:
            return False
        available = {self.variant_identity(variant) for variant in variants}
        return (
            len(tried_keys.intersection(available)) >= len(available)
            and self.variant_identity(selected_variant) in tried_keys
        )

    def variant_identity(self, variant) -> str:
        return variant.semantic_key or f"id:{variant.id}"

    def _published_variants(self, tier: AdventureLevelTier) -> list[AdventureLevelTierWaveVariant]:
        return list(
            AdventureLevelTierWaveVariant.objects.filter(
                wave__tier=tier, is_published=True
            ).order_by("semantic_key", "id")
        )

    def _tried_variant_keys(self, *, player, tier: AdventureLevelTier) -> set[str]:
        variant_ids = (
            AdventureLevelTierRun.objects.filter(player=player, tier=tier)
            .values_list("selected_variant_id", flat=True)
            .distinct()
        )
        return {
            self.variant_identity(variant)
            for variant in AdventureLevelTierWaveVariant.objects.filter(id__in=variant_ids)
        }
