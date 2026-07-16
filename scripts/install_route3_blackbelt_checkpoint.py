#!/usr/bin/env python3
from __future__ import annotations

import copy
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml


MAP = Path("mods/tuxemon/maps/route3.tmx")
NPC_DIR = Path("mods/tuxemon/db/npc")
PO = Path("mods/tuxemon/l18n/en_US/LC_MESSAGES/base.po")

PREFIX = "JJI Route 3 Black Belt Checkpoint"
OFFICER = "jji_route3_blackbelt_checkpoint_officer"

BLACK_BELT = "black_belt_contract"
GATE_OPEN = "jji_route3_blackbelt_checkpoint_open:yes"

# Beside the red flowers, blocking the eastern route.
CLOSED = (13, 6)

# Officer moves north after approving passage.
OPENED = (13, 5)

DIALOGUE = {
    OFFICER: "Black Belt Officer",

    "jji_route3_blackbelt_checkpoint_blocked": (
        "Officer: This route is restricted to Black Belts.\n"
        "Return after completing your assessment."
    ),

    "jji_route3_blackbelt_checkpoint_approved": (
        "Officer: You defeated Coach Toland and Coach Hill?\n"
        "Outstanding work. Your Black Belt status is confirmed.\n"
        "You may proceed."
    ),

    "jji_route3_blackbelt_checkpoint_open": (
        "Officer: The route is open.\n"
        "Good luck with the next stage of your journey."
    ),
}


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def load_yaml(path: Path) -> dict:
    if not path.exists():
        fail(f"Missing YAML file: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        fail(f"{path} is not a YAML mapping.")

    return data


def save_yaml(path: Path, data: dict) -> None:
    path.write_text(
        yaml.safe_dump(
            data,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def create_officer_definition() -> None:
    sources = (
        "jji_mansion_gate_officer_left",
        "jji_mansion_gate_officer_right",
        "jji_toland_stair_officer_left",
        "jji_blackbelt_dojo_stair_officer_left",
    )

    source = None

    for slug in sources:
        candidate = NPC_DIR / f"{slug}.yaml"

        if candidate.exists():
            source = candidate
            break

    if source is None:
        fail("Could not find an existing officer NPC to clone.")

    data = copy.deepcopy(load_yaml(source))
    data["slug"] = OFFICER

    if "speech" in data:
        data["speech"] = {
            "profile": {
                "default": {}
            }
        }

    target = NPC_DIR / f"{OFFICER}.yaml"
    save_yaml(target, data)

    template = data.get("template", {})

    print(
        f"Created {OFFICER} from {source.name}; "
        f"sprite="
        f"{template.get('sprite_name') if isinstance(template, dict) else None}"
    )


def events_layer(root: ET.Element) -> ET.Element:
    for group in root.findall("objectgroup"):
        if group.get("name", "").lower() == "events":
            return group

    fail("route3.tmx has no Events layer.")


def add_event(
    events: ET.Element,
    object_id: int,
    *,
    name: str,
    x: int,
    y: int,
    width: int,
    height: int,
    actions: list[str],
    conditions: list[str],
    behaviours: list[str] | None = None,
) -> int:
    obj = ET.SubElement(
        events,
        "object",
        {
            "id": str(object_id),
            "name": name,
            "type": "event",
            "x": str(x),
            "y": str(y),
            "width": str(width),
            "height": str(height),
        },
    )

    props = ET.SubElement(obj, "properties")

    for index, action in enumerate(actions, start=1):
        ET.SubElement(
            props,
            "property",
            {
                "name": f"act{index * 10}",
                "value": action,
            },
        )

    for index, behaviour in enumerate(behaviours or (), start=1):
        ET.SubElement(
            props,
            "property",
            {
                "name": f"behav{index * 10}",
                "value": behaviour,
            },
        )

    for index, condition in enumerate(conditions, start=1):
        ET.SubElement(
            props,
            "property",
            {
                "name": f"cond{index * 10}",
                "value": condition,
            },
        )

    return object_id + 1


def po_quote(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
    )
    return f'"{escaped}"'


def set_po_entry(
    lines: list[str],
    key: str,
    value: str,
) -> None:
    msgid = f'msgid "{key}"'
    replacement = f"msgstr {po_quote(value)}"

    matches = [
        index
        for index, line in enumerate(lines)
        if line == msgid
    ]

    if len(matches) > 1:
        fail(f"Duplicate PO entries found for {key}")

    if not matches:
        if lines and lines[-1] != "":
            lines.append("")

        lines.extend(
            [
                "# JJI Route 3 Black Belt checkpoint",
                msgid,
                replacement,
                "",
            ]
        )
        return

    msgid_index = matches[0]
    msgstr_index = msgid_index + 1

    while (
        msgstr_index < len(lines)
        and not lines[msgstr_index].startswith("msgstr ")
    ):
        msgstr_index += 1

    if msgstr_index >= len(lines):
        fail(f"No msgstr found for {key}")

    end = msgstr_index + 1

    while end < len(lines) and lines[end].startswith('"'):
        end += 1

    lines[msgstr_index:end] = [replacement]


if not MAP.exists():
    fail(f"Missing map: {MAP}")

if not PO.exists():
    fail(f"Missing catalogue: {PO}")

if not (Path("mods/tuxemon/db/item") / f"{BLACK_BELT}.yaml").exists():
    fail(f"Missing Black Belt item: {BLACK_BELT}")

create_officer_definition()

backup = MAP.with_suffix(
    ".tmx.bak-before-route3-blackbelt-checkpoint"
)

if not backup.exists():
    shutil.copy2(MAP, backup)
    print("Created backup:", backup)

tree = ET.parse(MAP)
root = tree.getroot()
events = events_layer(root)

# Remove only previous copies of this checkpoint.
for obj in list(events.findall("object")):
    name = obj.get("name", "")

    values = [
        prop.get("value", "")
        for prop in obj.findall("./properties/property")
    ]

    if (
        name.startswith(PREFIX)
        or any(OFFICER in value for value in values)
    ):
        events.remove(obj)

map_width = (
    int(root.get("width", "1"))
    * int(root.get("tilewidth", "16"))
)

map_height = (
    int(root.get("height", "1"))
    * int(root.get("tileheight", "16"))
)

object_ids = [
    int(obj.get("id", "0"))
    for group in root.findall("objectgroup")
    for obj in group.findall("object")
]

next_id = max(object_ids, default=0) + 1

closed_x, closed_y = CLOSED
open_x, open_y = OPENED

# Closed-state spawn, active across the entire map.
next_id = add_event(
    events,
    next_id,
    name=f"{PREFIX} - Closed Spawn",
    x=0,
    y=0,
    width=map_width,
    height=map_height,
    actions=[
        (
            f"create_npc {OFFICER},"
            f"{closed_x},{closed_y},stand"
        ),
        f"char_face {OFFICER},left",
    ],
    conditions=[
        f"not char_exists {OFFICER}",
        f"not variable_set {GATE_OPEN}",
    ],
)

# Refuse the player without the Black Belt.
next_id = add_event(
    events,
    next_id,
    name=f"{PREFIX} - Refuse Entry",
    x=closed_x * 16,
    y=closed_y * 16,
    width=16,
    height=16,
    actions=[
        f"char_face {OFFICER},player",
        (
            "translated_dialog "
            "jji_route3_blackbelt_checkpoint_blocked"
        ),
    ],
    conditions=[
        f"not variable_set {GATE_OPEN}",
        f"not has_item player,{BLACK_BELT}",
    ],
    behaviours=[
        f"talk {OFFICER}",
    ],
)

# Approve a player carrying the Black Belt.
next_id = add_event(
    events,
    next_id,
    name=f"{PREFIX} - Approve Entry",
    x=closed_x * 16,
    y=closed_y * 16,
    width=16,
    height=16,
    actions=[
        f"char_face {OFFICER},player",
        (
            "translated_dialog "
            "jji_route3_blackbelt_checkpoint_approved"
        ),
        f"char_move {OFFICER},up 1",
        f"char_face {OFFICER},down",
        f"set_variable {GATE_OPEN}",
    ],
    conditions=[
        f"not variable_set {GATE_OPEN}",
        f"is has_item player,{BLACK_BELT}",
        f"is char_exists {OFFICER}",
    ],
    behaviours=[
        f"talk {OFFICER}",
    ],
)

# Open-state spawn after returning to the map.
next_id = add_event(
    events,
    next_id,
    name=f"{PREFIX} - Open Spawn",
    x=0,
    y=0,
    width=map_width,
    height=map_height,
    actions=[
        (
            f"create_npc {OFFICER},"
            f"{open_x},{open_y},stand"
        ),
        f"char_face {OFFICER},down",
    ],
    conditions=[
        f"not char_exists {OFFICER}",
        f"is variable_set {GATE_OPEN}",
    ],
)

next_id = add_event(
    events,
    next_id,
    name=f"{PREFIX} - Open Talk",
    x=open_x * 16,
    y=open_y * 16,
    width=16,
    height=16,
    actions=[
        f"char_face {OFFICER},player",
        (
            "translated_dialog "
            "jji_route3_blackbelt_checkpoint_open"
        ),
    ],
    conditions=[
        f"is variable_set {GATE_OPEN}",
    ],
    behaviours=[
        f"talk {OFFICER}",
    ],
)

root.set("nextobjectid", str(next_id))

ET.indent(tree, space=" ", level=0)

tree.write(
    MAP,
    encoding="UTF-8",
    xml_declaration=True,
)

ET.parse(MAP)

lines = PO.read_text(encoding="utf-8").splitlines()

for key, value in DIALOGUE.items():
    set_po_entry(lines, key, value)

PO.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)

print()
print("Route 3 Black Belt checkpoint installed.")
print("Closed position:", CLOSED)
print("Open position:", OPENED)
