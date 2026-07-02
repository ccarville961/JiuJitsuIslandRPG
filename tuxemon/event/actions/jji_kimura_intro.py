from __future__ import annotations

from dataclasses import dataclass
from typing import final

from tuxemon.event.eventaction import EventAction
from tuxemon.session import Session


@final
@dataclass
class JJIKimuraIntroAction(EventAction):
    name = "jji_kimura_intro"

    def start(self, session: Session) -> None:
        engine = session.client.event_engine

        engine.execute_action("lock_controls", [])
        engine.execute_action("translated_dialog", ["okaythen"])
        engine.execute_action("translated_dialog", ["okaythen2"])
        engine.execute_action("set_variable", ["jji_kimura:intro_complete"])
        engine.execute_action("unlock_controls", [])
        engine.execute_action(
            "transition_teleport",
            ["player", "player_house_bedroom.tmx", "4", "4", "1", "0:0:0"],
        )

        self.stop()
