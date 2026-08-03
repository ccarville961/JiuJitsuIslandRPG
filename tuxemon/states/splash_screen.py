# SPDX-License-Identifier: GPL-3.0
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar

import pygame
from pygame.surface import Surface

from tuxemon.menu.menu import PopUpMenu
from tuxemon.platform.const.graphics import (
    BLACK_COLOR,
    CREATIVE_COMMONS,
    PYGAME_LOGO,
)
from tuxemon.platform.events import PlayerInput

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.state.manager import StateManager

logger = logging.getLogger(__name__)


class SplashState(PopUpMenu[Callable[[], None]]):
    """The state responsible for the splash screen."""

    name: ClassVar[str] = "SplashState"
    default_duration = 3

    def __init__(
        self, client: BaseClient, parent: StateManager, **kwargs: Any
    ) -> None:
        super().__init__(client=client, **kwargs)

        self.parent = parent
        self.task(self.fade_out, interval=self.default_duration)
        self.triggered = False

        # Store the splash sprites. Their final positions are calculated
        # from the real Android display surface inside draw().
        self.logo = self.load_sprite(PYGAME_LOGO)
        self.cc = self.load_sprite(CREATIVE_COMMONS)

        self.client.sound_manager.play("sound_ding")

    def resume(self) -> None:
        if self.triggered:
            self.parent.pop_state()

    def process_event(self, event: PlayerInput) -> PlayerInput | None:
        if event.pressed and not self.triggered:
            self.fade_out()
        return None

    def draw(self, surface: Surface) -> None:
        if not self.triggered:
            surface.fill(BLACK_COLOR)

            screen_rect = surface.get_rect()
            width = screen_rect.width
            height = screen_rect.height

            # Leave the lower corners free for Android touch controls.
            horizontal_margin = max(18, int(width * 0.035))
            top_margin = max(14, int(height * 0.05))

            # Position both logos from the real display dimensions.
            self.logo.rect.topleft = (
                horizontal_margin,
                top_margin,
            )

            self.cc.rect.topright = (
                width - horizontal_margin,
                top_margin,
            )

            warning_lines = [
                "18+ GAME",
                "IT'S CRUDE, RUDE",
                "AND NOT FOR VEGANS!",
            ]

            # Keep the warning centred between the upper logos and the
            # mobile control area.
            line_gap = max(30, int(height * 0.095))
            warning_center_y = int(height * 0.46)
            total_height = line_gap * (len(warning_lines) - 1)
            y = warning_center_y - total_height // 2

            for line in warning_lines:
                label = self.shadow_text(
                    line,
                    fg=(255, 255, 255),
                    bg=(0, 0, 0),
                ).convert_alpha()

                # Scale relative to the actual landscape height rather than
                # using a fixed desktop multiplier.
                scale = max(1.0, min(2.0, height / 360.0))

                label = pygame.transform.smoothscale(
                    label,
                    (
                        max(1, int(label.get_width() * scale)),
                        max(1, int(label.get_height() * scale)),
                    ),
                )

                label_rect = label.get_rect(
                    center=(screen_rect.centerx, y)
                )

                surface.blit(label, label_rect)
                y += line_gap

            self.sprites.draw(surface)

    def fade_out(self) -> None:
        self.triggered = True
        self.parent.push_state("FadeOutTransition")