# SPDX-License-Identifier: GPL-3.0
"""
Selectable player-character appearances for JiuJitsu Island RPG.

The two main arrays are index-aligned:

    BATTLE_SPRITES[0] belongs to NPC_SPRITES[0]
    BATTLE_SPRITES[1] belongs to NPC_SPRITES[1]

Never add an item to only one array.
"""

from __future__ import annotations


# Battle sheets located in:
# mods/tuxemon/gfx/sprites/player/<slug>.png
BATTLE_SPRITES: tuple[str, ...] = (
    "adventurer",
    "adventurerblack",
    "heroine",
    "heroineblack",
)


# Overworld sprite sheets located in:
# mods/tuxemon/gfx/sprites/<slug>.png
NPC_SPRITES: tuple[str, ...] = (
    "adventurer",
    "adventurerblack",
    "heroine",
    "brownheroine_brown",
)


# Optional information displayed by the visual selector.
# These arrays must remain in the same order as the two sprite arrays.
FIGHTER_NAMES: tuple[str, ...] = (
    "Competitor One",
    "Competitor Two",
    "Competitor Three",
    "Competitor Four",
)

FIGHTER_DESCRIPTIONS: tuple[str, ...] = (
    "A balanced competitor ready to begin their journey.",
    "A composed fighter with a strong pressure game.",
    "A technical competitor who stays calm under pressure.",
    "An athletic grappler prepared for any challenge.",
)


def validate_character_presets() -> None:
    """
    Ensure every selectable character has a complete set of data.

    This deliberately fails during startup if one array is edited without
    updating the others.
    """

    lengths = {
        "BATTLE_SPRITES": len(BATTLE_SPRITES),
        "NPC_SPRITES": len(NPC_SPRITES),
        "FIGHTER_NAMES": len(FIGHTER_NAMES),
        "FIGHTER_DESCRIPTIONS": len(FIGHTER_DESCRIPTIONS),
    }

    if len(set(lengths.values())) != 1:
        details = ", ".join(
            f"{name}={length}" for name, length in lengths.items()
        )
        raise ValueError(
            "JJI character preset arrays must have equal lengths: "
            f"{details}"
        )

    if not BATTLE_SPRITES:
        raise ValueError("At least one JJI character preset is required.")


def get_character_preset(index: int) -> tuple[str, str]:
    """
    Return the battle-sheet slug and overworld-sprite slug for an index.
    """

    validate_character_presets()

    if index < 0 or index >= len(BATTLE_SPRITES):
        raise IndexError(
            f"Character preset index {index} is outside the valid range "
            f"0-{len(BATTLE_SPRITES) - 1}."
        )

    return BATTLE_SPRITES[index], NPC_SPRITES[index]


validate_character_presets()
