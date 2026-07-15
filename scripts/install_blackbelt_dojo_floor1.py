#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


ROOT = Path.cwd()

MAP = ROOT / "mods/tuxemon/maps/taba_ba_main.tmx"
PO = ROOT / "mods/tuxemon/l18n/en_US/LC_MESSAGES/base.po"
NPC_DIR = ROOT / "mods/tuxemon/db/npc"

PATCH_PREFIX = "JJI Black Belt Dojo Floor 1"
NPC_PREFIX = "jji_blackbelt_dojo_"

BACKUP = MAP.with_suffix(".tmx.bak-before-blackbelt-dojo-floor1")


@dataclass(frozen=True)
class DojoNPC:
    suffix: str
    label: str
    tile_x: int
    tile_y: int
    facing: str
    dialogue_key: str
    dialogue: str
    preferred_sources: tuple[str, ...] = ()


# Coordinates use 16 × 16 map tiles.
#
# The two stair officers are positioned near the central upper staircase.
# The remaining NPCs are distributed around the room rather than clustered
# around the entrance.
#
# If one appears over furniture, only edit tile_x and tile_y here.
NPCS: tuple[DojoNPC, ...] = (
    DojoNPC(
        "stair_officer_left",
        "Stair Officer Left",
        15, 5, "down",
        "jji_blackbelt_dojo_stair_officer_left",
        (
            "Officer: Halt. The upper floor is restricted.\n"
            "Coach Dave and Coach Toland are conducting the Black Belt Assessment.\n"
            "Defeat them both and you will earn your Black Belt—and an official Mansion Invitation."
        ),
        ("officer", "police", "guard", "enforcer", "grunt"),
    ),
    DojoNPC(
        "stair_officer_right",
        "Stair Officer Right",
        17, 5, "down",
        "jji_blackbelt_dojo_stair_officer_right",
        (
            "Officer: Plenty of Brown Belts walk up those stairs.\n"
            "Most walk back down empty-handed.\n"
            "Do not continue until you are prepared."
        ),
        ("officer", "police", "guard", "enforcer", "grunt"),
    ),
    DojoNPC(
        "entrance_officer",
        "Entrance Officer",
        16, 14, "down",
        "jji_blackbelt_dojo_entrance_officer",
        (
            "Officer: Welcome to the Black Belt Dojo.\n"
            "Everyone enters through these doors...\n"
            "but not everyone leaves wearing a Black Belt."
        ),
        ("officer", "police", "guard", "enforcer", "grunt"),
    ),
    DojoNPC(
        "patrol_officer",
        "Patrol Officer",
        2, 8, "right",
        "jji_blackbelt_dojo_patrol_officer",
        (
            "Officer: Keep the corridors clear and show respect.\n"
            "Competitors have travelled from every academy on the island for today's assessments."
        ),
        ("officer", "police", "guard", "enforcer", "grunt"),
    ),
    DojoNPC(
        "nervous_brown_belt",
        "Nervous Brown Belt",
        11, 11, "right",
        "jji_blackbelt_dojo_nervous_brown",
        (
            "Brown Belt: I have spent six months preparing for this.\n"
            "I know every technique I planned to use...\n"
            "so why have my legs forgotten how to stand?"
        ),
        ("brown", "martial", "fighter", "trainer"),
    ),
    DojoNPC(
        "calm_brown_belt",
        "Calm Brown Belt",
        13, 11, "left",
        "jji_blackbelt_dojo_calm_brown",
        (
            "Brown Belt: Win or lose, I am climbing those stairs.\n"
            "Courage is not the absence of nerves.\n"
            "It is moving forward while they are screaming at you."
        ),
        ("brown", "martial", "fighter", "trainer"),
    ),
    DojoNPC(
        "purple_belt",
        "Purple Belt Spectator",
        7, 8, "right",
        "jji_blackbelt_dojo_purple_belt",
        (
            "Purple Belt: I have watched dozens of assessments here.\n"
            "Nobody walks upstairs smiling.\n"
            "Coach Dave notices mistakes before you realise you made them."
        ),
        ("purple", "martial", "fighter", "trainer"),
    ),
    DojoNPC(
        "blue_belt",
        "Blue Belt Student",
        14, 8, "left",
        "jji_blackbelt_dojo_blue_belt",
        (
            "Blue Belt: One day I will return for my own assessment.\n"
            "For now, I am studying the people who were brave enough to try."
        ),
        ("blue", "student", "martial", "fighter"),
    ),
    DojoNPC(
        "white_belt",
        "White Belt Student",
        4, 12, "right",
        "jji_blackbelt_dojo_white_belt",
        (
            "White Belt: Everyone upstairs was once standing where I am now.\n"
            "That makes becoming a Black Belt feel impossible...\n"
            "and possible at the same time."
        ),
        ("white", "student", "martial", "fighter"),
    ),
    DojoNPC(
        "older_black_belt",
        "Older Black Belt",
        5, 4, "down",
        "jji_blackbelt_dojo_older_black_belt",
        (
            "Black Belt: Your belt tells me where you have been.\n"
            "Your attitude tells me where you are going.\n"
            "A Black Belt is a responsibility, not a finish line."
        ),
        ("black", "professor", "trainer", "martial"),
    ),
    DojoNPC(
        "visiting_coach",
        "Visiting Coach",
        13, 4, "down",
        "jji_blackbelt_dojo_visiting_coach",
        (
            "Coach: Every academy teaches differently.\n"
            "Good fundamentals speak every language.\n"
            "Position first, control second, submission last."
        ),
        ("coach", "professor", "trainer", "martial"),
    ),
    DojoNPC(
        "veteran_grappler",
        "Veteran Grappler",
        9, 4, "down",
        "jji_blackbelt_dojo_veteran",
        (
            "Veteran: I earned my Black Belt twenty years ago.\n"
            "I am still corrected every week.\n"
            "Mastery begins when you stop pretending you know everything."
        ),
        ("old", "elder", "professor", "trainer"),
    ),
    DojoNPC(
        "jits_trivia",
        "Jits Trivia Student",
        11, 4, "down",
        "jji_blackbelt_dojo_jits_trivia",
        (
            "Student: Jiu-Jitsu is built around leverage and timing.\n"
            "That is why a smaller grappler can control someone much larger.\n"
            "Strength helps—but technique decides where that strength goes."
        ),
        ("student", "scientist", "professor", "trainer"),
    ),
    DojoNPC(
        "training_partner",
        "Training Partner",
        8, 13, "up",
        "jji_blackbelt_dojo_training_partner",
        (
            "Grappler: The best training partner is not the one who wins every round.\n"
            "It is the one who pushes you, protects you and helps you return tomorrow."
        ),
        ("fighter", "student", "martial", "trainer"),
    ),
    DojoNPC(
        "medic",
        "Dojo Medic",
        14, 13, "up",
        "jji_blackbelt_dojo_medic",
        (
            "Medic: Tap early and train tomorrow.\n"
            "Refusing to tap does not prove toughness.\n"
            "Usually it just creates paperwork for me."
        ),
        ("nurse", "doctor", "medic", "scientist"),
    ),
    DojoNPC(
        "cleaner",
        "Dojo Cleaner",
        17, 13, "up",
        "jji_blackbelt_dojo_cleaner",
        (
            "Cleaner: Funny thing about this place...\n"
            "the toughest people are usually the politest.\n"
            "Also, laundry is the true final boss of Jiu-Jitsu."
        ),
        ("janitor", "cleaner", "worker", "old"),
    ),
)


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def yaml_slug(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    matches = re.findall(r"(?m)^\s*slug:\s*['\"]?([a-zA-Z0-9_.-]+)", text)

    # Cloning is safest when the YAML file contains exactly one NPC record.
    if len(matches) != 1:
        return None

    return matches[0]


def discover_source_npcs() -> list[tuple[Path, str, str]]:
    results: list[tuple[Path, str, str]] = []

    for path in sorted(NPC_DIR.glob("*.yaml")):
        if path.name.startswith(NPC_PREFIX):
            continue

        slug = yaml_slug(path)
        if not slug:
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        searchable = f"{path.stem} {slug} {text}".lower()
        results.append((path, slug, searchable))

    return results


def source_score(searchable: str, preferred: tuple[str, ...]) -> int:
    score = 0

    for index, keyword in enumerate(preferred):
        if keyword in searchable:
            score += 100 - index * 5

    # Prefer definitions that already appear human and non-special.
    for useful in ("sprite_name", "human", "trainer", "student", "professor"):
        if useful in searchable:
            score += 2

    # Avoid unusual story-critical characters where possible.
    for risky in ("boss", "legendary", "monster", "final", "test_npcs"):
        if risky in searchable:
            score -= 25

    return score


def choose_sources() -> list[tuple[Path, str]]:
    candidates = discover_source_npcs()

    if not candidates:
        fail(
            "No safe single-record NPC YAML files were found in "
            "mods/tuxemon/db/npc."
        )

    selected: list[tuple[Path, str]] = []
    used_paths: set[Path] = set()

    for npc in NPCS:
        ranked = sorted(
            candidates,
            key=lambda item: (
                -source_score(item[2], npc.preferred_sources),
                item[0].name,
            ),
        )

        choice = next(
            (item for item in ranked if item[0] not in used_paths),
            ranked[0],
        )

        selected.append((choice[0], choice[1]))
        used_paths.add(choice[0])

    return selected


def replace_yaml_slug(text: str, old_slug: str, new_slug: str) -> str:
    pattern = re.compile(
        rf"(?m)^(\s*slug:\s*)['\"]?{re.escape(old_slug)}['\"]?(\s*(?:#.*)?)$"
    )

    updated, count = pattern.subn(
        lambda match: f"{match.group(1)}{new_slug}{match.group(2)}",
        text,
        count=1,
    )

    if count != 1:
        fail(f"Could not replace NPC slug {old_slug!r}.")

    return updated


def clone_npc_definitions() -> dict[str, str]:
    selections = choose_sources()
    slug_map: dict[str, str] = {}

    for npc, (source_path, source_slug) in zip(NPCS, selections):
        new_slug = f"{NPC_PREFIX}{npc.suffix}"
        destination = NPC_DIR / f"{new_slug}.yaml"

        source_text = source_path.read_text(encoding="utf-8")
        cloned = replace_yaml_slug(source_text, source_slug, new_slug)
        destination.write_text(cloned, encoding="utf-8")

        slug_map[npc.suffix] = new_slug

        print(
            f"NPC {new_slug}: cloned from "
            f"{source_path.name} ({source_slug})"
        )

    return slug_map


def property_element(
    parent: ET.Element,
    name: str,
    value: str,
) -> None:
    ET.SubElement(
        parent,
        "property",
        {
            "name": name,
            "value": value,
        },
    )


def add_event(
    group: ET.Element,
    object_id: int,
    *,
    name: str,
    x: int,
    y: int,
    actions: list[str] | None = None,
    conditions: list[str] | None = None,
    behaviours: list[str] | None = None,
    width: int = 16,
    height: int = 16,
) -> int:
    obj = ET.SubElement(
        group,
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

    properties = ET.SubElement(obj, "properties")

    for index, action in enumerate(actions or (), start=1):
        property_element(properties, f"act{index * 10}", action)

    for index, behaviour in enumerate(behaviours or (), start=1):
        property_element(properties, f"behav{index * 10}", behaviour)

    for index, condition in enumerate(conditions or (), start=1):
        property_element(properties, f"cond{index * 10}", condition)

    return object_id + 1


def locate_events_layer(root: ET.Element) -> ET.Element:
    for group in root.findall("objectgroup"):
        if group.get("name", "").lower() == "events":
            return group

    fail(f"{MAP} does not contain an Events object layer.")


def remove_previous_patch(events: ET.Element) -> int:
    removed = 0

    for obj in list(events.findall("object")):
        if obj.get("name", "").startswith(PATCH_PREFIX):
            events.remove(obj)
            removed += 1

    return removed


def patch_map(slug_map: dict[str, str]) -> None:
    if not BACKUP.exists():
        shutil.copy2(MAP, BACKUP)
        print(f"Created backup: {BACKUP}")

    tree = ET.parse(MAP)
    root = tree.getroot()
    events = locate_events_layer(root)

    removed = remove_previous_patch(events)
    if removed:
        print(f"Removed {removed} previous dojo event objects.")

    all_ids = [
        int(obj.get("id", "0"))
        for group in root.findall("objectgroup")
        for obj in group.findall("object")
    ]
    next_id = max(all_ids, default=0) + 1

    for npc in NPCS:
        slug = slug_map[npc.suffix]

        # Spawn event. The event itself can live at 0,0 because the create_npc
        # action contains the NPC's actual tile coordinates.
        next_id = add_event(
            events,
            next_id,
            name=f"{PATCH_PREFIX} - Spawn {npc.label}",
            x=0,
            y=0,
            actions=[
                (
                    f"create_npc {slug},"
                    f"{npc.tile_x},{npc.tile_y},stand"
                ),
                f"char_face {slug},{npc.facing}",
            ],
            conditions=[
                f"not char_exists {slug}",
            ],
        )

        # Tuxemon's talk behaviour runs this event only when that specific NPC
        # is deliberately interacted with.
        next_id = add_event(
            events,
            next_id,
            name=f"{PATCH_PREFIX} - Talk {npc.label}",
            x=npc.tile_x * 16,
            y=npc.tile_y * 16,
            actions=[
                f"char_face {slug},player",
                f"translated_dialog {npc.dialogue_key}",
            ],
            behaviours=[
                f"talk {slug}",
            ],
        )

    root.set(
        "nextobjectid",
        str(max(int(root.get("nextobjectid", "1")), next_id)),
    )

    ET.indent(tree, space=" ", level=0)
    tree.write(MAP, encoding="UTF-8", xml_declaration=True)

    # Immediately confirm that our output is still valid XML.
    ET.parse(MAP)

    print(f"Patched and validated: {MAP}")
    print(f"Added {len(NPCS)} NPCs and {len(NPCS)} talk events.")


def po_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
    )


def po_unescape(text: str) -> str:
    try:
        return ast.literal_eval(f'"{text}"')
    except (SyntaxError, ValueError):
        return text


def patch_dialogue() -> None:
    po_text = PO.read_text(encoding="utf-8")

    additions: list[str] = []

    for npc in NPCS:
        pattern = re.compile(
            rf'(?m)^msgid "{re.escape(npc.dialogue_key)}"$'
        )

        if pattern.search(po_text):
            print(f"Dialogue already exists: {npc.dialogue_key}")
            continue

        additions.append(
            f'msgid "{npc.dialogue_key}"\n'
            f'msgstr "{po_escape(npc.dialogue)}"\n'
        )

    if not additions:
        print("All dojo dialogue entries already exist.")
        return

    with PO.open("a", encoding="utf-8") as handle:
        if po_text and not po_text.endswith("\n"):
            handle.write("\n")

        handle.write("\n# JJI Black Belt Dojo - First Floor NPCs\n\n")
        handle.write("\n".join(additions))

    print(f"Added {len(additions)} dialogue entries to {PO}")


def validate_coordinates() -> None:
    tree = ET.parse(MAP)
    root = tree.getroot()

    map_width = int(root.get("width", "0"))
    map_height = int(root.get("height", "0"))

    print(f"Map dimensions: {map_width} × {map_height} tiles")

    invalid: list[str] = []

    occupied: dict[tuple[int, int], str] = {}

    for npc in NPCS:
        position = (npc.tile_x, npc.tile_y)

        if position in occupied:
            invalid.append(
                f"{npc.label} shares {position} with {occupied[position]}"
            )
        else:
            occupied[position] = npc.label

        if not (
            0 <= npc.tile_x < map_width
            and 0 <= npc.tile_y < map_height
        ):
            invalid.append(
                f"{npc.label} is outside map bounds at {position}"
            )

    if invalid:
        fail("\n".join(invalid))


def main() -> None:
    for required in (MAP, PO, NPC_DIR):
        if not required.exists():
            fail(f"Missing required path: {required}")

    validate_coordinates()
    slug_map = clone_npc_definitions()
    patch_map(slug_map)
    patch_dialogue()

    print()
    print("Black Belt Dojo first floor installed.")
    print()
    print("Next commands:")
    print("  pybabel compile -d mods/tuxemon/l18n -D base")
    print("  python3 run_tuxemon.py")


if __name__ == "__main__":
    main()
