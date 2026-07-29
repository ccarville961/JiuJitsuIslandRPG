# SPDX-License-Identifier: GPL-3.0
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import final

from tuxemon.combat.combat_context import (
    BattleMode,
    CombatContext,
    CombatType,
)
from tuxemon.combat.utils import check_battle_legal
from tuxemon.database.rules import config_monster
from tuxemon.database.runtime import db
from tuxemon.db import MonsterModel, NpcModel
from tuxemon.event.eventaction import EventAction
from tuxemon.monster.monster import Monster
from tuxemon.platform.const.sizes import PARTY_LIMIT
from tuxemon.session import Session

logger = logging.getLogger(__name__)


@final
@dataclass
class OpenMatBattleAction(EventAction):
    """
    Charge an entry fee and begin a random Open Mat trainer battle.

    Usage:
        open_mat_battle party_size,min_level,max_level,entry_fee,min_prize,max_prize

    Example:
        open_mat_battle 1,8,15,100,100,300
    """

    name = "open_mat_battle"

    nr_txmns: int
    min_level: int
    max_level: int
    entry_fee: int
    min_prize: int
    max_prize: int

    opponent_slug: str | None = field(default=None, init=False)
    battle_started: bool = field(default=False, init=False)
    battle_finished: bool = field(default=False, init=False)

    def start(self, session: Session) -> None:
        self._validate_parameters()

        player = session.player
        money_manager = player.money_controller.money_manager

        if money_manager.get_money() < self.entry_fee:
            self._dialog(session, "jji_open_mat_no_money")
            self.stop()
            return

        money_manager.remove_money(self.entry_fee)

        MonsterModel.load_cache(db)
        monster_cache = MonsterModel.get_cache()

        NpcModel.load_cache(db)
        npc_cache = NpcModel.get_cache()

        excluded_npcs = {
            "jji_koth_referee_center",
            "jji_hill_spectator_respect",
            "jji_hill_spectator_strategy",
            "jji_hill_spectator_ribs",
            "jji_hill_spectator_real_chance",
            "jji_hill_spectator_massive_win",
            "jji_hill_spectator_atomic_drop",
        }

        available_npcs = [
            npc
            for npc in npc_cache.values()
            if not npc.monsters
            and npc.slug not in excluded_npcs
        ]

        if not available_npcs:
            money_manager.add_money(self.entry_fee)
            logger.error("No valid random Open Mat NPCs were available.")
            self.stop()
            return

        available_monsters = list(monster_cache.values())

        if len(available_monsters) < self.nr_txmns:
            money_manager.add_money(self.entry_fee)
            logger.error("Not enough monsters for the Open Mat battle.")
            self.stop()
            return

        opponent_model = random.choice(available_npcs)
        self.opponent_slug = opponent_model.slug

        session.client.event_engine.execute_action(
            "create_npc",
            [self.opponent_slug, 0, 0],
            True,
        )

        opponent = session.client.get_npc(self.opponent_slug)

        if opponent is None:
            money_manager.add_money(self.entry_fee)
            logger.error(
                "Failed to create Open Mat opponent '%s'.",
                self.opponent_slug,
            )
            self.stop()
            return

        selected_monsters = random.sample(
            available_monsters,
            self.nr_txmns,
        )

        for monster_model in selected_monsters:
            level = random.randint(
                self.min_level,
                self.max_level,
            )

            monster = Monster.spawn_base(
                monster_model.slug,
                level,
            )

            # Preserve ordinary battle XP.
            monster.set_experience_modifier(level)

            # Open Mat prize money is awarded separately after victory.
            monster.money_modifier = 0.0

            opponent.party.insert_monster_to_party(
                monster,
                len(opponent.monsters),
            )

        if not (
            check_battle_legal(player)
            and check_battle_legal(opponent)
        ):
            money_manager.add_money(self.entry_fee)
            session.client.npc_manager.remove_npc(self.opponent_slug)
            self.opponent_slug = None
            logger.warning("Open Mat battle failed legality checks.")
            self.stop()
            return

        environment = session.client.environment_manager
        active_environment = environment.get_active_environment()

        if active_environment is None:
            money_manager.add_money(self.entry_fee)
            session.client.npc_manager.remove_npc(self.opponent_slug)
            self.opponent_slug = None
            logger.error("No battle environment is active.")
            self.stop()
            return
        context = CombatContext(
            session=session,
            teams=[player, opponent],
            combat_type=CombatType.TRAINER,
            battle_mode=BattleMode.SINGLE,
        )

        self.battle_started = True

        session.client.push_state(
            "CombatState",
            context=context,
        )

        battle_music = active_environment.get_battle_music().battle

        if battle_music.music:
            session.client.current_music.play(battle_music.music)

    def update(self, session: Session, dt: float) -> None:
        if not self.battle_started or self.battle_finished:
            return

        client = session.client

        combat_active = (
            "CombatState" in client.active_state_names
            or client.has_queued_state("CombatState")
        )

        if combat_active:
            return

        self.battle_finished = True
        self._resolve_result(session)
        self.stop()

    def _resolve_result(self, session: Session) -> None:
        if self.opponent_slug is None:
            return

        player = session.player

        outcome = player.battle_handler.get_last_battle_outcome(
            self.opponent_slug
        )

        outcome_value = getattr(outcome, "value", outcome)

        if outcome_value == "won":
            prize = random.randint(
                self.min_prize,
                self.max_prize,
            )

            player.money_controller.money_manager.add_money(prize)

            session.client.event_engine.execute_action(
                "translated_dialog",
                ["jji_open_mat_victory", {"prize": prize}],
                True,
            )

            logger.info(
                "Open Mat victory: awarded $%s.",
                prize,
            )

        elif outcome_value == "lost":
            self._dialog(session, "jji_open_mat_defeat")

        else:
            self._dialog(session, "jji_open_mat_draw")

        session.client.npc_manager.remove_npc(
            self.opponent_slug
        )

        self.opponent_slug = None

    def _dialog(
        self,
        session: Session,
        translation_slug: str,
    ) -> None:
        session.client.event_engine.execute_action(
            "translated_dialog",
            [translation_slug],
            True,
        )

    def _validate_parameters(self) -> None:
        if not 1 <= self.nr_txmns <= PARTY_LIMIT:
            raise ValueError(
                f"Party size must be between 1 and {PARTY_LIMIT}."
            )

        if self.min_level < 1:
            raise ValueError("Minimum level must be at least 1.")

        if self.max_level < self.min_level:
            raise ValueError(
                "Maximum level cannot be below minimum level."
            )

        if self.max_level > config_monster.level_range[1]:
            raise ValueError(
                f"Maximum level cannot exceed "
                f"{config_monster.level_range[1]}."
            )

        if self.entry_fee < 0:
            raise ValueError("Entry fee cannot be negative.")

        if self.min_prize < 0:
            raise ValueError("Minimum prize cannot be negative.")

        if self.max_prize < self.min_prize:
            raise ValueError(
                "Maximum prize cannot be below minimum prize."
            )

    def cleanup(self, session: Session) -> None:
        # Safety cleanup if the action is interrupted before result handling.
        if (
            self.opponent_slug
            and not self.battle_started
        ):
            session.client.npc_manager.remove_npc(
                self.opponent_slug
            )
            self.opponent_slug = None
