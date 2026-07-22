# SPDX-License-Identifier: GPL-3.0
"""Event action which starts the Jiu Jitsu Island credits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import final

from tuxemon.event.eventaction import EventAction
from tuxemon.session import Session


@final
@dataclass
class StartJjiCreditsAction(EventAction):
    """
    Start the Jiu Jitsu Island scrolling credits.

    Script usage:

        start_jji_credits
    """

    name = "start_jji_credits"

    def start(self, session: Session) -> None:
        session.client.push_state("JjiCreditsState")
        self.stop()
