from __future__ import annotations

from dataclasses import dataclass
from typing import final

from tuxemon.event.eventaction import EventAction
from tuxemon.session import Session


@final
@dataclass
class JjiClearPartyAction(EventAction):
    name = "jji_clear_party"
    npc_slug: str = "player"

    def start(self, session: Session) -> None:
        npc = session.client.get_npc(self.npc_slug)
        if npc is None:
            raise ValueError(f"NPC '{self.npc_slug}' not found")
        npc.party.clear_party()
        self.stop()
