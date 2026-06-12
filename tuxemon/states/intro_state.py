# SPDX-License-Identifier: GPL-3.0
from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import pygame
from pygame.surface import Surface

from tuxemon.locale.locale import T
from tuxemon.menu.menu import PopUpMenu
from tuxemon.platform.const.graphics import BLACK_COLOR, WHITE_COLOR

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.platform.events import PlayerInput

logger = logging.getLogger(__name__)


class IntroState(PopUpMenu[Callable[[], None]]):
    """The state responsible for the splash screen."""

    name: ClassVar[str] = "IntroState"

    def __init__(self, client: BaseClient, **kwargs: Any) -> None:
        super().__init__(client=client, **kwargs)

        self.triggered = False
        self.background = None

        try:
            intro_path = Path("mods/tuxemon/animations/intro/intro.png")
            self.background = pygame.image.load(str(intro_path)).convert()

            self.client.current_music.play("music_main_theme")

        except Exception as e:
            logger.warning(f"Could not load intro image: {e}")

    def process_event(self, event: PlayerInput) -> PlayerInput | None:
        if event.pressed and not self.triggered:
            self.triggered = True
            self.client.replace_state("StartState")
        return None

    def update(self, dt: float) -> None:
        super().update(dt)

    def draw(self, surface: Surface) -> None:
        if not self.triggered:
            surface.fill(BLACK_COLOR)

            if self.background:
                bg = pygame.transform.scale(
                    self.background,
                    surface.get_size()
                )
                surface.blit(bg, (0, 0))

            ticks = pygame.time.get_ticks()
            alpha = 190 if (ticks % 1000) < 500 else 255

            # Create the text using the game's existing font
            label = self.shadow_text(
                T.translate("menu_intro"),
                fg=WHITE_COLOR,
                bg=BLACK_COLOR,
            ).convert_alpha()

            label.set_alpha(alpha)

            # Scale text up while keeping original font style
            scale = 2
            label = pygame.transform.scale(
                label,
                (
                    label.get_width() * scale,
                    label.get_height() * scale,
                )
            )

            rect = surface.get_rect()
            label_rect = label.get_rect(
                center=(rect.centerx, rect.height - 50)
            )

            # Create a thick black outline
            shadow = label.copy()
            shadow.fill(
                (0, 0, 0, alpha),
                special_flags=pygame.BLEND_RGBA_MULT,
            )

            # Draw outline around the text
            for dx, dy in [
                (-4, 0), (4, 0),
                (0, -4), (0, 4),
                (-3, -3), (3, -3),
                (-3, 3), (3, 3),
            ]:
                surface.blit(shadow, label_rect.move(dx, dy))

            # Draw white text on top
            surface.blit(label, label_rect)