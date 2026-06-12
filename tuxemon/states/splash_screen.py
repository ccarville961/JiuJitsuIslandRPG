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

        width, height = client.context.resolution
        splash_border = int(width / 20)

        logo = self.load_sprite(PYGAME_LOGO)
        logo.rect.topleft = (
            splash_border,
            height - splash_border - logo.rect.height,
        )

        cc = self.load_sprite(CREATIVE_COMMONS)
        cc.rect.topleft = (
            width - splash_border - cc.rect.width,
            height - splash_border - cc.rect.height,
        )

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

            warning_lines = [
                "18+ GAME",
                "IT'S CRUDE, RUDE",
                "AND NOT FOR VEGANS!",
            ]

            y = surface.get_height() // 2 - 125

            for line in warning_lines:
                label = self.shadow_text(
                    line,
                    fg=(255, 255, 255),
                    bg=(0, 0, 0),
                ).convert_alpha()

                scale = 2
                label = pygame.transform.scale(
                    label,
                    (
                        label.get_width() * scale,
                        label.get_height() * scale,
                    ),
                )

                label_rect = label.get_rect(
                    center=(surface.get_width() // 2, y)
                )

                surface.blit(label, label_rect)
                y += 55

            self.sprites.draw(surface)

    def fade_out(self) -> None:
        self.triggered = True
        self.parent.push_state("FadeOutTransition")