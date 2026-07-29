# SPDX-License-Identifier: GPL-3.0
"""
Selectable player-character appearances for JiuJitsu Island RPG.

Each array is index-aligned. Every index represents one selectable
competitor:

    PREVIEW_SPRITES[index]
    BATTLE_SPRITES[index]
    NPC_SPRITES[index]
    FIGHTER_NAMES[index]
    FIGHTER_DESCRIPTIONS[index]

PREVIEW_SPRITES controls only the image shown on the character-selection
screen.

BATTLE_SPRITES and NPC_SPRITES control the character used after the
selection is confirmed.
"""

from __future__ import annotations


# Character-selection artwork located in:
# mods/tuxemon/gfx/sprites/battle/<slug>.png
#
# These are 128x88 sheets containing two 64x88 frames.
PREVIEW_SPRITES: tuple[str, ...] = (
    "blackgi-whitebelt",
    "teen-whitebelt",
    "black-wrestler",
    "bluegi_whitebelt",
    "fat-wrestler",
    "blonde-wrestler",
    "naked_grappler",
)


# Existing playable combat sheets located in:
# mods/tuxemon/gfx/sprites/player/<slug>.png
#
# These remain valid 128x64 player sheets. Some are temporarily reused
# until dedicated playable sheets are created for all seven competitors.
BATTLE_SPRITES: tuple[str, ...] = (
    "blackgi-whitebelt",
    "teen-whitebelt",
    "black-wrestler",
    "bluegi_whitebelt",
    "fat-wrestler",
    "blonde-wrestler",
    "naked_grappler",
)


# Existing overworld sheets located in:
# mods/tuxemon/gfx/sprites/<slug>.png
#
# These are also temporarily reused until matching overworld walking
# sheets are available for all seven competitors.
NPC_SPRITES: tuple[str, ...] = (
    "coach_carville",
    "teen_whitebelt_npc",
    "black_wrestler",
    "bluegi_whitebelt_npc",
    "black_wrestler",
    "blonde_wrestler_npc",
    "naked",
)


FIGHTER_NAMES: tuple[str, ...] = (
    "Black Gi White Belt",
    "Teen White Belt",
    "Black Wrestler",
    "Blue Gi White Belt",
    "Fat Wrestler",
    "Blonde Wrestler",
    "Naked Grappler",
)


# Descriptions are retained for compatibility, even though the selector
# currently does not display them.
FIGHTER_DESCRIPTIONS: tuple[str, ...] = (
    "",
    "",
    "",
    "",
    "",
    "",
    "",
)


def validate_character_presets() -> None:
    """Ensure every selectable character has a complete aligned preset."""

    lengths = {
        "PREVIEW_SPRITES": len(PREVIEW_SPRITES),
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

    if not PREVIEW_SPRITES:
        raise ValueError("At least one JJI character preset is required.")


def get_character_preset(index: int) -> tuple[str, str]:
    """
    Return the playable combat-sheet slug and overworld-sprite slug.
    """

    validate_character_presets()

    if index < 0 or index >= len(BATTLE_SPRITES):
        raise IndexError(
            f"Character preset index {index} is outside the valid range "
            f"0-{len(BATTLE_SPRITES) - 1}."
        )

    return BATTLE_SPRITES[index], NPC_SPRITES[index]


validate_character_presets()
