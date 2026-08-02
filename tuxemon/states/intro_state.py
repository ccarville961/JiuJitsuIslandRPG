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

        # Android extracts the packaged project into the current working
        # directory under files/app. Build absolute paths from that location.
        app_root = Path.cwd()

        intro_path = (
            app_root
            / "mods"
            / "tuxemon"
            / "animations"
            / "intro"
            / "intro.png"
        ).resolve()

        music_path = (
            app_root
            / "mods"
            / "tuxemon"
            / "music"
            / "JRPGCollection"
            / "ogg"
            / "JRPG_mainTheme.ogg"
        ).resolve()

        logger.info("Android app root: %s", app_root)
        logger.info("Intro image path: %s", intro_path)
        logger.info("Intro music path: %s", music_path)

        try:
            if not intro_path.is_file():
                raise FileNotFoundError(
                    f"Intro image not found: {intro_path}"
                )

            self.background = pygame.image.load(
                str(intro_path)
            ).convert()

            logger.info(
                "Loaded custom intro image: %s",
                intro_path,
            )
        except Exception:
            logger.exception(
                "Failed to load custom intro image"
            )

        try:
            if not music_path.is_file():
                raise FileNotFoundError(
                    f"Main theme not found: {music_path}"
                )

            # Load the custom file directly. This avoids a failed earlier
            # MusicPlayerState load being treated as already playing.
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            pygame.mixer.music.load(str(music_path))
            pygame.mixer.music.set_volume(0.8)
            pygame.mixer.music.play(-1)

            logger.info(
                "Playing custom main theme directly: %s",
                music_path,
            )
        except Exception:
            logger.exception(
                "Failed to play custom main theme"
            )

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
                screen_rect = surface.get_rect()

                # Keep the designed splash screen together in a central,
                # mobile-safe area. The outer edges are reserved for the
                # Android D-pad and A/B controls.
                safe_width = int(screen_rect.width * 0.68)
                safe_height = int(screen_rect.height * 0.76)

                image_width, image_height = self.background.get_size()

                scale_factor = min(
                    safe_width / image_width,
                    safe_height / image_height,
                )

                scaled_size = (
                    max(1, int(image_width * scale_factor)),
                    max(1, int(image_height * scale_factor)),
                )

                bg = pygame.transform.smoothscale(
                    self.background,
                    scaled_size,
                )

                bg_rect = bg.get_rect(
                    center=(
                        screen_rect.centerx,
                        int(screen_rect.height * 0.43),
                    )
                )

                surface.blit(bg, bg_rect)

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