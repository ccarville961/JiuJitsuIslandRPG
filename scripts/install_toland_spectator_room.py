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

MAP = ROOT / "mods/tuxemon/maps/dojo2.tmx"
NPC_DIR = ROOT / "mods/tuxemon/db/npc"
PO = ROOT / "mods/tuxemon/l18n/en_US/LC_MESSAGES/base.po"
GFX_DIR = ROOT / "mods/tuxemon/gfx"

PATCH_PREFIX = "JJI Toland Spectator Room"

TOLAND_NPC = "jji_coach_toland"
TOLAND_DEFEATED = "jji_blackbelt_toland_defeated:yes"

OFFICERS = (
    "jji_toland_stair_officer_left",
    "jji_toland_stair_officer_right",
)

SPECTATORS = (
    {
        "slug": "jji_toland_spectator_pressure",
        "dialogue": "jji_toland_spectator_pressure",
        "text": (
            "Brown Belt: Coach Toland's pressure is relentless.\n"
            "Do not give him space to settle his weight."
        ),
        "source_candidates": (
            "jji_blackbelt_dojo_calm_brown_belt",
            "jji_blackbelt_dojo_nervous_brown_belt",
            "jji_blackbelt_dojo_veteran_grappler",
        ),
    },
    {
        "slug": "jji_toland_spectator_takedowns",
        "dialogue": "jji_toland_spectator_takedowns",
        "text": (
            "Purple Belt: His takedowns arrive from angles "
            "you do not expect.\n"
            "Watch his level changes and protect your base."
        ),
        "source_candidates": (
            "jji_blackbelt_dojo_purple_belt",
            "jji_blackbelt_dojo_training_partner",
            "jji_blackbelt_dojo_blue_belt",
        ),
    },
    {
        "slug": "jji_toland_spectator_observer",
        "dialogue": "jji_toland_spectator_observer",
        "text": (
            "Black Belt: We are here to observe how Coach Toland moves.\n"
            "Every grip, step and reaction contains a lesson."
        ),
        "source_candidates": (
            "jji_blackbelt_dojo_older_black_belt",
            "jji_blackbelt_dojo_visiting_coach",
            "jji_blackbelt_dojo_veteran_grappler",
        ),
    },
    {
        "slug": "jji_toland_spectator_guard",
        "dialogue": "jji_toland_spectator_guard",
        "text": (
            "Blue Belt: His guard retention is exceptional.\n"
            "Break his posture and control his hips before attacking."
        ),
        "source_candidates": (
            "jji_blackbelt_dojo_blue_belt",
            "jji_blackbelt_dojo_white_belt",
            "jji_blackbelt_dojo_calm_brown_belt",
        ),
    },
    {
        "slug": "jji_toland_spectator_transitions",
        "dialogue": "jji_toland_spectator_transitions",
        "text": (
            "Veteran Grappler: His transitions are fluid.\n"
            "Predicting the next position is the real challenge."
        ),
        "source_candidates": (
            "jji_blackbelt_dojo_veteran_grappler",
            "jji_blackbelt_dojo_older_black_belt",
            "jji_blackbelt_dojo_training_partner",
        ),
    },
    {
        "slug": "jji_toland_spectator_composure",
        "dialogue": "jji_toland_spectator_composure",
        "text": (
            "Student: Toland punishes panic.\n"
            "Stay composed, frame correctly and make every escape deliberate."
        ),
        "source_candidates": (
            "jji_blackbelt_dojo_white_belt",
            "jji_blackbelt_dojo_nervous_brown_belt",
            "jji_blackbelt_dojo_blue_belt",
        ),
    },
)

DIALOGUE = {
    "jji_toland_stair_officer": (
        "Officer: The upper floor is closed during the assessment.\n"
        "Defeat Coach Toland before proceeding to Coach Hill."
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

    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        fail(f"{path} is not a single YAML mapping.")

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


def clone_npc(
    target_slug: str,
    source_candidates: tuple[str, ...],
) -> None:
    source_path = None

    for candidate in source_candidates:
        path = NPC_DIR / f"{candidate}.yaml"

        if path.exists():
            source_path = path
            break

    if source_path is None:
        fail(
            f"No valid source NPC found for {target_slug}.\n"
            f"Tried: {', '.join(source_candidates)}"
        )

    source = load_yaml(source_path)
    result = copy.deepcopy(source)
    result["slug"] = target_slug

    # Dialogue is controlled exclusively by TMX events.
    if "speech" in result:
        result["speech"] = {
            "profile": {
                "default": {}
            }
        }

    target = NPC_DIR / f"{target_slug}.yaml"
    save_yaml(target, result)

    template = result.get("template", {})

    print(
        f"{target_slug} <- {source_path.name} "
        f"sprite={template.get('sprite_name') if isinstance(template, dict) else None}"
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
        fail(f"Duplicate PO entries found for {key}")

    if not matches:
        if lines and lines[-1] != "":
            lines.append("")

        lines.extend(
            [
                "# JJI Coach Toland Spectator Room",
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


def properties(obj: ET.Element) -> ET.Element:
    props = obj.find("properties")

    if props is None:
        props = ET.SubElement(obj, "properties")

    return props


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


def collision_rectangles(
    root: ET.Element,
) -> list[tuple[float, float, float, float]]:
    rectangles = []

    for group in root.findall("objectgroup"):
        if "collision" not in group.get("name", "").lower():
            continue

        for obj in group.findall("object"):
            left = float(obj.get("x", "0"))
            top = float(obj.get("y", "0"))
            width = float(obj.get("width", "0"))
            height = float(obj.get("height", "0"))

            rectangles.append(
                (
                    left,
                    top,
                    left + width,
                    top + height,
                )
            )

    return rectangles


def tile_blocked(
    rectangles: list[tuple[float, float, float, float]],
    x: int,
    y: int,
) -> bool:
    left = x * 16
    top = y * 16
    right = left + 16
    bottom = top + 16

    return any(
        left < rect_right
        and right > rect_left
        and top < rect_bottom
        and bottom > rect_top
        for (
            rect_left,
            rect_top,
            rect_right,
            rect_bottom,
        ) in rectangles
    )


if not MAP.exists():
    fail(f"Missing map: {MAP}")

if not PO.exists():
    fail(f"Missing translation catalogue: {PO}")


# ------------------------------------------------------------------
# Update Coach Toland's overworld sprite.
# ------------------------------------------------------------------

talos_files = [
    path
    for path in GFX_DIR.rglob("*")
    if path.is_file()
    and path.stem.lower() == "talos_coach"
]

if not talos_files:
    fail(
        "Could not find talos_coach.png under mods/tuxemon/gfx.\n"
        "Confirm the file exists before running this installer."
    )

coach_path = NPC_DIR / f"{TOLAND_NPC}.yaml"
coach = load_yaml(coach_path)

template = coach.get("template")

if not isinstance(template, dict):
    fail(f"{coach_path} has no valid template mapping.")

template["sprite_name"] = "talos_coach"
coach["template"] = template

save_yaml(coach_path, coach)

print("Coach Toland overworld sprite: talos_coach")
print("Sprite resource:", talos_files[0])


# ------------------------------------------------------------------
# Create officers and spectators from valid existing NPC schemas.
# ------------------------------------------------------------------

officer_sources = (
    "jji_blackbelt_dojo_stair_officer_left",
    "jji_blackbelt_dojo_stair_officer_right",
    "jji_blackbelt_dojo_patrol_officer",
)

for officer_slug in OFFICERS:
    clone_npc(
        officer_slug,
        officer_sources,
    )

for spectator in SPECTATORS:
    clone_npc(
        spectator["slug"],
        spectator["source_candidates"],
    )


# ------------------------------------------------------------------
# Patch dojo2.tmx.
# ------------------------------------------------------------------

backup = MAP.with_suffix(
    ".tmx.bak-before-toland-spectator-room"
)

if not backup.exists():
    shutil.copy2(MAP, backup)
    print(f"Created backup: {backup}")

tree = ET.parse(MAP)
root = tree.getroot()

width = int(root.get("width", "0"))
height = int(root.get("height", "0"))

events = next(
    (
        group
        for group in root.findall("objectgroup")
        if group.get("name", "").lower() == "events"
    ),
    None,
)

if events is None:
    fail("dojo2.tmx has no Events object layer.")


# Remove previous copies of this patch.
for obj in list(events.findall("object")):
    if obj.get("name", "").startswith(PATCH_PREFIX):
        events.remove(obj)


# Find upstairs teleport events.
upstairs_events = []

for obj in events.findall("object"):
    values = [
        prop.get("value", "")
        for prop in obj.findall("./properties/property")
    ]

    if any(
        value.startswith("transition_teleport player,dojo3.tmx,")
        for value in values
    ):
        upstairs_events.append(obj)

if not upstairs_events:
    fail(
        "Could not find a transition from dojo2.tmx to dojo3.tmx."
    )


# Add the Toland-defeated gate condition to every upstairs teleport.
for obj in upstairs_events:
    props = properties(obj)

    existing_conditions = [
        prop.get("value", "")
        for prop in props.findall("property")
        if re.fullmatch(
            r"cond\d+",
            prop.get("name", ""),
        )
    ]

    required = f"is variable_set {TOLAND_DEFEATED}"

    if required not in existing_conditions:
        condition_numbers = [
            int(match.group(1))
            for prop in props.findall("property")
            if (
                match := re.fullmatch(
                    r"cond(\d+)",
                    prop.get("name", ""),
                )
            )
        ]

        next_condition = max(condition_numbers, default=0) + 10

        ET.SubElement(
            props,
            "property",
            {
                "name": f"cond{next_condition}",
                "value": required,
            },
        )


# Find tiles covered by the upstairs teleport.
teleport_tiles: list[tuple[int, int]] = []

for obj in upstairs_events:
    start_x = int(float(obj.get("x", "0"))) // 16
    start_y = int(float(obj.get("y", "0"))) // 16
    tile_width = max(
        1,
        int(float(obj.get("width", "16"))) // 16,
    )
    tile_height = max(
        1,
        int(float(obj.get("height", "16"))) // 16,
    )

    for y in range(start_y, start_y + tile_height):
        for x in range(start_x, start_x + tile_width):
            teleport_tiles.append((x, y))

teleport_tiles = list(dict.fromkeys(teleport_tiles))

if len(teleport_tiles) >= 2:
    officer_positions = teleport_tiles[:2]
else:
    stair_x, stair_y = teleport_tiles[0]
    officer_positions = [
        (max(1, stair_x - 1), stair_y),
        (min(width - 2, stair_x + 1), stair_y),
    ]


# Existing IDs.
object_ids = [
    int(obj.get("id", "0"))
    for group in root.findall("objectgroup")
    for obj in group.findall("object")
]

next_id = max(object_ids, default=0) + 1


# Officers physically block the stair entrance until Toland is beaten.
for index, (slug, position) in enumerate(
    zip(OFFICERS, officer_positions),
):
    x, y = position

    next_id = add_event(
        events,
        next_id,
        name=(
            f"{PATCH_PREFIX} - "
            f"Spawn Stair Officer {index + 1}"
        ),
        x=0,
        y=0,
        actions=[
            f"create_npc {slug},{x},{y},stand",
            f"char_face {slug},down",
        ],
        conditions=[
            f"not char_exists {slug}",
            f"not variable_set {TOLAND_DEFEATED}",
        ],
    )

    next_id = add_event(
        events,
        next_id,
        name=(
            f"{PATCH_PREFIX} - "
            f"Talk Stair Officer {index + 1}"
        ),
        x=x * 16,
        y=y * 16,
        actions=[
            f"char_face {slug},player",
            "translated_dialog jji_toland_stair_officer",
        ],
        conditions=[
            f"not variable_set {TOLAND_DEFEATED}",
        ],
        behaviours=[
            f"talk {slug}",
        ],
    )


# Remove officers immediately after Toland is defeated when the
# installed engine provides a remove_npc action.
remove_npc_supported = (
    ROOT / "tuxemon/event/actions/remove_npc.py"
).exists()

if remove_npc_supported:
    next_id = add_event(
        events,
        next_id,
        name=f"{PATCH_PREFIX} - Open Upstairs After Victory",
        x=0,
        y=0,
        actions=[
            f"remove_npc {OFFICERS[0]}",
            f"remove_npc {OFFICERS[1]}",
        ],
        conditions=[
            f"is variable_set {TOLAND_DEFEATED}",
            (
                "not variable_set "
                "jji_toland_stair_gate_opened:yes"
            ),
        ],
    )

    # Add the state setter as a final action.
    event = events.findall("object")[-1]
    props = properties(event)

    ET.SubElement(
        props,
        "property",
        {
            "name": "act30",
            "value": (
                "set_variable "
                "jji_toland_stair_gate_opened:yes"
            ),
        },
    )

    print("Officers will be removed immediately after victory.")
else:
    print(
        "remove_npc action is unavailable. Officers disappear "
        "after leaving and re-entering dojo2.tmx."
    )


# ------------------------------------------------------------------
# Choose six clear spectator tiles near the bottom of the room.
# ------------------------------------------------------------------

rectangles = collision_rectangles(root)

reserved = set(teleport_tiles)
reserved.update(officer_positions)

# Reserve Coach Toland and other existing generated NPC spawn tiles.
create_pattern = re.compile(
    r"^create_npc\s+([^,]+),(-?\d+),(-?\d+),"
)

for obj in events.findall("object"):
    for prop in obj.findall("./properties/property"):
        match = create_pattern.match(
            prop.get("value", "")
        )

        if match:
            reserved.add(
                (
                    int(match.group(2)),
                    int(match.group(3)),
                )
            )


candidates = []

for y in range(height - 2, max(1, height // 2), -1):
    for x in range(2, width - 2):
        if (x, y) in reserved:
            continue

        if tile_blocked(rectangles, x, y):
            continue

        candidates.append((x, y))

# Spread the spectators rather than placing them consecutively.
if len(candidates) < len(SPECTATORS):
    fail(
        "Could not find enough clear lower-room tiles for spectators."
    )

same_row = {}

for position in candidates:
    same_row.setdefault(position[1], []).append(position)

best_row = max(
    same_row.values(),
    key=len,
)

if len(best_row) >= len(SPECTATORS):
    positions = []

    for index in range(len(SPECTATORS)):
        source_index = round(
            index
            * (len(best_row) - 1)
            / max(1, len(SPECTATORS) - 1)
        )
        positions.append(best_row[source_index])
else:
    positions = candidates[:len(SPECTATORS)]


for spectator, (x, y) in zip(SPECTATORS, positions):
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
            f"translated_dialog {spectator['dialogue']}",
        ],
        conditions=[],
        behaviours=[
            f"talk {slug}",
        ],
    )

    reserved.add((x, y))

    print(
        f"Spectator {slug}: ({x}, {y}), facing up"
    )


root.set("nextobjectid", str(next_id))

ET.indent(tree, space=" ", level=0)
tree.write(
    MAP,
    encoding="UTF-8",
    xml_declaration=True,
)

ET.parse(MAP)


# ------------------------------------------------------------------
# Add dialogue.
# ------------------------------------------------------------------

po_backup = PO.with_suffix(
    ".po.bak-before-toland-spectator-room"
)

if not po_backup.exists():
    shutil.copy2(PO, po_backup)
    print(f"Created backup: {po_backup}")

lines = PO.read_text(encoding="utf-8").splitlines()

for key, value in DIALOGUE.items():
    set_po_entry(lines, key, value)

PO.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)

print()
print("Coach Toland spectator room installed.")
print("Officer positions:", officer_positions)
print("Spectator positions:", positions)
print("Upstairs teleport requires:", TOLAND_DEFEATED)
