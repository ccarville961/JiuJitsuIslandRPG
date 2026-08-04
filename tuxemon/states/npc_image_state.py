# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from pygame.surface import Surface
from pygame_menu.baseimage import IMAGE_MODE_FILL
from pygame_menu.locals import ALIGN_CENTER

from tuxemon.menu.menu import PygameMenuState

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.platform.events import PlayerInput


class NpcImageState(PygameMenuState):
    # The tutorial/image screen must hide the active world map.
    transparent = False  # JJI tutorial overlay
    name: ClassVar[str] = "NpcImageState"

    def process_event(self, event: PlayerInput) -> PlayerInput | None:
        return None

    def __init__(
        self,
        client: BaseClient,
        background: str,
        surface: Surface,
        **kwargs: Any,
    ) -> None:
        image_path = f"gfx/ui/background/{background}.png"
        width, height = client.context.resolution
        super().__init__(client=client, height=height, width=width, **kwargs)
        theme = self._setup_theme(image_path)

        # Fill the complete Android game surface with the tutorial background
        # instead of centring the native 256x144 image over the world map.
        background = getattr(theme, "background_color", None)

        if hasattr(background, "set_drawing_mode"):
            background.set_drawing_mode(IMAGE_MODE_FILL)

        self._menu_config["theme"] = theme
        surface = surface.copy()
        image = self._create_image_from_surface(surface)
        self.menu.add.image(image, align=ALIGN_CENTER)
        self.reset_theme()

    def draw(self, surface: Surface) -> None:
        """Draw an opaque tutorial scene over the complete game surface."""
        surface.fill((0, 0, 0))
        super().draw(surface)
