# SPDX-License-Identifier: GPL-3.0
"""Scrolling end credits for Jiu Jitsu Island."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from pygame.font import Font
from pygame.surface import Surface

from tuxemon.platform.const.graphics import BLACK_COLOR
from tuxemon.state.state import State

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.platform.events import PlayerInput


logger = logging.getLogger(__name__)

WHITE = (255, 255, 255)
SOFT_WHITE = (220, 220, 220)
GOLD = (255, 210, 70)


@dataclass(frozen=True)
class CreditLine:
    """Configuration for one displayed credits line."""

    text: str
    font_size: int
    spacing_after: int
    colour: tuple[int, int, int] = WHITE
    bold: bool = False


class JjiCreditsState(State):
    """Black-screen credits which scroll upwards."""

    name: ClassVar[str] = "JjiCreditsState"

    transparent = False
    force_draw = True

    def __init__(
        self,
        client: BaseClient,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(client, *args, **kwargs)

        self.returning_to_home = False
        self.finished_delay = 0.0

        # Do not use client.context.scale for fonts.
        # The state is already drawn at the active screen resolution, so
        # applying scale_int here makes text several times too large.
        self.resolution_font_scale = max(
            0.8,
            min(1.35, self.rect.height / 720),
        )

        self.scroll_speed = max(
            24.0,
            min(42.0, self.rect.height / 24),
        )

        self.font_path = self._find_game_font()

        self.fonts: dict[tuple[int, bool], Font] = {}
        self.lines = self._build_credit_lines()
        self.rendered_lines = self._render_credit_lines()
        self.total_height = self._calculate_total_height()

        self.scroll_position = float(
            self.rect.height + self._scaled_spacing(50)
        )

        if self.font_path:
            logger.info(
                "Jiu Jitsu Island credits font: %s",
                self.font_path,
            )
        else:
            logger.warning(
                "No bundled game font was discovered. "
                "Using Pygame's fallback font."
            )

    def _find_game_font(self) -> str | None:
        """
        Find the font already bundled and referenced by the game.

        Referenced font files receive the highest score. Pixel and retro
        fonts are preferred over unrelated bundled fonts.
        """
        project_root = Path(__file__).resolve().parents[2]

        excluded_directories = {
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "__pycache__",
        }

        font_files: list[Path] = []

        for extension in ("*.ttf", "*.otf"):
            for path in project_root.rglob(extension):
                if any(
                    directory in excluded_directories
                    for directory in path.parts
                ):
                    continue

                font_files.append(path)

        if not font_files:
            return None

        reference_files = [
            project_root / "tuxemon/menu/menu.py",
            project_root / "tuxemon/states/start.py",
            project_root / "tuxemon/state/draw.py",
            project_root / "tuxemon/ui/draw.py",
            project_root / "tuxemon/ui/text.py",
        ]

        reference_text = ""

        for path in reference_files:
            if not path.exists():
                continue

            reference_text += path.read_text(
                encoding="utf-8",
                errors="ignore",
            ).lower()

        preferred_terms = {
            "pixel": 40,
            "tuxemon": 35,
            "pressstart": 32,
            "press_start": 32,
            "munro": 30,
            "retro": 24,
            "arcade": 20,
            "game": 12,
        }

        def score(path: Path) -> int:
            name = path.name.lower()
            stem = path.stem.lower()
            path_text = str(path).lower()

            font_score = 0

            if name in reference_text:
                font_score += 200

            if stem in reference_text:
                font_score += 100

            for term, value in preferred_terms.items():
                if term in path_text:
                    font_score += value

            if "bold" in name:
                font_score -= 3

            return font_score

        selected = max(
            font_files,
            key=lambda path: (
                score(path),
                -len(str(path)),
            ),
        )

        return str(selected)

    def _scaled_font_size(self, size: int) -> int:
        """Scale fonts for resolution, not window pixel scaling."""

        return max(
            10,
            round(size * self.resolution_font_scale),
        )

    def _scaled_spacing(self, spacing: int) -> int:
        return max(
            2,
            round(spacing * self.resolution_font_scale),
        )

    def _build_credit_lines(self) -> list[CreditLine]:
        return [
            CreditLine(
                "JIU JITSU ISLAND",
                30,
                28,
                GOLD,
                True,
            ),
            CreditLine(
                "A game by",
                14,
                8,
                SOFT_WHITE,
            ),
            CreditLine(
                "CALLUM CARVILLE",
                20,
                52,
                WHITE,
                True,
            ),

            CreditLine(
                "BUILT USING",
                18,
                18,
                GOLD,
                True,
            ),
            CreditLine(
                "Tuxemon",
                15,
                9,
            ),
            CreditLine(
                "Pygame CE",
                15,
                52,
            ),

            CreditLine(
                "SPECIAL THANKS",
                18,
                18,
                GOLD,
                True,
            ),
            CreditLine(
                "The Folks",
                17,
                14,
            ),
            CreditLine(
                "Everyone who tested",
                15,
                6,
            ),
            CreditLine(
                "Jiu Jitsu Island",
                15,
                14,
            ),
            CreditLine(
                "The Brazilian Jiu Jitsu Community",
                15,
                56,
            ),

            CreditLine(
                "THANK YOU TO OUR SPONSORS",
                18,
                20,
                GOLD,
                True,
            ),
            CreditLine(
                "RND1.MMA",
                21,
                10,
                WHITE,
                True,
            ),
            CreditLine(
                "Custom Combat Sports Apparel",
                14,
                26,
                SOFT_WHITE,
            ),
            CreditLine(
                "PADDY'S POWERFUL BOTTLES",
                19,
                60,
                WHITE,
                True,
            ),

            CreditLine(
                "CONGRATULATIONS!",
                20,
                16,
                GOLD,
                True,
            ),
            CreditLine(
                "You became the",
                15,
                12,
            ),
            CreditLine(
                "KING OF THE HILL",
                27,
                90,
                WHITE,
                True,
            ),

            CreditLine(
                "ONE FINAL LESSON...",
                19,
                110,
                GOLD,
                True,
            ),

            CreditLine(
                "JUST REMEMBER...",
                25,
                70,
                WHITE,
                True,
            ),

            CreditLine(
                "JIU JITSU",
                33,
                12,
                GOLD,
                True,
            ),
            CreditLine(
                "IS NOT REAL",
                33,
                80,
                GOLD,
                True,
            ),

            CreditLine(
                "JUST",
                36,
                7,
                WHITE,
                True,
            ),
            CreditLine(
                "STAND",
                40,
                7,
                WHITE,
                True,
            ),
            CreditLine(
                "UP",
                46,
                120,
                WHITE,
                True,
            ),

            CreditLine(
                "THANKS FOR PLAYING!",
                22,
                16,
                GOLD,
                True,
            ),
            CreditLine(
                "See you on the mats.",
                16,
                100,
                SOFT_WHITE,
            ),
        ]

    def _get_font(self, size: int, bold: bool) -> Font:
        font_size = self._scaled_font_size(size)
        key = (font_size, bold)

        if key not in self.fonts:
            font = Font(
                self.font_path,
                font_size,
            )
            font.set_bold(bold)
            self.fonts[key] = font

        return self.fonts[key]

    def _fit_text(
        self,
        text: str,
        font: Font,
        maximum_width: int,
    ) -> list[str]:
        if font.size(text)[0] <= maximum_width:
            return [text]

        words = text.split()
        fitted_lines: list[str] = []
        current_line = ""

        for word in words:
            candidate = f"{current_line} {word}".strip()

            if (
                current_line
                and font.size(candidate)[0] > maximum_width
            ):
                fitted_lines.append(current_line)
                current_line = word
            else:
                current_line = candidate

        if current_line:
            fitted_lines.append(current_line)

        return fitted_lines or [text]

    def _render_credit_lines(
        self,
    ) -> list[tuple[Surface, int]]:
        rendered: list[tuple[Surface, int]] = []

        maximum_width = round(self.rect.width * 0.88)

        for line in self.lines:
            font = self._get_font(
                line.font_size,
                line.bold,
            )

            pieces = self._fit_text(
                line.text,
                font,
                maximum_width,
            )

            for index, piece in enumerate(pieces):
                image = font.render(
                    piece,
                    True,
                    line.colour,
                )

                if index == len(pieces) - 1:
                    spacing = self._scaled_spacing(
                        line.spacing_after
                    )
                else:
                    spacing = self._scaled_spacing(5)

                rendered.append((image, spacing))

        return rendered

    def _calculate_total_height(self) -> int:
        total_height = 0

        for image, spacing_after in self.rendered_lines:
            total_height += image.get_height()
            total_height += spacing_after

        return total_height

    def update(self, dt: float) -> None:
        super().update(dt)

        if self.returning_to_home:
            return

        self.scroll_position -= self.scroll_speed * dt

        final_content_bottom = (
            self.scroll_position + self.total_height
        )

        if final_content_bottom > -self._scaled_spacing(20):
            return

        self.finished_delay += dt

        if self.finished_delay >= 2.5:
            self._return_to_home_screen()

    def draw(self, surface: Surface) -> None:
        surface.fill(BLACK_COLOR)

        current_y = self.scroll_position
        screen_centre = surface.get_width() // 2

        for image, spacing_after in self.rendered_lines:
            image_rect = image.get_rect(
                centerx=screen_centre,
                top=round(current_y),
            )

            if (
                image_rect.bottom >= 0
                and image_rect.top <= surface.get_height()
            ):
                surface.blit(image, image_rect)

            current_y += image.get_height()
            current_y += spacing_after

    def process_event(
        self,
        event: PlayerInput,
    ) -> PlayerInput | None:
        if self.returning_to_home:
            return None

        event_text = str(event).lower()

        skip_inputs = (
            "escape",
            "back",
            "cancel",
            "interact",
            "confirm",
            "enter",
            "return",
        )

        if any(
            input_name in event_text
            for input_name in skip_inputs
        ):
            self._return_to_home_screen()

            return None

        return event

    def _return_to_home_screen(self) -> None:
        """
        Remove the active campaign world and return to StartState.

        quit_world is the existing Tuxemon action used for returning to the
        black background and main home screen.
        """
        if self.returning_to_home:
            return

        self.returning_to_home = True

        self.client.event_engine.execute_action(
            "quit_world",
            [],
            True,
        )
