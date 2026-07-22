# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import pygame

from collections import OrderedDict
from collections.abc import Callable, Generator
from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar

from pygame import SRCALPHA, draw
from pygame.font import Font
from pygame.rect import Rect
from pygame.surface import Surface

from tuxemon.animation import ScheduleType
from tuxemon.graphics import ColorLike, load_and_scale, load_image
from tuxemon.locale.locale import T
from tuxemon.menu.interface import ExpBar, HpBar, MenuItem
from tuxemon.menu.menu import Menu
from tuxemon.monster.filter import MonsterFilter
from tuxemon.monster.monster import Monster
from tuxemon.monster.renderer import MonsterRenderer
from tuxemon.platform.const.graphics import BG_MONSTERS, TRANSPARENT_COLOR
from tuxemon.platform.const.sizes import PARTY_LIMIT
from tuxemon.session import local_session
from tuxemon.sprite import Sprite
from tuxemon.tools import open_choice_dialog, open_dialog
from tuxemon.ui.graphic_box import GraphicBox
from tuxemon.ui.menu_options import (
    MenuOptions,
    create_choice_options,
    create_yes_no_options,
)
from tuxemon.ui.text import TextArea, draw_text

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.entity.party import PartyHandler
    from tuxemon.item.item import Item
    from tuxemon.monster.monster import Monster
    from tuxemon.prepare import DisplayContext

LAYER_MONSTER_ICONS = 20
LAYER_PORTRAIT = 30


class MonsterMenuState(Menu[Monster | None]):
    """
    A class to create monster menu objects.

    The monster menu allows you to view monsters in your party,
    teach them moves, and switch them both in and out of combat.
    """

    background_filename = BG_MONSTERS
    draw_borders = False

    name: ClassVar[str] = "MonsterMenuState"

    def __init__(
        self,
        client: BaseClient,
        monsters: list[Monster],
        monster_filter: MonsterFilter | None = None,
        *,
        on_selection: Callable[[MenuItem[Monster | None]], None] | None = None,
        is_valid_entry: Callable[[Monster | None], bool] | None = None,
        on_selection_change: Callable[[MonsterMenuState], None] | None = None,
        **kwargs: Any,
    ):
        super().__init__(client=client, **kwargs)
        self._external_on_selection = on_selection
        self._external_is_valid_entry = is_valid_entry
        self._external_on_selection_change = on_selection_change
        self.monster_filter = monster_filter or MonsterFilter()
        self.monsters = self.monster_filter.get_filtered_monsters(monsters)

        # make a text area to show messages
        rect = self.client.context.scaling.scale_tuple((20, 80, 80, 100))
        self.text_area = TextArea(
            font=self.font,
            font_color=self.font_color,
            rect=Rect(rect),
            scaling=self.client.context.scaling,
            font_shadow=(96, 96, 96),
        )
        self.sprites.add(self.text_area, layer=100)
        self.monster_stats_display = MonsterStatsDisplay(self)
        self.fighter_profile_display = FighterProfileDisplay(self)
        self.monster_sprite_displays: list[MonsterSpriteDisplay] = []
        self.monster_portrait_display = MonsterPortraitDisplay(self)

        # Set up the border images used for the monster slots
        self.hp_bar = HpBar(self.client.context)
        self.exp_bar = ExpBar(self.client.context)
        self.slot_renderer = MonsterSlotRenderer(
            self.client.context, self.font, self.hp_bar, self.font_color
        )

    def draw(self, surface: Surface) -> None:
        """Draw the fighter menu with a compact career profile."""
        super().draw(surface)

        screen_width, screen_height = surface.get_size()

        try:
            monster = self.monsters[self.selected_index]
        except IndexError:
            monster = None

        profile = self.fighter_profile_display

        def profile_value(
            method_names: tuple[str, ...],
            fallback: str,
        ) -> str:
            """Safely read a fighter-profile value."""
            for method_name in method_names:
                method = getattr(profile, method_name, None)

                if not callable(method):
                    continue

                try:
                    value = method()
                except TypeError:
                    try:
                        value = method(monster)
                    except (AttributeError, TypeError):
                        continue
                except AttributeError:
                    continue

                if value is not None and str(value).strip():
                    return str(value)

            return fallback

        academy = profile_value(
            (
                "get_academy_name",
                "get_academy",
            ),
            "Duncan Academy",
        )

        current_goal = profile_value(
            (
                "get_current_goal",
                "get_goal",
            ),
            "Become KOTH Champion",
        )

        wins = 0
        losses = 0

        # Locate the real saved character battle history.
        #
        # Different Tuxemon states expose the player through different
        # attributes. Examine all available candidates and use the record
        # with the greatest number of completed battles. This prevents an
        # empty secondary player object from incorrectly producing 0-0.
        candidate_characters: list[object] = []

        def add_candidate(candidate: object | None) -> None:
            if candidate is None:
                return

            if any(
                candidate is existing
                for existing in candidate_characters
            ):
                return

            candidate_characters.append(candidate)

        add_candidate(getattr(self, "char", None))
        add_candidate(getattr(self, "character", None))
        add_candidate(getattr(self, "player", None))

        client_context = getattr(self.client, "context", None)
        client_session = getattr(self.client, "session", None)

        add_candidate(
            getattr(client_context, "player", None)
        )
        add_candidate(
            getattr(client_session, "player", None)
        )
        add_candidate(
            getattr(self.client, "player", None)
        )

        context_session = getattr(
            client_context,
            "session",
            None,
        )

        add_candidate(
            getattr(context_session, "player", None)
        )

        # Some menu states retain the actual player as an owner or trainer.
        if monster is not None:
            add_candidate(
                getattr(monster, "owner", None)
            )
            add_candidate(
                getattr(monster, "trainer", None)
            )

        best_summary: dict[str, int] | None = None
        best_total = -1
        best_source = "not found"

        for candidate in candidate_characters:
            battle_handler = getattr(
                candidate,
                "battle_handler",
                None,
            )

            get_summary = getattr(
                battle_handler,
                "get_battle_outcome_summary",
                None,
            )

            if not callable(get_summary):
                continue

            try:
                summary = get_summary()

                candidate_wins = int(
                    summary.get("won", 0)
                )
                candidate_losses = int(
                    summary.get("lost", 0)
                )
                candidate_draws = int(
                    summary.get("draw", 0)
                )

                total = (
                    candidate_wins
                    + candidate_losses
                    + candidate_draws
                )
            except (
                AttributeError,
                TypeError,
                ValueError,
            ):
                continue

            if total > best_total:
                best_total = total
                best_summary = summary
                best_source = (
                    f"{type(candidate).__module__}."
                    f"{type(candidate).__name__}"
                )

        if best_summary is not None:
            wins = int(
                best_summary.get("won", 0)
            )
            losses = int(
                best_summary.get("lost", 0)
            )

        # Print once so the selected source can be verified.
        if not getattr(
            self,
            "_battle_record_source_reported",
            False,
        ):
            print(
                "FIGHTER PROFILE BATTLE RECORD:",
                {
                    "source": best_source,
                    "total": best_total,
                    "wins": wins,
                    "losses": losses,
                    "candidates": [
                        (
                            f"{type(candidate).__module__}."
                            f"{type(candidate).__name__}"
                        )
                        for candidate in candidate_characters
                    ],
                },
            )

            self._battle_record_source_reported = True

        # Cream profile panel beneath the green status bar.
        panel_left = int(screen_width * 0.515)
        panel_top = int(screen_height * 0.325)
        panel_right = screen_width - int(screen_width * 0.045)
        panel_bottom = screen_height - int(screen_height * 0.075)

        panel_width = panel_right - panel_left
        panel_height = panel_bottom - panel_top

        if panel_width <= 0 or panel_height <= 0:
            return

        shadow_colour = (92, 91, 82)
        outer_border = (91, 94, 91)
        border_highlight = (218, 233, 220)
        panel_colour = (218, 216, 191)
        panel_inner = (224, 222, 199)
        divider_colour = (112, 114, 108)

        academy_circle = (241, 242, 232)
        academy_dark = (52, 61, 61)

        trophy_gold = (237, 180, 35)
        trophy_light = (255, 213, 79)
        trophy_dark = (137, 88, 15)

        target_red = (206, 64, 53)
        target_white = (244, 240, 224)
        arrow_gold = (237, 179, 35)

        outer = Rect(
            panel_left,
            panel_top,
            panel_width,
            panel_height,
        )

        shadow = outer.move(6, 7)

        pygame.draw.rect(
            surface,
            shadow_colour,
            shadow,
            border_radius=5,
        )

        pygame.draw.rect(
            surface,
            outer_border,
            outer,
            border_radius=5,
        )

        inner = Rect(
            outer.x + 5,
            outer.y + 5,
            outer.width - 10,
            outer.height - 10,
        )

        pygame.draw.rect(
            surface,
            panel_colour,
            inner,
            border_radius=3,
        )

        highlight = Rect(
            inner.x + 3,
            inner.y + 3,
            inner.width - 6,
            inner.height - 6,
        )

        pygame.draw.rect(
            surface,
            border_highlight,
            highlight,
            width=2,
            border_radius=2,
        )

        content = Rect(
            inner.x + 18,
            inner.y + 15,
            inner.width - 36,
            inner.height - 30,
        )

        pygame.draw.rect(
            surface,
            panel_inner,
            content,
        )

        def draw_scaled_text(
            value: str,
            position: tuple[int, int],
            *,
            scale: float = 0.68,
            max_width: int | None = None,
        ) -> None:
            """
            Render using the existing game font, then reduce the result.

            This keeps the current pixel font while preventing long text
            from overflowing the profile panel.
            """
            temporary_width = max(
                700,
                max_width * 2 if max_width else 700,
            )

            temporary = pygame.Surface(
                (temporary_width, 100),
                pygame.SRCALPHA,
            )

            profile._render_text(
                temporary,
                str(value),
                (0, 0),
            )

            bounds = temporary.get_bounding_rect()

            if bounds.width <= 0 or bounds.height <= 0:
                return

            rendered = temporary.subsurface(bounds).copy()

            target_width = max(
                1,
                int(rendered.get_width() * scale),
            )
            target_height = max(
                1,
                int(rendered.get_height() * scale),
            )

            if max_width and target_width > max_width:
                ratio = max_width / target_width
                target_width = max_width
                target_height = max(
                    1,
                    int(target_height * ratio),
                )

            rendered = pygame.transform.scale(
                rendered,
                (target_width, target_height),
            )

            surface.blit(
                rendered,
                position,
            )

        section_height = content.height // 3
        icon_x = content.x + 82
        text_x = content.x + 172

        text_max_width = max(
            100,
            content.right - text_x - 18,
        )

        def draw_divider(y: int) -> None:
            pygame.draw.line(
                surface,
                divider_colour,
                (content.x + 10, y),
                (content.right - 10, y),
                2,
            )

        def draw_academy_icon(
            centre_x: int,
            centre_y: int,
        ) -> None:
            pygame.draw.circle(
                surface,
                academy_circle,
                (centre_x, centre_y),
                37,
            )

            pygame.draw.circle(
                surface,
                academy_dark,
                (centre_x, centre_y),
                37,
                width=3,
            )

            pygame.draw.polygon(
                surface,
                academy_dark,
                (
                    (centre_x, centre_y - 25),
                    (centre_x - 29, centre_y + 24),
                    (centre_x + 29, centre_y + 24),
                ),
            )

            pygame.draw.polygon(
                surface,
                academy_circle,
                (
                    (centre_x, centre_y - 9),
                    (centre_x - 9, centre_y + 17),
                    (centre_x + 9, centre_y + 17),
                ),
            )

        def draw_trophy_icon(
            centre_x: int,
            centre_y: int,
        ) -> None:
            cup = Rect(
                centre_x - 22,
                centre_y - 27,
                44,
                37,
            )

            pygame.draw.rect(
                surface,
                trophy_gold,
                cup,
                border_radius=5,
            )

            pygame.draw.rect(
                surface,
                trophy_dark,
                cup,
                width=3,
                border_radius=5,
            )

            pygame.draw.rect(
                surface,
                trophy_light,
                Rect(
                    cup.x + 6,
                    cup.y + 5,
                    cup.width - 12,
                    7,
                ),
                border_radius=2,
            )

            pygame.draw.arc(
                surface,
                trophy_gold,
                Rect(
                    centre_x - 37,
                    centre_y - 23,
                    22,
                    28,
                ),
                1.2,
                5.1,
                5,
            )

            pygame.draw.arc(
                surface,
                trophy_gold,
                Rect(
                    centre_x + 15,
                    centre_y - 23,
                    22,
                    28,
                ),
                -1.95,
                1.95,
                5,
            )

            pygame.draw.rect(
                surface,
                trophy_gold,
                Rect(
                    centre_x - 4,
                    centre_y + 9,
                    8,
                    16,
                ),
            )

            pygame.draw.rect(
                surface,
                trophy_gold,
                Rect(
                    centre_x - 19,
                    centre_y + 24,
                    38,
                    8,
                ),
                border_radius=2,
            )

            pygame.draw.rect(
                surface,
                trophy_dark,
                Rect(
                    centre_x - 19,
                    centre_y + 24,
                    38,
                    8,
                ),
                width=2,
                border_radius=2,
            )

        def draw_target_icon(
            centre_x: int,
            centre_y: int,
        ) -> None:
            pygame.draw.circle(
                surface,
                target_red,
                (centre_x, centre_y),
                37,
            )

            pygame.draw.circle(
                surface,
                target_white,
                (centre_x, centre_y),
                27,
            )

            pygame.draw.circle(
                surface,
                target_red,
                (centre_x, centre_y),
                18,
            )

            pygame.draw.circle(
                surface,
                target_white,
                (centre_x, centre_y),
                9,
            )

            pygame.draw.circle(
                surface,
                target_red,
                (centre_x, centre_y),
                4,
            )

            pygame.draw.line(
                surface,
                arrow_gold,
                (centre_x + 1, centre_y - 1),
                (centre_x + 31, centre_y - 31),
                5,
            )

            pygame.draw.polygon(
                surface,
                arrow_gold,
                (
                    (centre_x + 31, centre_y - 31),
                    (centre_x + 21, centre_y - 30),
                    (centre_x + 30, centre_y - 21),
                ),
            )

        # Academy section.
        academy_centre_y = (
            content.y + section_height // 2
        )

        draw_academy_icon(
            icon_x,
            academy_centre_y,
        )

        draw_scaled_text(
            "ACADEMY",
            (
                text_x,
                academy_centre_y - 38,
            ),
            scale=0.67,
            max_width=text_max_width,
        )

        draw_scaled_text(
            academy,
            (
                text_x,
                academy_centre_y + 9,
            ),
            scale=0.58,
            max_width=text_max_width,
        )

        divider_one = content.y + section_height
        draw_divider(divider_one)

        # Record section.
        record_centre_y = (
            content.y
            + section_height
            + section_height // 2
        )

        draw_trophy_icon(
            icon_x,
            record_centre_y - 4,
        )

        draw_scaled_text(
            "RECORD",
            (
                text_x,
                record_centre_y - 47,
            ),
            scale=0.67,
            max_width=text_max_width,
        )

        label_x = text_x
        colon_x = text_x + 118
        record_value_x = text_x + 145

        draw_scaled_text(
            "Wins",
            (
                label_x,
                record_centre_y - 3,
            ),
            scale=0.57,
            max_width=105,
        )

        draw_scaled_text(
            ":",
            (
                colon_x,
                record_centre_y - 3,
            ),
            scale=0.57,
        )

        draw_scaled_text(
            str(wins),
            (
                record_value_x,
                record_centre_y - 3,
            ),
            scale=0.57,
            max_width=90,
        )

        draw_scaled_text(
            "Losses",
            (
                label_x,
                record_centre_y + 31,
            ),
            scale=0.57,
            max_width=105,
        )

        draw_scaled_text(
            ":",
            (
                colon_x,
                record_centre_y + 31,
            ),
            scale=0.57,
        )

        draw_scaled_text(
            str(losses),
            (
                record_value_x,
                record_centre_y + 31,
            ),
            scale=0.57,
            max_width=90,
        )

        divider_two = content.y + section_height * 2
        draw_divider(divider_two)

        # Current goal section.
        goal_centre_y = (
            content.y
            + section_height * 2
            + section_height // 2
        )

        draw_target_icon(
            icon_x,
            goal_centre_y,
        )

        draw_scaled_text(
            "CURRENT GOAL",
            (
                text_x,
                goal_centre_y - 37,
            ),
            scale=0.62,
            max_width=text_max_width,
        )

        draw_scaled_text(
            current_goal,
            (
                text_x,
                goal_centre_y + 10,
            ),
            scale=0.52,
            max_width=text_max_width,
        )

    def calc_menu_items_rect(self) -> Rect:
        width, height = self.rect.size
        left = width // 2.25
        top = height // 12
        width //= 2
        return Rect(left, top, width, height - top * 2)

    def initialize_items(
        self,
    ) -> Generator[MenuItem[Monster | None], None, None]:
        # position the monster portrait
        try:
            monster = self.monsters[self.selected_index]
            self.monster_portrait_display.update(monster)
        except IndexError:
            self.monster_portrait_display.update(None)

        self.animations.empty()
        self.monster_portrait_display.animate_down()

        # position and animate the monster portrait
        _width, _height = self.client.context.resolution
        width = _width // 2
        height = _height // int(PARTY_LIMIT * 1.5)

        # JiuJitsu Island displays one fighter slot for the player character.
        # The remaining five Pokémon-style party slots are intentionally removed.
        rect = Rect(0, 0, width, height)
        surface = Surface(rect.size, SRCALPHA)
        item = MenuItem(surface, None, None, None)
        yield item

        self.refresh_menu_items()

        # Explicitly populate both information panels when the menu first opens.
        monster: Monster | None = None

        try:
            monster = self.monsters[self.selected_index]
        except IndexError:
            pass

        self.monster_stats_display.update(monster)
        self.fighter_profile_display.update(monster)

    def on_menu_selection(self, item: MenuItem[Monster | None]) -> None:
        if self._external_on_selection:
            return self._external_on_selection(item)
        return None

    def is_valid_entry(self, monster: Monster | None) -> bool:
        if self._external_is_valid_entry:
            return self._external_is_valid_entry(monster)
        return monster is not None

    def refresh_menu_items(self) -> None:
        """Used to render slots after their 'focus' flags change."""
        MonsterSpriteDisplay.cleanup(self.monster_sprite_displays)

        for index, item in enumerate(self.menu_items):
            self.assign_monster_to_item(index, item)

    def assign_monster_to_item(
        self, index: int, item: MenuItem[Monster | None]
    ) -> None:
        monster = self.monsters[index] if index < len(self.monsters) else None
        item.game_object = monster
        item.enabled = (monster is not None) and self.is_valid_entry(monster)
        item.image.fill(TRANSPARENT_COLOR)
        item.in_focus = (index == self.selected_index) and item.enabled
        self.slot_renderer.render_slot(
            item.image, item.image.get_rect(), monster, item.in_focus
        )

        if monster:
            sprite_display = MonsterSpriteDisplay(self)
            sprite_display.update(monster, item.rect)
            self.monster_sprite_displays.append(sprite_display)

    def on_menu_selection_change(self) -> None:
        if self._external_on_selection_change:
            self._external_on_selection_change(self)

        monster: Monster | None = None
        try:
            monster = self.monsters[self.selected_index]
            self.monster_portrait_display.update(monster)
        except IndexError:
            self.monster_portrait_display.update(None)

        self.monster_stats_display.update(monster)
        self.refresh_menu_items()

        # Draw the profile after refreshing the menu so its card sprite
        # is not cleared or covered by the refreshed menu items.
        self.fighter_profile_display.update(monster)

    def remove_monster_sprite_display(self, monster: Monster) -> None:
        for sprite_display in self.monster_sprite_displays:
            if sprite_display.monster == monster:
                if sprite_display.sprite:
                    self.sprites.remove(sprite_display.sprite)
                self.monster_sprite_displays.remove(sprite_display)
                break


class MonsterMenuHandler:
    """Handles interactions within the monster menu."""

    def __init__(self, client: BaseClient, party: PartyHandler) -> None:
        """Initialize with client and character."""
        self.name = "WorldMenuState"
        self.client = client
        self.party = party
        self.context: dict[str, Any] = {}

    def monster_menu_hook(self, monster_menu: MonsterMenuState) -> None:
        """Handles monster reordering."""
        monster = self.context.get("monster")
        if not monster:
            return

        monster_list = self.party.monsters
        original = monster_menu.get_selected_item()
        if original and original.game_object:
            original_monster = original.game_object
            index = monster_list.index(original_monster)
            monster_list[self.context["old_index"]] = original_monster
            monster_list[index] = self.context["monster"]
            self.context["old_index"] = index

    def select_monster(self, monster: Monster) -> None:
        """Selects a monster for movement."""
        self.context["monster"] = monster
        self.context["old_index"] = self.party.monsters.index(monster)
        self.client.remove_state_by_name("ChoiceState")

    def monster_stats(self, monster: Monster) -> None:
        """Displays monster statistics."""
        self.client.remove_state_by_name("ChoiceState")
        params = {
            "monster": monster,
            "source": self.name,
            "monsters": self.party.monsters,
        }
        self.client.push_state("MonsterInfoState", **params)

    def monster_techs(self, monster: Monster) -> None:
        """Displays monster techniques."""
        self.client.remove_state_by_name("ChoiceState")
        params = {
            "monster": monster,
            "source": self.name,
            "monsters": self.party.monsters,
        }
        self.client.push_state("MonsterMovesState", **params)

    def remove_item_direct(self, monster: Monster) -> None:
        item = monster.held_item
        if item:
            monster.unequip_item()
            self.party.owner.bag.add_item(item)

        self.client.remove_state_by_name("ChoiceState")
        self.monster_menu.refresh_menu_items()

    def open_item_picker(self, monster: Monster) -> None:
        from tuxemon.item.filter import ItemFilter
        from tuxemon.states.item_menu import ItemMenuState

        self.client.remove_state_by_name("ChoiceState")
        items_filtered = ItemFilter(self.party.owner.bag.items)
        items_filtered.add_filter(lambda item: item.behaviors.holdable)

        self.client.push_state(
            ItemMenuState(
                self.client,
                character=self.party.owner,
                source=self.name,
                item_filter=items_filtered,
                on_selection=lambda menu_item: self._equip_from_picker(
                    monster, menu_item
                ),
            )
        )

    def _equip_from_picker(
        self, monster: Monster, menu_item: MenuItem[Item | None]
    ) -> None:
        item = menu_item.game_object
        if not item:
            return

        monster.equip_item(item)
        self.party.owner.bag.remove_item(item)
        self.client.remove_state_by_name("ItemMenuState")
        self.monster_menu.refresh_menu_items()

    def swap_items(self, mon_a: Monster, mon_b: Monster) -> None:
        """Swaps held items between two monsters."""
        mon_a.swap_items(mon_b)
        self.client.remove_state_by_name("ChoiceState")
        self.monster_menu.refresh_menu_items()

    def open_swap_picker(self, monster: Monster) -> None:
        """Opens a submenu to choose another monster to swap items with."""
        self.client.remove_state_by_name("ChoiceState")

        candidates = [
            m for m in self.party.monsters if m is not monster and m.held_item
        ]

        if not candidates:
            return

        actions = {
            m.name: partial(self.swap_items, monster, m) for m in candidates
        }
        menu = MenuOptions(create_choice_options(actions))
        open_choice_dialog(self.client, menu, escape_key_exits=True)

    def release_monster(self, monster: Monster) -> None:
        """Shows confirmation for releasing a monster."""
        self.client.remove_state_by_name("ChoiceState")
        params = {"name": monster.name.upper()}
        msg = T.format("release_confirmation", params)
        open_dialog(self.client, [msg], dialog_speed="max")

        options = create_yes_no_options(
            yes_action=partial(self.positive_answer, monster),
            no_action=self.negative_answer,
        )

        menu = MenuOptions(options)
        open_choice_dialog(self.client, menu, escape_key_exits=False)

    def positive_answer(self, monster: Monster) -> None:
        """Handles monster release."""
        success = self.party.release_monster(monster)
        if success:
            self.client.remove_state_by_name("ChoiceState")
            self.client.remove_state_by_name("DialogState")
            params = {"name": monster.name.upper()}
            msg = T.format("tuxemon_released", params)
            open_dialog(self.client, [msg], dialog_speed="max")
            self.monster_menu.remove_monster_sprite_display(monster)

            num_monsters = len(self.party.monsters)
            if self.monster_menu.selected_index >= num_monsters:
                self.monster_menu.change_selection(max(0, num_monsters - 1))

            self.monster_menu.refresh_menu_items()
            self.monster_menu.on_menu_selection_change()
        else:
            open_dialog(
                self.client, [T.translate("cant_release")], dialog_speed="max"
            )

    def negative_answer(self) -> None:
        """Handles rejection for releasing a monster."""
        self.client.remove_state_by_name("ChoiceState")
        self.client.remove_state_by_name("DialogState")

    def open_monster_submenu(self, monster_menu: MonsterMenuState) -> None:
        """Opens a submenu for the selected monster."""
        original = monster_menu.get_selected_item()
        if not (original and original.game_object):
            return

        mon = original.game_object

        actions: dict[str, Callable[..., None]] = {
            "info": partial(self.monster_stats, mon),
        }

        if mon.moves.moves:
            actions["tech"] = partial(self.monster_techs, mon)

        if mon.held_item:
            actions["unequip_item"] = partial(self.remove_item_direct, mon)

        holdable_items = [
            item
            for item in self.party.owner.bag.items
            if item.behaviors.holdable
        ]

        if holdable_items:
            actions["equip_item"] = partial(self.open_item_picker, mon)

        other_with_items = [
            m for m in self.party.monsters if m is not mon and m.held_item
        ]

        if other_with_items:
            actions["swap_item"] = partial(self.open_swap_picker, mon)

        if self.party.party_size > 1:
            actions.update(
                {
                    "move": partial(self.select_monster, mon),
                    "sort": lambda: self.open_sort_submenu(monster_menu),
                    "release": partial(self.release_monster, mon),
                }
            )

        options = create_choice_options(actions)
        menu = MenuOptions(options)
        open_choice_dialog(self.client, menu, escape_key_exits=True)

    def handle_selection(
        self,
        menu_item: MenuItem[Monster | None],
        monster_menu: MonsterMenuState,
    ) -> None:
        """Handles selection interaction for monsters."""
        if "monster" in self.context:
            del self.context["monster"]
        else:
            self.open_monster_submenu(monster_menu)

    def sort_monsters(
        self,
        monster_menu: MonsterMenuState,
        key: Callable[[Monster], Any],
        reverse: bool = False,
    ) -> None:
        """Sorts the monsters in the party by a given key."""
        self.party.monsters.sort(key=key, reverse=reverse)
        monster_menu.monsters = self.party.monsters
        monster_menu.refresh_menu_items()
        monster_menu.on_menu_selection_change()

    def open_monster_menu(self) -> None:
        """Pushes the monster menu state."""
        self.monster_menu = self.client.push_state(
            MonsterMenuState(
                self.client,
                self.party.monsters,
                on_selection=lambda item: self.handle_selection(
                    item, self.monster_menu
                ),
                on_selection_change=self.monster_menu_hook,
            )
        )

    def open_sort_submenu(self, monster_menu: MonsterMenuState) -> None:
        """Opens a submenu with sorting options."""
        actions: dict[str, Callable[..., None]] = {
            "level": lambda: self.sort_monsters(
                monster_menu, key=lambda m: m.level
            ),
            "hp": lambda: self.sort_monsters(
                monster_menu, key=lambda m: m.hp_ratio, reverse=True
            ),
            "name": lambda: self.sort_monsters(
                monster_menu, key=lambda m: m.name.lower()
            ),
            "id": lambda: self.sort_monsters(
                monster_menu, key=lambda m: m.txmn_id
            ),
        }
        options = create_choice_options(actions)
        menu = MenuOptions(options)
        open_choice_dialog(self.client, menu, escape_key_exits=True)


class MonsterStatsDisplay:
    def __init__(self, menu_state: MonsterMenuState) -> None:
        self.menu_state = menu_state
        self.sprite = TextArea(
            font=self.menu_state.font,
            font_color=self.menu_state.font_color,
            rect=Rect(0, 0, 1, 1),
            scaling=self.menu_state.client.context.scaling,
        )
        self.menu_state.sprites.add(self.sprite, layer=LAYER_MONSTER_ICONS)

    def update(self, monster: Monster | None) -> None:
        if not monster:
            self.sprite.image = self.menu_state.shadow_text("")
            return

        stats = OrderedDict(
            [
                (
                    "Health",
                    f"{monster.current_hp}/{monster.hp}",
                ),
                ("Defence", str(monster.armour)),
                ("Escapes", str(monster.dodge)),
                ("Submissions", str(monster.melee)),
                ("Takedowns", str(monster.ranged)),
                ("Cardio", str(monster.speed)),
            ]
        )

        max_len = max(len(label) for label in stats.keys())
        text = "\n".join(
            f"{label:<{max_len}}: {value}" for label, value in stats.items()
        )

        self.sprite.image = self.menu_state.shadow_text(text)
        width, height = self.menu_state.client.context.resolution
        self.sprite.rect.topleft = (width // 10, height // 2 + 50)


class FighterProfileDisplay:
    """Draw the complete fighter profile as one reliable surface."""

    BELT_ORDER = (
        ("black_belt", "Black Belt"),
        ("brown_belt", "Brown Belt"),
        ("purple_belt", "Purple Belt"),
        ("blue_belt", "Blue Belt"),
        ("white_belt", "White Belt"),
    )

    def __init__(self, menu_state: MonsterMenuState) -> None:
        self.menu_state = menu_state

        self.sprite = Sprite()
        self.sprite.image = Surface((1, 1), SRCALPHA)
        self.sprite.rect = self.sprite.image.get_rect()

        # Keep the complete card above the menu background.
        self.menu_state.sprites.add(
            self.sprite,
            layer=LAYER_MONSTER_ICONS + 5,
        )

    def get_player(self) -> Any:
        return local_session.player

    def get_current_belt(self) -> str:
        player = self.get_player()

        for item_slug, belt_name in self.BELT_ORDER:
            if player.bag.has_item(item_slug):
                return belt_name

        return "Unranked"

    def get_battle_record(self) -> tuple[int, int]:
        player = self.get_player()

        if not player.battle_handler.get_battles():
            return 0, 0

        summary = player.battle_handler.get_battle_outcome_summary()

        return (
            int(summary.get("won", 0)),
            int(summary.get("lost", 0)),
        )

    def get_title_count(self) -> int:
        player = self.get_player()

        if player.bag.has_item("koth_championship_belt"):
            return 1

        return 0

    def get_current_goal(self) -> str:
        player = self.get_player()

        if player.bag.has_item("koth_championship_belt"):
            return "Defend KOTH Championship"

        if player.bag.has_item("black_belt"):
            return "Become KOTH Champion"

        if player.bag.has_item("brown_belt"):
            return "Earn Black Belt"

        if player.bag.has_item("purple_belt"):
            return "Earn Brown Belt"

        if player.bag.has_item("blue_belt"):
            return "Earn Purple Belt"

        if player.bag.has_item("white_belt"):
            return "Earn Blue Belt"

        return "Begin Your Journey"

    def _render_text(
        self,
        surface: Surface,
        text: str,
        position: tuple[int, int],
    ) -> None:
        """Render pixel text with the same dark shadow style as the menu."""
        x, y = position

        shadow = self.menu_state.font.render(
            text,
            True,
            (105, 104, 92),
        )
        foreground = self.menu_state.font.render(
            text,
            True,
            (20, 20, 18),
        )

        surface.blit(shadow, (x + 2, y + 2))
        surface.blit(foreground, (x, y))

    def _draw_separator(
        self,
        surface: Surface,
        y: int,
        left: int,
        right: int,
    ) -> None:
        """Draw the segmented horizontal lines from the reference design."""
        x = left

        while x < right:
            draw.line(
                surface,
                (105, 103, 95),
                (x, y),
                (min(x + 5, right), y),
                2,
            )
            x += 8

    def update(self, monster: Monster | None) -> None:
        if not monster:
            self.sprite.image = Surface((1, 1), SRCALPHA)
            self.sprite.rect = self.sprite.image.get_rect()
            return

        screen_width, screen_height = (
            self.menu_state.client.context.resolution
        )

        # Fill the empty right-hand area beneath the green status panel.
        panel_left = int(screen_width * 0.40)
        panel_top = int(screen_height * 0.27)
        panel_width = int(screen_width * 0.52)
        panel_height = int(screen_height * 0.62)

        surface = Surface(
            (panel_width + 10, panel_height + 10),
            SRCALPHA,
        )

        # Card shadow.
        draw.rect(
            surface,
            (45, 43, 49, 150),
            Rect(8, 8, panel_width, panel_height),
        )

        # Dark outside border.
        draw.rect(
            surface,
            (73, 69, 76),
            Rect(0, 0, panel_width, panel_height),
        )

        # Grey frame.
        draw.rect(
            surface,
            (132, 124, 122),
            Rect(3, 3, panel_width - 6, panel_height - 6),
        )

        # Cream border.
        draw.rect(
            surface,
            (214, 212, 180),
            Rect(7, 7, panel_width - 14, panel_height - 14),
        )

        # Main cream panel.
        draw.rect(
            surface,
            (225, 222, 190),
            Rect(11, 11, panel_width - 22, panel_height - 22),
        )

        # Cyan highlights matching the menu frame.
        draw.line(
            surface,
            (202, 255, 244),
            (12, 10),
            (panel_width - 12, 10),
            3,
        )

        draw.line(
            surface,
            (202, 255, 244),
            (10, 12),
            (10, panel_height - 12),
            3,
        )

        font_height = self.menu_state.font.get_linesize()

        left_x = int(panel_width * 0.05)
        nested_x = int(panel_width * 0.13)
        colon_x = int(panel_width * 0.40)
        value_x = int(panel_width * 0.46)
        right_x = panel_width - left_x

        usable_height = panel_height - 34
        row_gap = max(
            font_height + 5,
            usable_height // 11,
        )

        y = 25

        wins, losses = self.get_battle_record()

        # Belt.
        self._render_text(
            surface,
            "Belt",
            (left_x, y),
        )
        self._render_text(
            surface,
            ":",
            (colon_x, y),
        )
        self._render_text(
            surface,
            self.get_current_belt(),
            (value_x, y),
        )

        # Academy.
        y += row_gap

        self._render_text(
            surface,
            "Academy",
            (left_x, y),
        )
        self._render_text(
            surface,
            ":",
            (colon_x, y),
        )
        self._render_text(
            surface,
            "Duncan Academy",
            (value_x, y),
        )

        # Divider.
        y += row_gap

        self._draw_separator(
            surface,
            y,
            left_x,
            right_x,
        )

        # Record heading.
        y += max(15, row_gap // 2)

        self._render_text(
            surface,
            "Record",
            (left_x, y),
        )

        # Wins.
        y += row_gap

        self._render_text(
            surface,
            "Wins",
            (nested_x, y),
        )
        self._render_text(
            surface,
            ":",
            (colon_x, y),
        )
        self._render_text(
            surface,
            str(wins),
            (value_x, y),
        )

        # Losses.
        y += row_gap

        self._render_text(
            surface,
            "Losses",
            (nested_x, y),
        )
        self._render_text(
            surface,
            ":",
            (colon_x, y),
        )
        self._render_text(
            surface,
            str(losses),
            (value_x, y),
        )

        # Divider.
        y += row_gap

        self._draw_separator(
            surface,
            y,
            left_x,
            right_x,
        )

        # Titles.
        y += max(15, row_gap // 2)

        self._render_text(
            surface,
            "Titles",
            (left_x, y),
        )
        self._render_text(
            surface,
            ":",
            (colon_x, y),
        )
        self._render_text(
            surface,
            str(self.get_title_count()),
            (value_x, y),
        )

        # Divider.
        y += row_gap

        self._draw_separator(
            surface,
            y,
            left_x,
            right_x,
        )

        # Current goal.
        y += max(15, row_gap // 2)

        self._render_text(
            surface,
            "Current Goal",
            (left_x, y),
        )
        self._render_text(
            surface,
            ":",
            (colon_x, y),
        )

        y += row_gap

        self._render_text(
            surface,
            self.get_current_goal(),
            (nested_x, y),
        )

        self.sprite.image = surface
        self.sprite.rect = surface.get_rect(
            topleft=(panel_left, panel_top)
        )

        # Menu setup and refresh operations may clear auxiliary sprites.
        # Ensure the fighter profile is present and drawn above everything.
        if self.sprite not in self.menu_state.sprites:
            self.menu_state.sprites.add(
                self.sprite,
                layer=200,
            )
        else:
            self.menu_state.sprites.change_layer(
                self.sprite,
                200,
            )

        self.sprite.visible = True
        self.sprite.dirty = 1

class MonsterSpriteDisplay:
    """
    Manages the sprite used to visually represent a monster inside the party menu.

    Each instance tracks a single monster and its corresponding sprite. The class
    is responsible for creating the sprite, positioning it relative to the slot
    rectangle, updating it when the selected monster changes, and removing it
    cleanly from the menu state's sprite group when no longer needed.
    """

    def __init__(self, menu_state: MonsterMenuState) -> None:
        self.menu_state = menu_state
        self.scaling = self.menu_state.client.context.scaling
        self.resolution = self.menu_state.client.context.resolution
        self.sprite: Sprite | None = None
        self.monster: Monster | None = None

    @staticmethod
    def cleanup(displays: list[MonsterSpriteDisplay]) -> None:
        for display in displays:
            display.remove_sprite()
        displays.clear()

    def update(self, monster: Monster | None, rect: Rect) -> None:
        self.monster = monster

        if monster:
            if self.sprite:
                self.menu_state.sprites.remove(self.sprite)

            renderer = MonsterRenderer(monster, scale=2.5, frame_duration=0.25)
            self.sprite = renderer.get_sprite("menu")
            self.menu_state.sprites.add(self.sprite, layer=LAYER_MONSTER_ICONS)

            width = self.resolution[0]
            margin = int(width * 0.005)
            self.sprite.rect.x = width - (self.sprite.rect.width + margin)
            self.sprite.rect.y = rect.y + self.scaling.scale_int(10)

        else:
            self.remove_sprite()

    def remove_sprite(self) -> None:
        if self.sprite is not None:
            self.menu_state.sprites.remove(self.sprite)
            self.sprite = None
        self.monster = None


class MonsterPortraitDisplay:
    def __init__(self, menu_state: MonsterMenuState) -> None:
        self.menu_state = menu_state
        self.scaling = self.menu_state.client.context.scaling
        self.resolution = self.menu_state.client.context.resolution
        self.portrait = Sprite()
        self.portrait.rect = Rect(0, 0, 0, 0)
        self.menu_state.sprites.add(self.portrait, layer=LAYER_PORTRAIT)

    def update(self, monster: Monster | None) -> None:
        image = None
        if monster is not None:
            try:
                scale = self.menu_state.client.context.scale
                renderer = MonsterRenderer(monster, scale=scale)
                sprite = renderer.get_sprite("front")
                image = sprite.image
            except Exception:
                pass

        image = image or Surface((1, 1), SRCALPHA)

        self.portrait.image = image
        width, height = self.resolution
        self.portrait.rect = image.get_rect(
            centerx=width // 4,
            top=height // 12,
        )

    def animate_down(self) -> None:
        ani = self.menu_state.animate(
            self.portrait.rect,
            y=-self.scaling.scale_int(5),
            duration=1,
            transition="in_out_quad",
            relative=True,
        )
        ani.schedule(self.animate_up, ScheduleType.ON_FINISH)

    def animate_up(self) -> None:
        ani = self.menu_state.animate(
            self.portrait.rect,
            y=self.scaling.scale_int(5),
            duration=1,
            transition="in_out_quad",
            relative=True,
        )
        ani.schedule(self.animate_down, ScheduleType.ON_FINISH)


class MonsterSlotBorder:
    def __init__(self, root: str = "gfx/ui/monster/"):
        self.border_types = ["empty", "filled", "active"]
        self.borders: dict[str, GraphicBox] = {}
        self.load_borders(root)

    def load_borders(self, root: str) -> None:
        for border_type in self.border_types:
            filename = root + border_type + "_monster_slot_border.png"
            border = load_and_scale(filename)

            filename = root + border_type + "_monster_slot_bg.png"
            background = load_image(filename)

            window = GraphicBox(
                Rect(0, 0, 3, 3),
                border,
                background=background,
            )
            self.borders[border_type] = window

    def get_border(self, selected: bool, filled: bool) -> GraphicBox:
        if selected:
            return self.borders["active"]
        elif filled:
            return self.borders["filled"]
        else:
            return self.borders["empty"]


class MonsterSlotRenderer:
    """Unified renderer for monster slot layout."""

    def __init__(
        self,
        context: DisplayContext,
        font: Font,
        hp_bar: HpBar,
        font_color: ColorLike,
    ):
        self.context = context
        self.scaling = context.scaling
        self.font = font
        self.hp_bar = hp_bar
        self.font_color = font_color
        self.slot_border = MonsterSlotBorder()

    def render_slot(
        self,
        surface: Surface,
        rect: Rect,
        monster: Monster | None,
        in_focus: bool,
    ) -> None:
        surface.fill(TRANSPARENT_COLOR)

        filled = monster is not None
        border = self.slot_border.get_border(in_focus, filled)
        border.draw(surface)

        if not monster:
            return

        padding = self.scaling.scale_int(6)
        content = rect.inflate(-padding, -padding)

        upper_label = f"{monster.name}{monster.gender_symbol}"

        text_rect = rect.inflate(-padding, -padding)
        draw_text(
            surface,
            upper_label,
            text_rect,
            scaling=self.scaling,
            font=self.font,
        )

        text_rect.top = rect.bottom - self.scaling.scale_int(7)
        bottom_label = f"  Lv {monster.level}"
        draw_text(
            surface,
            bottom_label,
            text_rect,
            scaling=self.scaling,
            font=self.font,
        )

        hp_width = int(content.width * 0.35)
        hp_rect = Rect(0, 0, hp_width, self.scaling.scale_int(8))
        hp_rect.right = content.right
        hp_rect.centery = content.centery

        self.hp_bar.value = monster.hp_ratio
        self.hp_bar.draw(surface, hp_rect)

        self._draw_icons(surface, monster, rect)

    def _draw_icons(
        self,
        surface: Surface,
        monster: Monster,
        content: Rect,
    ) -> None:
        icon_y = content.top + self.scaling.scale_int(4)

        for i, status in enumerate(monster.status.get_statuses()):
            if status.icon:
                img = load_and_scale(status.icon)
                x = int(content.width * 0.45) + i * (
                    img.get_width() + self.scaling.scale_int(4)
                )
                x += content.left
                surface.blit(img, (x, icon_y))

        if monster.held_item:
            item_img = load_and_scale(monster.held_item.sprite, 1.5)
            x = int(content.width * 0.45) + len(
                monster.status.get_statuses()
            ) * (self.scaling.scale_int(4) + item_img.get_width())
            x += content.left
            surface.blit(item_img, (x, icon_y))
