# SPDX-License-Identifier: GPL-3.0
from __future__ import annotations

from pygame.rect import Rect

COMBAT_NATIVE_WIDTH = 256
COMBAT_NATIVE_HEIGHT = 144
BATTLE_NATIVE_HEIGHT = 108
DIALOG_NATIVE_HEIGHT = 36

# Original Tuxemon combat layout:
# 154 px message area + 102 px command menu = 256 px total.
COMBAT_MESSAGE_NATIVE_WIDTH = 154
COMBAT_MENU_NATIVE_WIDTH = 102


def get_combat_viewport(context: object) -> Rect:
    """
    Return a centred 256x144 combat viewport using the game's current scale.

    Android may expose a much wider physical surface than the logical game
    presentation. Combat should remain inside the centred game-sized area.
    """
    screen_rect = context.rect.copy()
    scaling = context.scaling

    desired_width = int(scaling.scale_int(COMBAT_NATIVE_WIDTH))
    desired_height = int(scaling.scale_int(COMBAT_NATIVE_HEIGHT))

    fit_scale = min(
        desired_width / COMBAT_NATIVE_WIDTH,
        desired_height / COMBAT_NATIVE_HEIGHT,
        screen_rect.width / COMBAT_NATIVE_WIDTH,
        screen_rect.height / COMBAT_NATIVE_HEIGHT,
    )

    viewport_width = max(1, int(round(COMBAT_NATIVE_WIDTH * fit_scale)))
    viewport_height = max(1, int(round(COMBAT_NATIVE_HEIGHT * fit_scale)))

    viewport = Rect(0, 0, viewport_width, viewport_height)
    viewport.center = screen_rect.center
    return viewport


def get_combat_battle_rect(context: object) -> Rect:
    """Return the upper 256x108 battle area within the combat viewport."""
    viewport = get_combat_viewport(context)
    battle_height = int(
        round(viewport.height * BATTLE_NATIVE_HEIGHT / COMBAT_NATIVE_HEIGHT)
    )

    battle_rect = viewport.copy()
    battle_rect.height = battle_height
    battle_rect.top = viewport.top
    return battle_rect


def get_combat_dialog_rect(context: object) -> Rect:
    """Return the lower 256x36 dialogue/menu area."""
    viewport = get_combat_viewport(context)
    dialog_height = int(
        round(viewport.height * DIALOG_NATIVE_HEIGHT / COMBAT_NATIVE_HEIGHT)
    )

    dialog_rect = Rect(
        viewport.left,
        viewport.bottom - dialog_height,
        viewport.width,
        dialog_height,
    )
    return dialog_rect



def get_combat_message_rect(context: object) -> Rect:
    """
    Return only the message portion of the lower combat row.

    The command menu owns the right-hand 102/256 of the row, so dialogue
    must stop before that area instead of extending underneath it.
    """
    dialog_rect = get_combat_dialog_rect(context)

    message_width = int(
        round(
            dialog_rect.width
            * COMBAT_MESSAGE_NATIVE_WIDTH
            / COMBAT_NATIVE_WIDTH
        )
    )

    return Rect(
        dialog_rect.left,
        dialog_rect.top,
        message_width,
        dialog_rect.height,
    )


def offset_combat_layouts(
    layouts: dict[object, dict[str, list[Rect]]],
    viewport: Rect,
) -> None:
    """
    Move absolute combat YAML rectangles into the centred viewport.

    hud_line1 / hud_line2 are deliberately NOT moved. Those coordinates
    are relative to the HUD surface itself, rather than the battle screen.
    """
    for npc_layout in layouts.values():
        for key, rects in npc_layout.items():
            if key.startswith("hud_line"):
                continue

            for rect in rects:
                rect.move_ip(viewport.left, viewport.top)
