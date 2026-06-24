from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, ClassVar

from pygame_menu.locals import ALIGN_CENTER, POSITION_EAST
from pygame_menu.menu import Menu
from pygame_menu.widgets.selection.highlight import HighlightSelection

from tuxemon.locale.locale import T
from tuxemon.menu.menu import PygameMenuState
from tuxemon.platform.const.graphics import BG_START_SCREEN
from tuxemon.tools import open_dialog

if False:
    from tuxemon.base_client import BaseClient


class MinigameState(PygameMenuState):
    """Jiu Jitsu trivia minigame."""

    name: ClassVar[str] = "MinigameState"

    ROUND_LIMITS = {
        "easy": 5,
        "normal": 7,
        "hard": 10,
        "nerd": 15,
    }

    SCORE_VALUES = {
        "easy": 1,
        "normal": 2,
        "hard": 3,
        "nerd": 5,
    }

    def __init__(
        self,
        client: "BaseClient",
        difficulty: str = "easy",
        streak: int = 0,
        score: int = 0,
        round_number: int = 1,
        asked_questions: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        width, height = client.context.resolution

        self.difficulty = difficulty
        self.streak = streak
        self.score = score
        self.round_number = round_number
        self.asked_questions = asked_questions or []
        self.max_rounds = self.ROUND_LIMITS.get(self.difficulty, 5)
        self.answer_locked = False

        super().__init__(client=client, height=height, width=width, **kwargs)

        theme = self._setup_theme(BG_START_SCREEN)
        theme.widget_font_color = (255, 255, 255)
        theme.widget_font_shadow = True
        theme.widget_font_shadow_color = (0, 0, 0)
        theme.widget_font_shadow_offset = 3
        theme.selection_color = (255, 255, 255)
        theme.scrollarea_position = POSITION_EAST
        theme.widget_alignment = ALIGN_CENTER
        self._menu_config["theme"] = theme

        self.add_menu_items(self.menu)
        self.reset_theme()

    def _load_questions(self) -> list[dict[str, Any]]:
        path = Path("mods/tuxemon/db/trivia.json")
        questions = json.loads(path.read_text(encoding="utf-8"))

        filtered = [
            question
            for question in questions
            if question.get("difficulty", "easy") == self.difficulty
        ]

        return filtered or questions

    def _question_id(self, question: dict[str, Any]) -> str:
        return question.get("id") or question["question"]

    def _choose_question(self, questions: list[dict[str, Any]]) -> dict[str, Any]:
        available = [
            question
            for question in questions
            if self._question_id(question) not in self.asked_questions
        ]

        if not available:
            self.asked_questions = []
            available = questions

        question = random.choice(available)
        self.asked_questions.append(self._question_id(question))
        return question

    def add_menu_items(self, menu: Menu) -> None:
        if self.round_number > self.max_rounds:
            self.show_final_screen(menu)
            return

        questions = self._load_questions()
        self.question = self._choose_question(questions)

        menu.add.vertical_margin(25)

        menu.add.label(
            title="Mat Trivia",
            label_id="question_title",
            font_size=self.font_type.big,
            align=ALIGN_CENTER,
            underline=True,
        )

        menu.add.label(
            title=(
                f"{self.difficulty.upper()} — "
                f"Round {self.round_number} of {self.max_rounds}"
            ),
            label_id="round_label",
            font_size=self.font_type.small,
            align=ALIGN_CENTER,
        )

        menu.add.vertical_margin(20)

        menu.add.label(
            title=self.question["question"],
            label_id="question",
            font_size=self.font_type.medium,
            align=ALIGN_CENTER,
            max_char=44,
            wordwrap=True,
        )

        menu.add.vertical_margin(18)

        choices = list(self.question["choices"])
        if self.question["correct"] not in choices:
            choices.append(self.question["correct"])

        random.shuffle(choices)

        for choice in choices:
            menu.add.button(
                choice,
                self.check_answer,
                choice,
                font_size=self.font_type.small,
                selection_effect=HighlightSelection(),
                align=ALIGN_CENTER,
            )

        menu.add.vertical_margin(18)

        menu.add.label(
            title=(
                f"{T.translate('score_label')}: {self.score}    "
                f"{T.translate('streak_label')}: {self.streak}"
            ),
            label_id="score_streak_label",
            font_size=self.font_type.medium,
            align=ALIGN_CENTER,
        )

    def show_final_screen(self, menu: Menu) -> None:
        menu.add.label(
            title="Trivia Complete",
            font_size=self.font_type.big,
            align=ALIGN_CENTER,
            underline=True,
        )

        menu.add.label(
            title=f"Difficulty: {self.difficulty.upper()}",
            font_size=self.font_type.medium,
            align=ALIGN_CENTER,
        )

        menu.add.label(
            title=f"Final Score: {self.score}",
            font_size=self.font_type.medium,
            align=ALIGN_CENTER,
        )

        menu.add.label(
            title=f"Final Streak: {self.streak}",
            font_size=self.font_type.medium,
            align=ALIGN_CENTER,
        )

        menu.add.button(
            "Play Again",
            lambda: self.client.replace_state(
                "MinigameState",
                difficulty=self.difficulty,
                streak=0,
                score=0,
                round_number=1,
                asked_questions=[],
            ),
            font_size=self.font_type.small,
            selection_effect=HighlightSelection(),
        )

        menu.add.button(
            "Exit",
            lambda: self.client.replace_state("StartState"),
            font_size=self.font_type.small,
            selection_effect=HighlightSelection(),
        )

    def check_answer(self, answer: str) -> None:
        if self.answer_locked:
            return

        self.answer_locked = True

        next_streak = self.streak
        next_score = self.score

        if answer == self.question["correct"]:
            next_streak += 1
            next_score += 1
        else:
            next_streak = 0
            open_dialog(
                self.client,
                [f"Wrong! Correct answer: {self.question['correct']}"],
                dialog_speed="max",
            )

        self.client.replace_state(
            "MinigameState",
            difficulty=self.difficulty,
            streak=next_streak,
            score=next_score,
            round_number=self.round_number + 1,
            asked_questions=list(self.asked_questions),
        )