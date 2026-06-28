from __future__ import annotations

from dataclasses import dataclass
from typing import final

from tuxemon.event.eventaction import EventAction
from tuxemon.session import Session


@final
@dataclass
class JjiStartAtlasStoryAction(EventAction):
    name = "jji_start_atlas_story"

    def start(self, session: Session) -> None:
        session.jji_story_battle = "atlas_prologue"
        session.jji_story_step = 0
        session.jji_prologue_ending_started = False
        self.stop()
