# SPDX-License-Identifier: GPL-3.0
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import final

from tuxemon.db import StatType
from tuxemon.event.eventaction import EventAction
from tuxemon.monster.monster import Monster
from tuxemon.session import Session

logger = logging.getLogger(__name__)


@final
@dataclass
class CleanupDuplicateYouAction(EventAction):
    """
    Keep one permanent player fighter after the Sensei Duncan tutorial.

    If multiple monsters with slug ``you`` exist in the player's party,
    preserve the strongest one and remove the weaker duplicates.

    Script usage:
        cleanup_duplicate_you
    """

    name = "cleanup_duplicate_you"

    @staticmethod
    def strength_score(monster: Monster, party_index: int) -> tuple[int, ...]:
        """
        Rank fighters by progression and combat stats.

        The party index is the final tie-breaker, so when two copies are
        otherwise identical, the newer copy added later is preserved.
        """
        stats = tuple(
            int(monster.return_stat(stat))
            for stat in StatType
        )

        experience = int(
            getattr(
                monster,
                "experience",
                getattr(monster, "exp", 0),
            )
            or 0
        )

        return (
            int(monster.level),
            experience,
            int(monster.hp),
            *stats,
            party_index,
        )

    def start(self, session: Session) -> None:
        player = session.player

        matching = [
            (index, monster)
            for index, monster in enumerate(player.monsters)
            if monster.slug == "you"
        ]

        if len(matching) <= 1:
            logger.info(
                "Duplicate fighter cleanup skipped: player has %s copy of 'you'.",
                len(matching),
            )
            self.stop()
            return

        keep_index, permanent_fighter = max(
            matching,
            key=lambda entry: self.strength_score(entry[1], entry[0]),
        )

        logger.info(
            "Keeping permanent fighter 'you' at party index %s, level %s.",
            keep_index,
            permanent_fighter.level,
        )

        for index, monster in matching:
            if monster is permanent_fighter:
                continue

            logger.info(
                "Removing temporary prologue fighter 'you' at party index %s, "
                "level %s.",
                index,
                monster.level,
            )
            player.party.remove_monster(monster)

        self.stop()
