#!/usr/bin/env python3

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "mods/tuxemon/maps/flower_city.tmx"

NPC_SLUG = "jji_flower_city_blackbelt_officer"

CLOSED_POSITION = (37, 17)
OPEN_POSITION = (37, 19)

# New variable name deliberately ignores the previous automatic test state.
GATE_VARIABLE = "jji_flower_city_route5_manual_gate:open"
LEGACY_GATE_VARIABLE = "jji_flower_city_route5_blackbelt_gate:open"

PREFIX = "JJI Flower City Manual Black Belt Gate"


def fail(message: str) -> None:
    raise SystemExit(f"\nERROR: {message}\n")


def add_property(
    properties: ET.Element,
    name: str,
    value: str,
) -> None:
    ET.SubElement(
        properties,
        "property",
        {
            "name": name,
            "value": value,
        },
    )


def get_event_group(root: ET.Element) -> ET.Element:
    for group in root.findall("objectgroup"):
        if group.get("name", "").strip().lower() == "events":
            return group

    existing_ids = [
        int(group.get("id", "0"))
        for group in root.findall("objectgroup")
        if group.get("id", "").isdigit()
    ]

    return ET.SubElement(
        root,
        "objectgroup",
        {
            "id": str(max(existing_ids or [0]) + 1),
            "name": "Events",
        },
    )


def next_object_id(root: ET.Element) -> int:
    ids = [
        int(obj.get("id", "0"))
        for obj in root.findall(".//object")
        if obj.get("id", "").isdigit()
    ]

    return max(ids or [0]) + 1


def remove_old_gate_events(group: ET.Element) -> int:
    removed = 0

    old_prefixes = (
        "JJI Flower City Black Belt Gate",
        "JJI Flower City Manual Black Belt Gate",
    )

    for obj in list(group.findall("object")):
        name = obj.get("name", "")

        values = [
            prop.get("value", "")
            for prop in obj.findall("./properties/property")
        ]

        generated_event = name.startswith(old_prefixes)

        controls_this_officer = any(
            NPC_SLUG in value
            for value in values
        )

        if generated_event or controls_this_officer:
            group.remove(obj)
            removed += 1

    return removed


def add_event(
    group: ET.Element,
    object_id: int,
    name: str,
    tile_x: int,
    tile_y: int,
    *,
    actions: list[str],
    conditions: list[str] | None = None,
    behaviours: list[str] | None = None,
    tile_size: int = 16,
) -> int:
    obj = ET.SubElement(
        group,
        "object",
        {
            "id": str(object_id),
            "name": f"{PREFIX} - {name}",
            "type": "event",
            "x": str(tile_x * tile_size),
            "y": str(tile_y * tile_size),
            "width": str(tile_size),
            "height": str(tile_size),
        },
    )

    props = ET.SubElement(obj, "properties")

    for index, action in enumerate(actions, start=1):
        add_property(
            props,
            f"act{index * 10:03d}",
            action,
        )

    for index, condition in enumerate(
        conditions or [],
        start=1,
    ):
        add_property(
            props,
            f"cond{index * 10:03d}",
            condition,
        )

    for index, behaviour in enumerate(
        behaviours or [],
        start=1,
    ):
        add_property(
            props,
            f"behav{index * 10:03d}",
            behaviour,
        )

    return object_id + 1


def main() -> None:
    if not MAP.exists():
        fail(f"Map not found: {MAP}")

    tree = ET.parse(MAP)
    root = tree.getroot()

    tile_width = int(root.get("tilewidth", "16"))
    tile_height = int(root.get("tileheight", "16"))

    if tile_width != tile_height:
        fail(
            f"Expected square tiles, found "
            f"{tile_width}x{tile_height}."
        )

    map_width = int(root.get("width", "0"))
    map_height = int(root.get("height", "0"))

    for label, (x, y) in {
        "closed position": CLOSED_POSITION,
        "open position": OPEN_POSITION,
    }.items():
        if not (
            0 <= x < map_width
            and 0 <= y < map_height
        ):
            fail(
                f"{label} {(x, y)} is outside "
                f"the {map_width}x{map_height} map."
            )

    events = get_event_group(root)

    removed = remove_old_gate_events(events)
    print(f"Removed old officer events: {removed}")

    object_id = next_object_id(root)

    # --------------------------------------------------------
    # Spawn in the blocking position until manually approved.
    # --------------------------------------------------------

    object_id = add_event(
        events,
        object_id,
        "Spawn Closed Officer",
        0,
        0,
        actions=[
            (
                f"create_npc {NPC_SLUG},"
                f"{CLOSED_POSITION[0]},"
                f"{CLOSED_POSITION[1]},stand"
            ),
            f"char_face {NPC_SLUG},down",
        ],
        conditions=[
            f"not variable_set {GATE_VARIABLE}",
            f"not char_exists {NPC_SLUG}",
        ],
        tile_size=tile_width,
    )

    # --------------------------------------------------------
    # Spawn in the open position after approval.
    # --------------------------------------------------------

    object_id = add_event(
        events,
        object_id,
        "Spawn Open Officer",
        0,
        0,
        actions=[
            (
                f"create_npc {NPC_SLUG},"
                f"{OPEN_POSITION[0]},"
                f"{OPEN_POSITION[1]},stand"
            ),
            f"char_face {NPC_SLUG},down",
        ],
        conditions=[
            f"is variable_set {GATE_VARIABLE}",
            f"not char_exists {NPC_SLUG}",
        ],
        tile_size=tile_width,
    )

    # --------------------------------------------------------
    # Manual refusal dialogue.
    #
    # This event cannot run automatically because it requires
    # the talk behaviour.
    # --------------------------------------------------------

    object_id = add_event(
        events,
        object_id,
        "Blocked Talk",
        CLOSED_POSITION[0],
        CLOSED_POSITION[1],
        actions=[
            f"char_face {NPC_SLUG},player",
            (
                "translated_dialog "
                "jji_flower_city_blackbelt_blocked"
            ),
        ],
        conditions=[
            "not has_item player,black_belt",
            f"not variable_set {GATE_VARIABLE}",
        ],
        behaviours=[
            f"talk {NPC_SLUG}",
        ],
        tile_size=tile_width,
    )

    # --------------------------------------------------------
    # Manual Black Belt approval.
    #
    # The important correction is:
    #   is has_item player,black_belt
    #
    # The officer only moves after the player talks to him.
    # --------------------------------------------------------

    object_id = add_event(
        events,
        object_id,
        "Approve Black Belt Talk",
        CLOSED_POSITION[0],
        CLOSED_POSITION[1],
        actions=[
            f"char_face {NPC_SLUG},player",
            (
                "translated_dialog "
                "jji_flower_city_blackbelt_confirmed"
            ),
            f"char_move {NPC_SLUG},down 2",
            f"char_face {NPC_SLUG},down",
            f"set_variable {GATE_VARIABLE}",
            f"set_variable {LEGACY_GATE_VARIABLE}",
        ],
        conditions=[
            "is has_item player,black_belt",
            f"not variable_set {GATE_VARIABLE}",
        ],
        behaviours=[
            f"talk {NPC_SLUG}",
        ],
        tile_size=tile_width,
    )

    # --------------------------------------------------------
    # Manual dialogue after the officer has moved.
    # --------------------------------------------------------

    object_id = add_event(
        events,
        object_id,
        "Open Talk",
        OPEN_POSITION[0],
        OPEN_POSITION[1],
        actions=[
            f"char_face {NPC_SLUG},player",
            (
                "translated_dialog "
                "jji_flower_city_blackbelt_open"
            ),
        ],
        conditions=[
            f"is variable_set {GATE_VARIABLE}",
        ],
        behaviours=[
            f"talk {NPC_SLUG}",
        ],
        tile_size=tile_width,
    )

    current_next_id = int(root.get("nextobjectid", "1"))

    root.set(
        "nextobjectid",
        str(max(current_next_id, object_id)),
    )

    ET.indent(tree, space=" ", level=0)

    tree.write(
        MAP,
        encoding="UTF-8",
        xml_declaration=True,
    )

    # Confirm the written map remains valid.
    ET.parse(MAP)

    print()
    print(f"Updated: {MAP}")
    print(f"Officer blocks at: {CLOSED_POSITION}")
    print(f"Officer moves to: {OPEN_POSITION}")
    print(f"Gate variable: {GATE_VARIABLE}")
    print()
    print("The officer now moves only after manual dialogue.")


if __name__ == "__main__":
    main()
