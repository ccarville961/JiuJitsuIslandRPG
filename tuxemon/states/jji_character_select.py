# SPDX-License-Identifier: GPL-3.0
from __future__ import annotations

from pathlib import Path

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar

import pygame

from pygame_menu.locals import ALIGN_CENTER, ALIGN_LEFT, ALIGN_RIGHT
from pygame_menu.widgets.selection.highlight import HighlightSelection

from tuxemon.entity.sheet import CombatSheet
from tuxemon.graphics import scale_surface
from tuxemon.jji_character_presets import (
    BATTLE_SPRITES,
    FIGHTER_DESCRIPTIONS,
    FIGHTER_NAMES,
    PREVIEW_SPRITES,
)
from tuxemon.menu.menu import PygameMenuState
from tuxemon.platform.const.graphics import BG_START_SCREEN

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient


class JJICharacterSelectState(PygameMenuState):
    """Graphical player-character selection screen."""

    name: ClassVar[str] = "JJICharacterSelectState"

    def __init__(
        self,
        client: BaseClient,
        on_confirm: Callable[[int], None],
        **kwargs: Any,
    ) -> None:
        width, height = client.context.resolution

        super().__init__(
            client=client,
            width=width,
            height=height,
            **kwargs,
        )

        theme = self._setup_theme(BG_START_SCREEN)

        theme.widget_font_color = (255, 255, 255)
        theme.widget_font_shadow = True
        theme.widget_font_shadow_color = (0, 0, 0)
        theme.widget_font_shadow_offset = 1
        theme.widget_alignment = ALIGN_CENTER

        self._menu_config["theme"] = theme

        self.on_confirm = on_confirm
        self.index = 0

        self._build_menu()

    def _build_menu(
        self,
        selected_widget: str = "confirm_character",
    ) -> None:
        self.menu.clear()

        self.menu.add.label(
            title="Choose Your Competitor",
            font_size=self.font_type.big,
            font_color=(255, 255, 255),
            align=ALIGN_CENTER,
            padding=(4, 12),
        )

        preview_sprite = PREVIEW_SPRITES[self.index]

        # Load the cleaned 64x88 front-facing selector preview.
        preview_path = (
            Path.cwd()
            / "mods"
            / "tuxemon"
            / "gfx"
            / "sprites"
            / "character_select"
            / f"{preview_sprite}.png"
        ).resolve()

        if not preview_path.is_file():
            raise FileNotFoundError(
                f"Character preview sprite was not found: {preview_path}"
            )

        front_surface = pygame.image.load(
            str(preview_path)
        ).convert_alpha()

        # Remove transparent space surrounding the character so the
        # competitor name sits directly below the visible sprite.
        visible_bounds = front_surface.get_bounding_rect(min_alpha=1)

        if visible_bounds.width > 0 and visible_bounds.height > 0:
            front_surface = front_surface.subsurface(
                visible_bounds
            ).copy()

        # Reduced from 1.5 so all controls fit on screen.
        surface = scale_surface(
            front_surface,
            self.factor * 1.15,
        )

        image = self._create_image_from_surface(surface)

        self.menu.add.image(
            image,
            align=ALIGN_CENTER,
            margin=(0, 0),
        )

        self.menu.add.label(
            title=FIGHTER_NAMES[self.index],
            font_size=self.font_type.medium,
            font_color=(255, 255, 255),
            align=ALIGN_CENTER,
            padding=(0, 10),
        )

        self.menu.add.label(
            title="Press Enter to confirm",
            font_size=self.font_type.small,
            font_color=(255, 255, 255),
            align=ALIGN_CENTER,
            padding=(2, 8),
        )

        # Keep all character-selection actions on one mobile-friendly row.
        screen_width, _screen_height = self.client.context.resolution
        action_row = self.menu.add.frame_h(
            width=int(screen_width * 0.48),
            height=max(44, int(self.font_type.small * 2.4)),
            frame_id="character_action_row",
        )
        action_row.relax(True)

        previous_button = self.menu.add.button(
            title="< Previous  ",
            action=self.previous,
            button_id="previous_character",
            font_size=self.font_type.small,
            font_color=(255, 255, 255),
            selection_effect=HighlightSelection(),
            padding=(2, 8),
        )

        confirm_button = self.menu.add.button(
            title="Confirm",
            action=self.confirm,
            button_id="confirm_character",
            font_size=self.font_type.small,
            font_color=(255, 255, 255),
            selection_effect=HighlightSelection(),
            padding=(2, 8),
        )

        next_button = self.menu.add.button(
            title="Next >",
            action=self.next,
            button_id="next_character",
            font_size=self.font_type.small,
            font_color=(255, 255, 255),
            selection_effect=HighlightSelection(),
            padding=(2, 8),
        )

        action_row.pack(previous_button, align=ALIGN_LEFT)
        action_row.pack(confirm_button, align=ALIGN_CENTER)
        action_row.pack(next_button, align=ALIGN_RIGHT)

        # Move the complete Confirm widget slightly right while preserving
        # its centred text and selection border.
        confirm_button.translate(8, 0)

        # Start with the important confirmation option selected.
        self.menu.select_widget(selected_widget)

    def _rebuild_menu(self, selected_widget: str) -> None:
        self._build_menu(selected_widget)

    def previous(self) -> None:
        self.index = (self.index - 1) % len(PREVIEW_SPRITES)
        self._rebuild_menu("previous_character")

    def next(self) -> None:
        self.index = (self.index + 1) % len(PREVIEW_SPRITES)
        self._rebuild_menu("next_character")

    def confirm(self) -> None:
        self.on_confirm(self.index)
