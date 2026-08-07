# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar

from pygame_menu.menu import Menu

from tuxemon.menu.menu import PygameMenuState
from tuxemon.menu.transitions import SlideRightWorldViewport
from tuxemon.platform.const import buttons
from tuxemon.platform.const.graphics import DIMGRAY_COLOR
from tuxemon.platform.events import PlayerInput
from tuxemon.states.monster_menu import MonsterMenuHandler

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.entity.npc import NPC
    from tuxemon.world.manager import MenuItem, WorldMenuManager

logger = logging.getLogger(__name__)


WorldMenuGameObj = Callable[[], object]


def add_menu_items_to_pygame_menu(
    menu: Menu, items: list[MenuItem], resolution: tuple[int, int]
) -> None:
    """Helper function to add items to a pygame_menu.Menu instance."""
    menu.clear()

    for item in items:
        label = item.label
        callback = item.callback
        if item.enabled:
            menu.add.button(label, callback)
        else:
            menu.add.label(
                label,
                font_color=DIMGRAY_COLOR,
            )

    width, height = resolution
    widgets_size = menu.get_size(widget=True)
    b_width, b_height = menu.get_scrollarea().get_border_size()
    menu.resize(
        widgets_size[0],
        height - 2 * b_height,
        position=(width + b_width, b_height, False),
    )


class WorldMenuState(PygameMenuState):
    """Menu for the world state."""

    name: ClassVar[str] = "WorldMenuState"

    def __init__(
        self,
        client: BaseClient,
        menu_manager: WorldMenuManager,
        character: NPC,
        **kwargs: Any,
    ) -> None:
        """Initialize menu state and build menu separately."""
        self.char = character
        width, height = client.context.resolution

        super().__init__(
            client=client, height=height, transition=SlideRightWorldViewport(), **kwargs
        )

        self.menu_manager = menu_manager
        self.menu_manager.set_menu_renderer(self)
        self.update_menu_from_manager()
        self.handler = MonsterMenuHandler(self.client, self.char.party)

    def update_menu_from_manager(self) -> None:
        """Refreshes the menu display using items provided by the manager."""
        display = self.menu_manager.build_current_menu_items(self.char)
        resolution = self.client.context.resolution
        add_menu_items_to_pygame_menu(self.menu, display, resolution)

        # Establish the FINAL menu position before its slide animation starts.
        # This prevents the menu jumping vertically when the animation ends.
        current_menu = self.menu.get_current()

        physical_rect = self.client.context.rect
        logical_w, logical_h = self.client.context.resolution

        world_left = physical_rect.centerx - logical_w // 2
        world_top = physical_rect.centery - logical_h // 2
        world_right = world_left + logical_w

        menu_width = current_menu.get_width(border=True)

        # Fine tuning for the bordered Android world viewport.
        # Positive X moves right.
        # Positive Y moves down.
        WORLD_MENU_X_NUDGE = 16
        WORLD_MENU_Y_NUDGE = 11

        final_x = (
            world_right
            - menu_width
            + WORLD_MENU_X_NUDGE
        )
        final_y = world_top + WORLD_MENU_Y_NUDGE

        current_menu.translate(0, 0)
        current_menu.set_absolute_position(
            final_x,
            final_y,
        )

    def open_monster_menu(self) -> None:
        self.handler.open_monster_menu()

    def process_event(self, event: PlayerInput) -> PlayerInput | None:
        if (
            event.button in (buttons.START, buttons.B, buttons.BACK)
            and event.pressed
        ):
            self.client.pop_state()
            return None
        return super().process_event(event)
