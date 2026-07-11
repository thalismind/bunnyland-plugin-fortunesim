"""Declarative charm and locale-omen generation enrichment."""

from bunnyland.core.generation import GenerationDelta, GenerationRequest

from .components import AUSPICIOUS, FOREBODING, CharmComponent, OmenComponent

CURSED_TERMS = (
    "cursed",
    "hexed",
    "jinxed",
    "ill-omened",
    "haunted trinket",
    "broken mirror",
    "malefic",
)
LUCKY_CHARM_TERMS = (
    "charm",
    "talisman",
    "amulet",
    "clover",
    "rabbit's foot",
    "rabbits foot",
    "horseshoe",
    "wishbone",
    "lucky",
    "four-leaf",
)
OMINOUS_TERMS = (
    "ominous",
    "haunted",
    "cursed",
    "graveyard",
    "crypt",
    "tomb",
    "forsaken",
    "eerie",
    "dreadful",
    "gloomy",
    "abandoned",
    "sinister",
)
AUSPICIOUS_TERMS = (
    "blessed",
    "hallowed",
    "sacred",
    "shrine",
    "sunlit",
    "serene",
    "auspicious",
    "hopeful",
)


def _text(request):
    return " ".join(
        (request.source_key, request.entity_kind, request.description, *request.tags)
    ).casefold()


class FortuneGenerationEnricher:
    capabilities: tuple[str, ...] = ()

    def enrich(self, request: GenerationRequest) -> GenerationDelta:
        existing = tuple(request.context.get("base_components", ()))
        text = _text(request)
        if request.entity_kind == "room":
            if any(isinstance(item, OmenComponent) for item in existing):
                return GenerationDelta()
            if any(term in text for term in OMINOUS_TERMS):
                return GenerationDelta(
                    components=(
                        OmenComponent(
                            kind=FOREBODING,
                            omen="ominous-locale",
                            text="An oppressive dread hangs over this place.",
                            source="worldgen",
                        ),
                    )
                )
            if any(term in text for term in AUSPICIOUS_TERMS):
                return GenerationDelta(
                    components=(
                        OmenComponent(
                            kind=AUSPICIOUS,
                            omen="blessed-locale",
                            text="A gentle, blessed calm suffuses this place.",
                            source="worldgen",
                        ),
                    )
                )
            return GenerationDelta()
        if any(isinstance(item, CharmComponent) for item in existing):
            return GenerationDelta()
        if any(term in text for term in CURSED_TERMS):
            return GenerationDelta(components=(CharmComponent(luck=-1.5, label="trinket"),))
        if any(term in text for term in LUCKY_CHARM_TERMS):
            return GenerationDelta(components=(CharmComponent(luck=1.0, label="charm"),))
        return GenerationDelta()


__all__ = [
    "AUSPICIOUS_TERMS",
    "CURSED_TERMS",
    "FortuneGenerationEnricher",
    "LUCKY_CHARM_TERMS",
    "OMINOUS_TERMS",
]
