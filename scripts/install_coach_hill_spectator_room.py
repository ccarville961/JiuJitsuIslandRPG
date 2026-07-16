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

HILL_MAP = ROOT / "mods/tuxemon/maps/dojo3.tmx"
TOLAND_MAP = ROOT / "mods/tuxemon/maps/dojo2.tmx"

NPC_DIR = ROOT / "mods/tuxemon/db/npc"
PO_PATH = (
    ROOT
    / "mods/tuxemon/l18n/en_US/LC_MESSAGES/base.po"
)
GFX_DIR = ROOT / "mods/tuxemon/gfx"

HILL_NPC = "jji_coach_hill"
PATCH_PREFIX = "JJI Coach Hill Spectator Room"

TOLAND_DEFEATED = (
    "jji_blackbelt_toland_defeated:yes"
)

SPECTATORS = (
    {
        "slug": "jji_hill_spectator_massive_win",
        "source_candidates": (
            "jji_toland_spectator_pressure",
            "jji_blackbelt_dojo_purple_belt",
            "jji_blackbelt_dojo_calm_brown_belt",
        ),
        "dialogue": "jji_hill_spectator_massive_win",
        "text": (
            "Purple Belt: Wow! You beat Coach Toland!\n"
            "That is a massive win. You might really have "
            "a chance against Coach Hill."
        ),
    },
    {
        "slug": "jji_hill_spectator_respect",
        "source_candidates": (
            "jji_toland_spectator_takedowns",
            "jji_blackbelt_dojo_blue_belt",
            "jji_blackbelt_dojo_white_belt",
        ),
        "dialogue": "jji_hill_spectator_respect",
        "text": (
            "Blue Belt: Toland is no joke.\n"
            "If you handled his pressure, you have earned "
            "everyone's respect."
        ),
    },
    {
        "slug": "jji_hill_spectator_real_chance",
        "source_candidates": (
            "jji_toland_spectator_observer",
            "jji_blackbelt_dojo_older_black_belt",
            "jji_blackbelt_dojo_visiting_coach",
        ),
        "dialogue": "jji_hill_spectator_real_chance",
        "text": (
            "Black Belt: Coach Hill will not be easy.\n"
            "But after defeating Toland, you have a real "
            "chance of completing the assessment."
        ),
    },
    {
        "slug": "jji_hill_spectator_atomic_drop",
        "source_candidates": (
            "jji_toland_spectator_transitions",
            "jji_blackbelt_dojo_veteran_grappler",
            "jji_blackbelt_dojo_training_partner",
        ),
        "dialogue": "jji_hill_spectator_atomic_drop",
        "text": (
            "Veteran Grappler: Watch for Coach Hill's "
            "famous Atomic Butt Drop.\n"
            "It is his signature finisher."
        ),
    },
    {
        "slug": "jji_hill_spectator_ribs",
        "source_candidates": (
            "jji_toland_spectator_guard",
            "jji_blackbelt_dojo_nervous_brown_belt",
            "jji_blackbelt_dojo_white_belt",
        ),
        "dialogue": "jji_hill_spectator_ribs",
        "text": (
            "Brown Belt: People say the Atomic Butt Drop "
            "has broken ribs.\n"
            "Stay mobile and do not let him trap you beneath it."
        ),
    },
    {
        "slug": "jji_hill_spectator_strategy",
        "source_candidates": (
            "jji_toland_spectator_composure",
            "jji_blackbelt_dojo_calm_brown_belt",
            "jji_blackbelt_dojo_blue_belt",
        ),
        "dialogue": "jji_hill_spectator_strategy",
        "text": (
            "Student: Keep your frames strong and watch "
            "his hips.\n"
            "If Hill gets above you, move before he launches "
            "the Atomic Butt Drop!"
        ),
    },
)

DIALOGUE = {
    "jji_toland_stair_officer_open": (
        "Officer: Coach Toland has approved your progress.\n"
        "The path to Coach Hill is now open."
    ),
    "jji_blackbelt_toland_next_hill": (
        "Coach Toland: You fought well. Your jiu-jitsu is worthy.\n"
        "You have passed my assessment.\n"
        "Go upstairs. Coach Hill is waiting for you."
    ),
    "jji_blackbelt_toland_after": (
        "Coach Toland: You have already passed my assessment.\n"
        "Coach Hill is your final test. Stay composed."
    ),
    **{
        spectator["dialogue"]: spectator["text"]
        for spectator in SPECTATORS
    },
}


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        fail(f"Missing YAML file: {path}")

    data = yaml.safe_load(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        fail(f"{path} is not a single YAML mapping.")

    return data


def save_yaml(
    path: Path,
    data: dict[str, Any],
) -> None:
    path.write_text(
        yaml.safe_dump(
            data,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def clone_npc(
    target_slug: str,
    source_candidates: tuple[str, ...],
) -> None:
    source_path = None

    for candidate in source_candidates:
        candidate_path = (
            NPC_DIR / f"{candidate}.yaml"
        )

        if candidate_path.exists():
            source_path = candidate_path
            break

    if source_path is None:
        fail(
            f"No reusable source NPC found for {target_slug}.\n"
            f"Tried: {', '.join(source_candidates)}"
        )

    result = copy.deepcopy(
        load_yaml(source_path)
    )

    result["slug"] = target_slug

    if "speech" in result:
        result["speech"] = {
            "profile": {
                "default": {}
            }
        }

    destination = (
        NPC_DIR / f"{target_slug}.yaml"
    )

    save_yaml(destination, result)

    template = result.get("template", {})

    print(
        f"{target_slug} <- {source_path.name}; "
        f"sprite="
        f"{template.get('sprite_name') if isinstance(template, dict) else None}"
    )


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
        fail(
            f"Duplicate translation entries for {key}"
        )

    if not matches:
        if lines and lines[-1] != "":
            lines.append("")

        lines.extend(
            [
                "# JJI Coach Hill assessment",
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
        and not lines[msgstr_index].startswith(
            "msgstr "
        )
    ):
        msgstr_index += 1

    if msgstr_index >= len(lines):
        fail(f"No msgstr found for {key}")

    end_index = msgstr_index + 1

    while (
        end_index < len(lines)
        and lines[end_index].startswith('"')
    ):
        end_index += 1

    lines[msgstr_index:end_index] = [
        msgstr
    ]


def event_layer(
    root: ET.Element,
) -> ET.Element:
    for group in root.findall("objectgroup"):
        if (
            group.get("name", "").lower()
            == "events"
        ):
            return group

    fail("Map has no Events object layer.")


def add_event(
    layer: ET.Element,
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
        layer,
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

    properties = ET.SubElement(
        obj,
        "properties",
    )

    for index, action in enumerate(
        actions,
        start=1,
    ):
        ET.SubElement(
            properties,
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
            properties,
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
            properties,
            "property",
            {
                "name": f"cond{index * 10}",
                "value": condition,
            },
        )

    return object_id + 1


def find_create_positions(
    events: ET.Element,
) -> dict[tuple[int, int], list[str]]:
    pattern = re.compile(
        r"^create_npc\s+([^,]+),"
        r"(-?\d+),(-?\d+),"
    )

    occupied: dict[
        tuple[int, int],
        list[str],
    ] = {}

    for obj in events.findall("object"):
        for prop in obj.findall(
            "./properties/property"
        ):
            match = pattern.match(
                prop.get("value", "")
            )

            if not match:
                continue

            position = (
                int(match.group(2)),
                int(match.group(3)),
            )

            occupied.setdefault(
                position,
                [],
            ).append(match.group(1))

    return occupied


# ------------------------------------------------------------------
# Update Coach Hill's overworld minisprite.
# ------------------------------------------------------------------

icon_files = [
    path
    for path in GFX_DIR.rglob("*")
    if (
        path.is_file()
        and path.stem.lower() == "icon_coach"
    )
]

if not icon_files:
    fail(
        "Could not find icon_coach.png under "
        "mods/tuxemon/gfx."
    )

hill_npc_path = (
    NPC_DIR / f"{HILL_NPC}.yaml"
)

hill_npc = load_yaml(hill_npc_path)
hill_template = hill_npc.get("template")

if not isinstance(hill_template, dict):
    fail(
        f"{hill_npc_path} has no template mapping."
    )

hill_template["sprite_name"] = "icon_coach"
hill_npc["template"] = hill_template

save_yaml(
    hill_npc_path,
    hill_npc,
)

print("Coach Hill overworld sprite: icon_coach")
print("Sprite resource:", icon_files[0])


# ------------------------------------------------------------------
# Create distinct spectators.
# ------------------------------------------------------------------

for spectator in SPECTATORS:
    clone_npc(
        spectator["slug"],
        spectator["source_candidates"],
    )


# ------------------------------------------------------------------
# Repair Toland post-battle events.
# ------------------------------------------------------------------

if TOLAND_MAP.exists():
    toland_backup = TOLAND_MAP.with_suffix(
        ".tmx.bak-before-final-toland-dialogue-repair"
    )

    if not toland_backup.exists():
        shutil.copy2(
            TOLAND_MAP,
            toland_backup,
        )

    toland_tree = ET.parse(TOLAND_MAP)
    toland_root = toland_tree.getroot()
    toland_events = event_layer(toland_root)

    for obj in toland_events.findall("object"):
        name = obj.get("name", "")

        values = [
            prop.get("value", "")
            for prop in obj.findall(
                "./properties/property"
            )
        ]

        # Ensure officer open dialogue points to the
        # translated key.
        if any(
            value
            == (
                "translated_dialog "
                "jji_toland_stair_officer_open"
            )
            for value in values
        ):
            print(
                "Verified Toland officer open dialogue event:",
                name,
            )

        # Ensure Toland's manual post-battle talk uses
        # the correct post-battle key.
        if name.endswith(
            "Coach Toland Post-Battle Talk"
        ):
            for prop in obj.findall(
                "./properties/property"
            ):
                value = prop.get("value", "")

                if value.startswith(
                    "translated_dialog "
                ):
                    prop.set(
                        "value",
                        (
                            "translated_dialog "
                            "jji_blackbelt_toland_next_hill"
                        ),
                    )

            print(
                "Repaired Coach Toland post-battle dialogue."
            )

    ET.indent(
        toland_tree,
        space=" ",
        level=0,
    )

    toland_tree.write(
        TOLAND_MAP,
        encoding="UTF-8",
        xml_declaration=True,
    )

    ET.parse(TOLAND_MAP)


# ------------------------------------------------------------------
# Populate dojo3.tmx.
# ------------------------------------------------------------------

if not HILL_MAP.exists():
    fail(f"Missing map: {HILL_MAP}")

hill_backup = HILL_MAP.with_suffix(
    ".tmx.bak-before-hill-spectator-room"
)

if not hill_backup.exists():
    shutil.copy2(
        HILL_MAP,
        hill_backup,
    )
    print(f"Created backup: {hill_backup}")

tree = ET.parse(HILL_MAP)
root = tree.getroot()
events = event_layer(root)

width = int(root.get("width", "0"))
height = int(root.get("height", "0"))

for obj in list(events.findall("object")):
    if obj.get("name", "").startswith(
        PATCH_PREFIX
    ):
        events.remove(obj)


occupied = find_create_positions(events)

# Place spectators in one tight row near the bottom.
#
# dojo3 is expected to be 24 × 12 like the other
# assessment floors. Row height-1 may overlap the
# bottom transition, so use height-2.
spectator_y = height - 2

start_x = max(
    2,
    (width - len(SPECTATORS)) // 2,
)

positions = [
    (
        start_x + index,
        spectator_y,
    )
    for index in range(len(SPECTATORS))
]


# If the centred row conflicts with an existing NPC,
# search left-to-right for a clear consecutive block.
def block_is_clear(
    candidate_positions: list[
        tuple[int, int]
    ],
) -> bool:
    return all(
        position not in occupied
        for position in candidate_positions
    )


if not block_is_clear(positions):
    positions = []

    for candidate_x in range(
        2,
        width - len(SPECTATORS) - 1,
    ):
        candidate_positions = [
            (
                candidate_x + index,
                spectator_y,
            )
            for index in range(
                len(SPECTATORS)
            )
        ]

        if block_is_clear(
            candidate_positions
        ):
            positions = candidate_positions
            break

if len(positions) != len(SPECTATORS):
    fail(
        "Could not find six consecutive clear tiles "
        "for Coach Hill spectators."
    )


all_ids = [
    int(obj.get("id", "0"))
    for group in root.findall("objectgroup")
    for obj in group.findall("object")
]

next_id = max(all_ids, default=0) + 1

for spectator, (x, y) in zip(
    SPECTATORS,
    positions,
):
    slug = spectator["slug"]

    next_id = add_event(
        events,
        next_id,
        name=f"{PATCH_PREFIX} - Spawn {slug}",
        x=0,
        y=0,
        actions=[
            f"create_npc {slug},{x},{y},stand",
            f"char_face {slug},up",
        ],
        conditions=[
            f"not char_exists {slug}",
            f"is variable_set {TOLAND_DEFEATED}",
        ],
    )

    next_id = add_event(
        events,
        next_id,
        name=f"{PATCH_PREFIX} - Talk {slug}",
        x=x * 16,
        y=y * 16,
        actions=[
            f"char_face {slug},player",
            (
                f"translated_dialog "
                f"{spectator['dialogue']}"
            ),
        ],
        conditions=[
            f"is variable_set {TOLAND_DEFEATED}",
        ],
        behaviours=[
            f"talk {slug}",
        ],
    )

    print(
        f"{slug}: ({x}, {y}), facing up"
    )

root.set(
    "nextobjectid",
    str(next_id),
)

ET.indent(
    tree,
    space=" ",
    level=0,
)

tree.write(
    HILL_MAP,
    encoding="UTF-8",
    xml_declaration=True,
)

ET.parse(HILL_MAP)


# ------------------------------------------------------------------
# Update translations.
# ------------------------------------------------------------------

po_backup = PO_PATH.with_suffix(
    ".po.bak-before-hill-spectator-dialogue"
)

if not po_backup.exists():
    shutil.copy2(
        PO_PATH,
        po_backup,
    )

lines = PO_PATH.read_text(
    encoding="utf-8"
).splitlines()

for key, value in DIALOGUE.items():
    set_po_entry(
        lines,
        key,
        value,
    )

PO_PATH.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)

print()
print("Coach Hill spectator room installed.")
print("Spectator positions:", positions)
print("Coach Hill sprite: icon_coach")
print("Toland post-battle translations repaired.")
