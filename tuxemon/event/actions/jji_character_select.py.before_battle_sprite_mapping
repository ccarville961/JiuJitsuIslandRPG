# SPDX-License-Identifier: GPL-3.0
from __future__ import annotations

from dataclasses import dataclass
from typing import final

from tuxemon.event.eventaction import EventAction
from tuxemon.session import Session


@final
@dataclass
class JJICharacterSelectAction(EventAction):
    """
    Open the graphical JiuJitsu Island player-character selector.

    Script usage:
        jji_character_select
    """

    name = "jji_character_select"

    def start(self, session: Session) -> None:
        player = session.player

        def _confirm(index: int) -> None:
            player.appearance_manager.update_from_character_index(index)

            # Presets 0-1 are male; presets 2-3 are female.
            gender = "male" if index in (0, 1) else "female"
            player.gender = gender

            player.game_variables.set(
                "jji_character_index",
                str(index),
            )

            session.client.pop_state()

        session.client.push_state(
            "JJICharacterSelectState",
            on_confirm=_confirm,
        )

    def update(self, session: Session, dt: float) -> None:
        if (
            "JJICharacterSelectState"
            not in session.client.active_state_names
        ):
            self.stop()
