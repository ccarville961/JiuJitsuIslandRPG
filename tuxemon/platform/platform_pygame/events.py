# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections.abc import Generator, Mapping
from dataclasses import dataclass, field
from typing import ClassVar

import pygame as pg
from pygame.event import Event
from pygame.joystick import JoystickType
from pygame.rect import Rect
from pygame.surface import Surface

from tuxemon import graphics
from tuxemon.platform.const import buttons, events
from tuxemon.platform.events import (
    EventQueueHandler,
    InputHandler,
    PlayerInput,
)
from tuxemon.session import local_session
from tuxemon.ui.draw import blit_alpha

logger = logging.getLogger(__name__)


def get_event_finger_id(event: object) -> int:
    """Return a compatible finger ID across pygame/SDL platforms."""
    finger_id = getattr(event, "finger_id", None)

    if finger_id is None:
        finger_id = getattr(event, "fingerid", None)

    if finger_id is None:
        finger_id = getattr(event, "touch_id", 0)

    try:
        return int(finger_id)
    except (TypeError, ValueError):
        return 0

HORIZONTAL_AXIS = 0
VERTICAL_AXIS = 1


class PygameEventQueueHandler(EventQueueHandler):
    """Handle all events from the pygame event queue."""

    def __init__(self) -> None:
        super().__init__()

    def process_events(self) -> Generator[PlayerInput, None, None]:
        for pg_event in pg.event.get():
            for input_handler in self.get_input_handlers():
                try:
                    input_handler.process_event(pg_event)
                except Exception:
                    logger.exception(
                        "Input handler %s failed while processing event %r",
                        type(input_handler).__name__,
                        pg_event,
                    )

            if pg_event.type == pg.QUIT:
                local_session.client.event_engine.execute_action("quit")

        for input_handler in self.get_input_handlers():
            for event in input_handler.get_events():
                if all(f(event) for f in self._filters):
                    yield event


class InputMappingStrategy:
    def map_button(self, raw_button_id: int) -> int | None:
        raise NotImplementedError

    def map_axis(self, axis_id: int, value: float) -> tuple[int | None, bool]:
        raise NotImplementedError


class XboxMapping(InputMappingStrategy):
    def map_button(self, raw_button_id: int) -> int | None:
        return {
            0: buttons.A,
            1: buttons.B,
            6: buttons.BACK,
            7: buttons.START,
            11: buttons.LEFT,
            12: buttons.RIGHT,
            13: buttons.UP,
            14: buttons.DOWN,
        }.get(raw_button_id)

    def map_axis(self, axis_id: int, value: float) -> tuple[int | None, bool]:
        if axis_id == HORIZONTAL_AXIS:
            return (
                buttons.RIGHT if value > 0 else buttons.LEFT,
                abs(value) > 0.25,
            )
        elif axis_id == VERTICAL_AXIS:
            return (
                buttons.DOWN if value > 0 else buttons.UP,
                abs(value) > 0.25,
            )
        return (None, False)


class PlayStationMapping(InputMappingStrategy):
    def map_button(self, raw_button_id: int) -> int | None:
        return {
            1: buttons.A,  # Cross
            2: buttons.B,  # Circle
            8: buttons.BACK,
            9: buttons.START,
            14: buttons.LEFT,
            15: buttons.RIGHT,
            12: buttons.UP,
            13: buttons.DOWN,
        }.get(raw_button_id)

    def map_axis(self, axis_id: int, value: float) -> tuple[int | None, bool]:
        if axis_id == HORIZONTAL_AXIS:
            return (
                buttons.RIGHT if value > 0 else buttons.LEFT,
                abs(value) > 0.2,
            )
        elif axis_id == VERTICAL_AXIS:
            return (
                buttons.DOWN if value > 0 else buttons.UP,
                abs(value) > 0.2,
            )
        return (None, False)


class KeyBindingRules:
    RESERVED_KEYS = {
        pg.K_ESCAPE,
        pg.K_RETURN,
        pg.K_BACKSPACE,
        pg.K_LSHIFT,
        pg.K_RSHIFT,
        pg.K_UP,
        pg.K_DOWN,
        pg.K_LEFT,
        pg.K_RIGHT,
    }

    @classmethod
    def is_valid_binding(cls, key: int) -> bool:
        return key not in cls.RESERVED_KEYS


class PygameEventHandler(InputHandler[Event]):
    """
    Input handler of Pygame events.
    """


class PygameGamepadInput(PygameEventHandler):
    """
    Gamepad event handler.

    NOTE: Due to implementation, you may receive "released" inputs for
    buttons/directions/axis even if they are released already. Pressed
    or held inputs will never be duplicated and are always "correct".

    Parameters:
        mapping_strategy: An InputMappingStrategy instance used to convert
            raw pygame identifiers (button indices, axis indices, hat values)
            into logical button identifiers used by the game.
    """

    def __init__(
        self,
        mapping_strategy: InputMappingStrategy,
        joysticks: list[JoystickType],
    ):
        super().__init__({})
        self.mapping = mapping_strategy
        self.joysticks = joysticks
        self.hat_state = (0, 0)
        self.axis_state = {HORIZONTAL_AXIS: 0, VERTICAL_AXIS: 0}

        for js in self.joysticks:
            try:
                # No js.init() here
                instance_id = js.get_instance_id()
                logger.info(f"Using joystick with instance ID {instance_id}")
            except Exception as e:
                logger.warning(f"Failed to access joystick instance ID: {e}")

    def _is_our_joystick(self, pg_event: Event) -> bool:
        return any(
            js.get_instance_id() == pg_event.joy for js in self.joysticks
        )

    def handle_button(
        self, button: int, pressed: bool, value: float = 0.0
    ) -> None:
        """
        Handles button press or release events.

        Parameters:
            button: The button identifier.
            pressed: True if the button is pressed, False if released.
            value: The analog value of the button (optional, defaults to 0.0).
        """
        logger.debug(
            f"{'Pressed' if pressed else 'Released'} {button} with value {value}"
        )
        if pressed:
            self.press(button, value)
        else:
            self.release(button)

    def process_event(self, input_event: Event) -> None:
        """
        Processes a pygame event.

        Parameters:
            input_event: The pygame event.
        """
        self.check_button(input_event)
        self.check_hat(input_event)
        self.handle_axis_event(input_event)

    def check_button(self, pg_event: Event) -> None:
        """
        Checks for button press/release events.

        Parameters:
            pg_event: The pygame event.
        """
        if pg_event.type in (pg.JOYBUTTONDOWN, pg.JOYBUTTONUP):
            if not self._is_our_joystick(pg_event):
                return

            button = self.mapping.map_button(pg_event.button)
            if button is not None:
                self.handle_button(button, pg_event.type == pg.JOYBUTTONDOWN)

    def check_hat(self, pg_event: Event) -> None:
        """
        Checks for hat switch motion events.

        Parameters:
            pg_event: The pygame event.
        """
        if pg_event.type == pg.JOYHATMOTION:
            if not self._is_our_joystick(pg_event):
                return

            x, y = pg_event.value
            prev_x, prev_y = self.hat_state
            self.hat_state = (x, y)

            if x != prev_x:
                self.handle_button(buttons.LEFT, x == -1)
                self.handle_button(buttons.RIGHT, x == 1)
                if prev_x == -1 and x != -1:
                    self.handle_button(buttons.LEFT, False)
                if prev_x == 1 and x != 1:
                    self.handle_button(buttons.RIGHT, False)

            if y != prev_y:
                self.handle_button(buttons.DOWN, y == 1)
                self.handle_button(buttons.UP, y == -1)
                if prev_y == 1 and y != 1:
                    self.handle_button(buttons.DOWN, False)
                if prev_y == -1 and y != -1:
                    self.handle_button(buttons.UP, False)

    def handle_axis_event(self, pg_event: Event) -> None:
        """
        Checks for axis motion events.

        Parameters:
            pg_event: The pygame event.
        """
        if pg_event.type == pg.JOYAXISMOTION:
            if not self._is_our_joystick(pg_event):
                return

            self._handle_axis(pg_event.axis, pg_event.value)

    def _handle_axis(self, axis: int, value: float) -> None:
        """Handles axis motion events."""
        button, pressed = self.mapping.map_axis(axis, value)
        if button is None:
            return

        # Determine direction: -1 (negative), 1 (positive), 0 (neutral)
        direction = 0
        if pressed:
            direction = 1 if value > 0 else -1

        # If direction hasn't changed, do nothing
        if self.axis_state[axis] == direction:
            return

        # Release previous direction
        if self.axis_state[axis] == -1:
            self.handle_button(
                buttons.LEFT if axis == HORIZONTAL_AXIS else buttons.UP, False
            )
        elif self.axis_state[axis] == 1:
            self.handle_button(
                buttons.RIGHT if axis == HORIZONTAL_AXIS else buttons.DOWN,
                False,
            )

        # Press new direction if applicable
        if direction != 0:
            self.handle_button(button, True, abs(value))

        # Update state
        self.axis_state[axis] = direction


class PygameKeyboardInput(PygameEventHandler):
    """
    Keyboard event handler.

    Parameters:
        event_map: Mapping of original identifiers to button identifiers.
    """

    default_input_map = {
        pg.K_UP: buttons.UP,
        pg.K_DOWN: buttons.DOWN,
        pg.K_LEFT: buttons.LEFT,
        pg.K_RIGHT: buttons.RIGHT,
        pg.K_RETURN: buttons.A,
        pg.K_RSHIFT: buttons.B,
        pg.K_LSHIFT: buttons.B,
        pg.K_ESCAPE: buttons.BACK,
        pg.K_BACKSPACE: events.BACKSPACE,
        None: events.UNICODE,
    }

    def __init__(
        self, event_map: Mapping[int | None, int] | None = None
    ) -> None:
        super().__init__(event_map or self.default_input_map)
        self._initialize_buttons_from_map(self.event_map)
        self._needs_rebuild: bool = False
        self._pending_map: Mapping[int | None, int] | None = None

    def update_state(self, dt: float) -> None:
        if self._needs_rebuild:
            assert self._pending_map is not None
            self.event_map = self._pending_map
            self._initialize_buttons_from_map(self._pending_map)
            self._needs_rebuild = False

        super().update_state(dt)

    def process_event(self, input_event: Event) -> None:
        """
        Processes a pygame event.

        Parameters:
            input_event: The pygame event.
        """
        pressed = input_event.type == pg.KEYDOWN
        released = input_event.type == pg.KEYUP

        if pressed or released:
            self._handle_key_event(input_event, pressed)

    def reload_mapping(self, new_map: Mapping[int | None, int]) -> None:
        """Update the key→button mapping in place."""
        self._pending_map = new_map
        self._needs_rebuild = True

    def _initialize_buttons_from_map(
        self, mapping: Mapping[int | None, int]
    ) -> None:
        """Ensure self.buttons matches the given mapping."""
        for button in mapping.values():
            if button not in self.buttons:
                self.buttons[button] = PlayerInput(button)

        for button in list(self.buttons.keys()):
            if button not in mapping.values():
                del self.buttons[button]

    def _handle_key_event(self, input_event: Event, pressed: bool) -> None:
        """Handles key press or release events."""
        try:
            button = self.event_map[input_event.key]
        except KeyError:
            self._handle_unicode_event(input_event, pressed)
        else:
            if pressed:
                self.press(button)
            else:
                self.release(button)

    def _handle_unicode_event(self, input_event: Event, pressed: bool) -> None:
        """Handles Unicode input events."""
        try:
            if pressed:
                self.release(events.UNICODE)
                self.press(events.UNICODE, input_event.unicode)
            else:
                self.release(events.UNICODE)
        except AttributeError:
            pass


# +-----------------------+
# |         UP            |
# |   +---------------+   |
# |   |               |   |
# | L |     GAP       | R |
# | E |   (dead zone) | I |
# | F |               | G |
# | T +---------------+ H |
# |         DOWN          |
# +-----------------------+


DPAD_IMAGE = "gfx/d-pad.png"
A_BUTTON_IMAGE = "gfx/a-button.png"
B_BUTTON_IMAGE = "gfx/b-button.png"
A_BUTTON_SCALE = 1.0
B_BUTTON_SCALE = 2.1
DPAD_GAP_RATIO = 0.2


@dataclass
class DPadRectsInfo:
    up: Rect = field(default_factory=lambda: Rect(0, 0, 0, 0))
    down: Rect = field(default_factory=lambda: Rect(0, 0, 0, 0))
    left: Rect = field(default_factory=lambda: Rect(0, 0, 0, 0))
    right: Rect = field(default_factory=lambda: Rect(0, 0, 0, 0))


@dataclass
class DPadInfo:
    surface: Surface = field(default_factory=lambda: Surface((0, 0)))
    position: tuple[int, int] = (0, 0)
    rect: DPadRectsInfo = field(default_factory=DPadRectsInfo)


@dataclass
class DPadButtonInfo:
    surface: Surface = field(default_factory=lambda: Surface((0, 0)))
    position: tuple[int, int] = (0, 0)
    rect: Rect = field(default_factory=lambda: Rect(0, 0, 0, 0))


class TouchOverlayUI:
    """Responsive landscape touch controls."""

    def __init__(
        self,
        transparency: int,
        resolution: tuple[int, int],
    ) -> None:
        # The old default of 45 is almost invisible on Android.
        self.transparency = max(175, min(255, transparency))
        self.resolution = resolution
        self.dpad = DPadInfo()
        self.a_button = DPadButtonInfo()
        self.b_button = DPadButtonInfo()
        self.load()

    def set_transparency(self, value: int) -> None:
        self.transparency = max(0, min(255, value))

    def ensure_layout(self, resolution: tuple[int, int]) -> None:
        """Rebuild controls when the real display size changes."""
        if tuple(resolution) != tuple(self.resolution):
            self.resolution = tuple(resolution)
            self.load()

    def load(self) -> None:
        """Create controls positioned against the real screen edges."""
        screen_width, screen_height = self.resolution

        if screen_width <= 0 or screen_height <= 0:
            return

        margin = max(14, int(screen_height * 0.045))

        # Landscape sizing: approximately one third of screen height.
        dpad_size = max(
            96,
            min(
                int(screen_height * 0.36),
                int(screen_width * 0.19),
            ),
        )

        button_size = max(58, int(dpad_size * 0.56))
        button_gap = max(14, int(button_size * 0.25))

        raw_dpad = graphics.load_and_scale(DPAD_IMAGE)
        raw_a = graphics.load_and_scale(A_BUTTON_IMAGE)
        raw_b = graphics.load_and_scale(B_BUTTON_IMAGE)

        dpad_surface = pg.transform.scale(
            raw_dpad,
            (dpad_size, dpad_size),
        )

        a_surface = pg.transform.scale(
            raw_a,
            (button_size, button_size),
        )

        b_surface = pg.transform.scale(
            raw_b,
            (button_size, button_size),
        )

        dpad_x = margin
        dpad_y = screen_height - margin - dpad_size

        third = dpad_size // 3
        half = dpad_size // 2

        dpad_rects = DPadRectsInfo(
            up=Rect(
                dpad_x + third,
                dpad_y,
                third,
                half,
            ),
            down=Rect(
                dpad_x + third,
                dpad_y + half,
                third,
                dpad_size - half,
            ),
            left=Rect(
                dpad_x,
                dpad_y + third,
                half,
                third,
            ),
            right=Rect(
                dpad_x + half,
                dpad_y + third,
                dpad_size - half,
                third,
            ),
        )

        self.dpad = DPadInfo(
            surface=dpad_surface,
            position=(dpad_x, dpad_y),
            rect=dpad_rects,
        )

        button_y = screen_height - margin - button_size
        a_x = screen_width - margin - button_size
        b_x = a_x - button_gap - button_size

        self.a_button = DPadButtonInfo(
            surface=a_surface,
            position=(a_x, button_y),
            rect=Rect(
                a_x,
                button_y,
                button_size,
                button_size,
            ),
        )

        self.b_button = DPadButtonInfo(
            surface=b_surface,
            position=(b_x, button_y),
            rect=Rect(
                b_x,
                button_y,
                button_size,
                button_size,
            ),
        )

    def draw(self, screen: Surface) -> None:
        """Draw controls using the actual display surface size."""
        self.ensure_layout(screen.get_size())

        blit_alpha(
            screen,
            self.dpad.surface,
            self.dpad.position,
            self.transparency,
        )

        blit_alpha(
            screen,
            self.a_button.surface,
            self.a_button.position,
            self.transparency,
        )

        blit_alpha(
            screen,
            self.b_button.surface,
            self.b_button.position,
            self.transparency,
        )


class PygameTouchOverlayInput(PygameEventHandler):
    """Responsive touch controls for Android and emulator testing."""

    default_input_map: ClassVar[Mapping[int | None, int]] = {}

    def __init__(
        self,
        transparency: int,
        resolution: tuple[int, int],
    ) -> None:
        super().__init__({})

        self.ui = TouchOverlayUI(
            transparency,
            resolution,
        )

        self.buttons = {
            buttons.UP: PlayerInput(buttons.UP),
            buttons.DOWN: PlayerInput(buttons.DOWN),
            buttons.LEFT: PlayerInput(buttons.LEFT),
            buttons.RIGHT: PlayerInput(buttons.RIGHT),
            buttons.A: PlayerInput(buttons.A),
            buttons.B: PlayerInput(buttons.B),
            buttons.START: PlayerInput(buttons.START),
        }

        self._active_touches: dict[int, int] = {}

    def load(self) -> None:
        self.ui.load()

    def _normalised_touch_position(
        self,
        input_event: Event,
    ) -> tuple[int, int] | None:
        x = getattr(input_event, "x", None)
        y = getattr(input_event, "y", None)

        if x is None or y is None:
            return None

        try:
            x_value = float(x)
            y_value = float(y)
        except (TypeError, ValueError):
            return None

        width, height = self.ui.resolution

        return (
            int(x_value * width),
            int(y_value * height),
        )

    def process_event(self, input_event: Event) -> None:
        """Handle real touch input and emulator mouse input."""

        if input_event.type in (
            pg.FINGERDOWN,
            pg.FINGERUP,
            pg.FINGERMOTION,
        ):
            finger_id = get_event_finger_id(input_event)

            if input_event.type == pg.FINGERUP:
                self._handle_release(finger_id)
                return

            position = self._normalised_touch_position(input_event)

            if position is None:
                return

            if input_event.type == pg.FINGERDOWN:
                self._handle_press(finger_id, position)
            else:
                self._handle_motion(finger_id, position)

            return

        # Android Emulator commonly converts mouse clicks into mouse events.
        if input_event.type == pg.MOUSEBUTTONDOWN:
            if getattr(input_event, "button", 0) == 1:
                self._handle_press(
                    -1,
                    tuple(input_event.pos),
                )
            return

        if input_event.type == pg.MOUSEBUTTONUP:
            if getattr(input_event, "button", 0) == 1:
                self._handle_release(-1)
            return

        if input_event.type == pg.MOUSEMOTION:
            if -1 in self._active_touches:
                self._handle_motion(
                    -1,
                    tuple(input_event.pos),
                )

    def _handle_press(
        self,
        pointer_id: int,
        position: tuple[int, int],
    ) -> None:
        button = self.get_touched_button(position)

        if button is None:
            return

        old_button = self._active_touches.get(pointer_id)

        if old_button is not None and old_button != button:
            self._active_touches.pop(pointer_id, None)

            if old_button not in self._active_touches.values():
                self.release(old_button)

        if button not in self._active_touches.values():
            self.press(button)

        self._active_touches[pointer_id] = button

        logger.info(
            "Mobile control pressed: %s at %s",
            button,
            position,
        )

    def _handle_release(self, pointer_id: int) -> None:
        button = self._active_touches.pop(pointer_id, None)

        if button is None:
            return

        if button not in self._active_touches.values():
            self.release(button)

        logger.info("Mobile control released: %s", button)

    def _handle_motion(
        self,
        pointer_id: int,
        position: tuple[int, int],
    ) -> None:
        old_button = self._active_touches.get(pointer_id)
        new_button = self.get_touched_button(position)

        if old_button == new_button:
            return

        if old_button is not None:
            self._active_touches.pop(pointer_id, None)

            if old_button not in self._active_touches.values():
                self.release(old_button)

        if new_button is not None:
            if new_button not in self._active_touches.values():
                self.press(new_button)

            self._active_touches[pointer_id] = new_button

    def get_touched_button(
        self,
        position: tuple[int, int],
    ) -> int | None:
        controls = (
            (buttons.UP, self.ui.dpad.rect.up),
            (buttons.DOWN, self.ui.dpad.rect.down),
            (buttons.LEFT, self.ui.dpad.rect.left),
            (buttons.RIGHT, self.ui.dpad.rect.right),
            (buttons.A, self.ui.a_button.rect),
            (buttons.START, self.ui.b_button.rect),
        )

        for button, rect in controls:
            if rect.collidepoint(position):
                return button

        return None

    def draw(self, screen: Surface) -> None:
        self.ui.draw(screen)


class PygameMouseInput(PygameEventHandler):
    """
    Mouse event handler.

    Parameters:
        event_map: Mapping of original identifiers to button identifiers.
    """

    default_input_map = {
        pg.MOUSEBUTTONDOWN: buttons.MOUSELEFT,
        pg.MOUSEBUTTONUP: buttons.MOUSELEFT,
    }

    def process_event(self, pg_event: Event) -> None:
        if pg_event.type == pg.MOUSEBUTTONDOWN:
            self.press(buttons.MOUSELEFT, pg_event.pos)
        elif pg_event.type == pg.MOUSEBUTTONUP:
            self.release(buttons.MOUSELEFT)
