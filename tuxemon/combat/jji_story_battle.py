# SPDX-License-Identifier: GPL-3.0
from __future__ import annotations


def is_atlas_prologue(session) -> bool:
    return getattr(session, "jji_story_battle", None) == "atlas_prologue"


def get_step(session) -> int:
    return int(getattr(session, "jji_story_step", 0))


def set_step(session, step: int) -> None:
    session.jji_story_step = step


def player_prompt(session) -> str:
    step = get_step(session)

    if step == 0:
        return "Atlas: Wee white belt\nspastic."

    if step == 1:
        return "Player: Spaz."

    return "Atlas: Night night\ndickhead."


def player_move_name(session) -> str:
    step = get_step(session)
    if step == 0:
        return "Blast Double"
    return "Spaz"


def after_player_move_dialog(session) -> str:
    step = get_step(session)

    if step == 0:
        return "Atlas throws up\na triangle."

    if step == 1:
        return "Atlas: Haha.\nYou're shite."

    return "Atlas: Night night\ndickhead."
