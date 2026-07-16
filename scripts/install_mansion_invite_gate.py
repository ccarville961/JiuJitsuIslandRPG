#!/usr/bin/env python3
from __future__ import annotations

import copy
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml


ROOT = Path.cwd()

MAP = ROOT / "mods/tuxemon/maps/routea.tmx"
NPC_DIR = ROOT / "mods/tuxemon/db/npc"
PO = ROOT / "mods/tuxemon/l18n/en_US/LC_MESSAGES/base.po"
CONDITION_DIR = ROOT / "tuxemon/event/conditions"

PATCH_PREFIX = "JJI Mansion Invitation Gate"

ITEM = "mansion_invitation"
GATE_OPEN = "jji_mansion_gate_open:yes"

LEFT = "jji_mansion_gate_officer_left"
RIGHT = "jji_mansion_gate_officer_right"

# The two routea Mansion entrance tiles from your output.
ENTRANCE_PIXELS = {
    (96, 192),
    (112, 192),
}

# Officers block tiles immediately below the two entrances.
CLOSED_POSITIONS = {
    LEFT: (6, 19),
    RIGHT: (7, 19),
}

# After accepting the invitation, they step outward.
OPEN_POSITIONS = {
    LEFT: (5, 19),
    RIGHT: (8, 19),
}

DIALOGUE = {
    "jji_mansion_gate_no_invite": (
        "Officer: This path is restricted.\n"
        "Only competitors with a Mansion Invitation may pass."
    ),
    "jji_mansion_gate_invite": (
        "Officer: You defeated Coach Toland and Coach Hill?\n"
        "That is an incredible achievement.\n"
        "Your invitation is valid. Please proceed."
    ),
    "jji_mansion_gate_open": (
        "Officer: Welcome, champion.\n"
        "The Mansion is waiting for you."
    ),
}


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        fail(f"Missing YAML file: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        fail(f"{path} is not a YAML mapping.")

    return data


def save_yaml(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(
            data,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def clone_officer(
    target_slug: str,
    candidates: tuple[str, ...],
) -> None:
    source = None

    for candidate_slug in candidates:
        candidate = NPC_DIR / f"{candidate_slug}.yaml"

        if candidate.exists():
            source = candidate
            break

    if source is None:
        fail(
            f"Could not find an officer source for {target_slug}.\n"
            f"Tried: {', '.join(candidates)}"
        )

    data = copy.deepcopy(load_yaml(source))
    data["slug"] = target_slug

    if "speech" in data:
        data["speech"] = {
            "profile": {
                "default": {}
            }
        }

    destination = NPC_DIR / f"{target_slug}.yaml"
    save_yaml(destination, data)

    template = data.get("template", {})

    print(
        f"{target_slug} <- {source.name}; "
        f"sprite="
        f"{template.get('sprite_name') if isinstance(template, dict) else None}"
    )


def detect_item_condition() -> tuple[str, str]:
    """
    Detect the installed engine's inventory condition and return:
      - player has Mansion Invitation
      - player does not have Mansion Invitation
    """

    preferred = (
        "has_item",
        "item_in_inventory",
        "player_has_item",
        "has_item_quantity",
    )

    for condition_name in preferred:
        source = CONDITION_DIR / f"{condition_name}.py"

        if not source.exists():
            continue

        text = source.read_text(
            encoding="utf-8",
            errors="replace",
        )

        # Detect the condition's parameter declaration where possible.
        if re.search(
            r"\b(character|character_slug|char_slug)\b",
            text,
            flags=re.IGNORECASE,
        ):
            positive = f"{condition_name} player,{ITEM}"
        else:
            positive = f"{condition_name} {ITEM}"

        print(
            "Detected item condition:",
            source.name,
        )

        return positive, f"not {positive}"

    possible = []

    for source in sorted(CONDITION_DIR.glob("*.py")):
        text = source.read_text(
            encoding="utf-8",
            errors="replace",
        ).lower()

        if "inventory" in text or "item" in text:
            possible.append(source.name)

    fail(
        "Could not detect the inventory condition.\n"
        "Possible condition modules:\n  "
        + "\n  ".join(possible)
        + "\n\nRun:\n"
        "ls tuxemon/event/conditions | grep -Ei 'item|inventory'"
    )


def events_layer(root: ET.Element) -> ET.Element:
    for group in root.findall("objectgroup"):
        if group.get("name", "").lower() == "events":
            return group

    fail("routea.tmx has no Events layer.")


def properties(obj: ET.Element) -> ET.Element:
    result = obj.find("properties")

    if result is None:
        result = ET.SubElement(obj, "properties")

    return result


def values(obj: ET.Element) -> list[str]:
    return [
        prop.get("value", "")
        for prop in obj.findall("./properties/property")
    ]


def add_condition(
    obj: ET.Element,
    condition: str,
) -> None:
    props = properties(obj)

    existing = [
        prop.get("value", "")
        for prop in props.findall("property")
        if re.fullmatch(
            r"cond\d+",
            prop.get("name", ""),
        )
    ]

    if condition in existing:
        return

    numbers = []

    for prop in props.findall("property"):
        match = re.fullmatch(
            r"cond(\d+)",
            prop.get("name", ""),
        )

        if match:
            numbers.append(int(match.group(1)))

    ET.SubElement(
        props,
        "property",
        {
            "name": f"cond{max(numbers, default=0) + 10}",
            "value": condition,
        },
    )


def add_event(
    events: ET.Element,
    object_id: int,
    *,
    name: str,
    x: int,
    y: int,
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
            "width": "16",
            "height": "16",
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

    for index, behaviour in enumerate(
        behaviours or (),
        start=1,
    ):
        ET.SubElement(
            props,
            "property",
            {
                "name": f"behav{index * 10}",
                "value": behaviour,
            },
        )

    for index, condition in enumerate(
        conditions,
        start=1,
    ):
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
    msgstr = f"msgstr {po_quote(value)}"

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
                "# JJI Mansion invitation gate",
                msgid,
                msgstr,
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

    lines[msgstr_index:end] = [msgstr]


if not MAP.exists():
    fail(f"Missing map: {MAP}")

if not PO.exists():
    fail(f"Missing translation catalogue: {PO}")

has_invite, no_invite = detect_item_condition()

print("Has-invitation condition:", has_invite)
print("No-invitation condition:", no_invite)


# ------------------------------------------------------------------
# Create the two officer NPC records.
# ------------------------------------------------------------------

officer_sources = (
    "jji_toland_stair_officer_left",
    "jji_toland_stair_officer_right",
    "jji_blackbelt_dojo_stair_officer_left",
    "jji_blackbelt_dojo_stair_officer_right",
)

clone_officer(LEFT, officer_sources)
clone_officer(RIGHT, officer_sources)


# ------------------------------------------------------------------
# Patch routea.tmx.
# ------------------------------------------------------------------

backup = MAP.with_suffix(
    ".tmx.bak-before-mansion-invitation-gate"
)

if not backup.exists():
    shutil.copy2(MAP, backup)
    print("Created backup:", backup)

tree = ET.parse(MAP)
root = tree.getroot()
events = events_layer(root)

# Remove a previous installation of this feature.
for obj in list(events.findall("object")):
    if obj.get("name", "").startswith(PATCH_PREFIX):
        events.remove(obj)


# Find exactly the two Mansion entrance teleports.
entrances = []

for obj in events.findall("object"):
    position = (
        int(float(obj.get("x", "0"))),
        int(float(obj.get("y", "0"))),
    )

    obj_values = values(obj)

    is_mansion_teleport = any(
        value.startswith(
            "transition_teleport player,mansion.tmx,"
        )
        for value in obj_values
    )

    if position in ENTRANCE_PIXELS and is_mansion_teleport:
        entrances.append(obj)

if len(entrances) != 2:
    fail(
        "Expected the two routea Mansion entrances at "
        "(96,192) and (112,192), "
        f"but found {len(entrances)}."
    )


# The teleport cannot fire before the officers approve entry.
for entrance in entrances:
    add_condition(
        entrance,
        f"is variable_set {GATE_OPEN}",
    )


all_ids = [
    int(obj.get("id", "0"))
    for group in root.findall("objectgroup")
    for obj in group.findall("object")
]

next_id = max(all_ids, default=0) + 1

officers = (
    LEFT,
    RIGHT,
)


# Closed-state officer spawns.
for index, slug in enumerate(officers, start=1):
    x, y = CLOSED_POSITIONS[slug]

    next_id = add_event(
        events,
        next_id,
        name=f"{PATCH_PREFIX} - Closed Spawn {index}",
        x=0,
        y=0,
        actions=[
            f"create_npc {slug},{x},{y},stand",
            f"char_face {slug},down",
        ],
        conditions=[
            f"not char_exists {slug}",
            f"not variable_set {GATE_OPEN}",
        ],
    )


# Refusal dialogue without an invitation.
for index, slug in enumerate(officers, start=1):
    x, y = CLOSED_POSITIONS[slug]

    next_id = add_event(
        events,
        next_id,
        name=f"{PATCH_PREFIX} - Refuse Entry {index}",
        x=x * 16,
        y=y * 16,
        actions=[
            f"char_face {slug},player",
            "translated_dialog jji_mansion_gate_no_invite",
        ],
        conditions=[
            f"not variable_set {GATE_OPEN}",
            no_invite,
        ],
        behaviours=[
            f"talk {slug}",
        ],
    )


# Invitation dialogue. Either officer can approve entry.
for index, slug in enumerate(officers, start=1):
    x, y = CLOSED_POSITIONS[slug]

    next_id = add_event(
        events,
        next_id,
        name=f"{PATCH_PREFIX} - Present Invitation {index}",
        x=x * 16,
        y=y * 16,
        actions=[
            f"char_face {slug},player",
            "translated_dialog jji_mansion_gate_invite",

            # Left officer steps left.
            f"char_move {LEFT},left 1",

            # Right officer steps right.
            f"char_move {RIGHT},right 1",

            f"char_face {LEFT},down",
            f"char_face {RIGHT},down",

            f"set_variable {GATE_OPEN}",
        ],
        conditions=[
            f"not variable_set {GATE_OPEN}",
            has_invite,
            f"is char_exists {LEFT}",
            f"is char_exists {RIGHT}",
        ],
        behaviours=[
            f"talk {slug}",
        ],
    )


# Respawn officers at the sides after returning to routea.
for index, slug in enumerate(officers, start=1):
    x, y = OPEN_POSITIONS[slug]

    next_id = add_event(
        events,
        next_id,
        name=f"{PATCH_PREFIX} - Open Spawn {index}",
        x=0,
        y=0,
        actions=[
            f"create_npc {slug},{x},{y},stand",
            f"char_face {slug},down",
        ],
        conditions=[
            f"not char_exists {slug}",
            f"is variable_set {GATE_OPEN}",
        ],
    )

    next_id = add_event(
        events,
        next_id,
        name=f"{PATCH_PREFIX} - Open Talk {index}",
        x=x * 16,
        y=y * 16,
        actions=[
            f"char_face {slug},player",
            "translated_dialog jji_mansion_gate_open",
        ],
        conditions=[
            f"is variable_set {GATE_OPEN}",
        ],
        behaviours=[
            f"talk {slug}",
        ],
    )


root.set(
    "nextobjectid",
    str(next_id),
)

ET.indent(tree, space=" ", level=0)

tree.write(
    MAP,
    encoding="UTF-8",
    xml_declaration=True,
)

ET.parse(MAP)

print("Updated routea.tmx.")
print("Closed officer positions:", CLOSED_POSITIONS)
print("Open officer positions:", OPEN_POSITIONS)


# ------------------------------------------------------------------
# Add dialogue.
# ------------------------------------------------------------------

po_backup = PO.with_suffix(
    ".po.bak-before-mansion-gate-dialogue"
)

if not po_backup.exists():
    shutil.copy2(PO, po_backup)

lines = PO.read_text(
    encoding="utf-8"
).splitlines()

for key, value in DIALOGUE.items():
    set_po_entry(lines, key, value)

PO.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)

print("Added Mansion gate dialogue.")
print()
print("Mansion invitation gate installed successfully.")
