#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MAP_PATH = ROOT / "mods/tuxemon/maps/mansion.tmx"
NPC_DIR = ROOT / "mods/tuxemon/db/npc"
ITEM_DIR = ROOT / "mods/tuxemon/db/item"
PO_PATH = ROOT / "mods/tuxemon/l18n/en_US/LC_MESSAGES/base.po"

BACKUP_PATH = MAP_PATH.with_suffix(".tmx.before_koth_blackbelt_ceremony")

INSTALL_PREFIX = "JJI KOTH Black Belt Ceremony"
CEREMONY_VARIABLE = "jji_koth_blackbelt_ceremony:complete"


# ---------------------------------------------------------------------
# Verified project NPC slugs
# ---------------------------------------------------------------------
#
# D1 Elliott previously battles through classic_gym_leader_mila.
# Brown Belt Bruce previously battles through brownbelt_tavern_enforcer.
# Coach Conleth already exists as brownbelt_tavern_coach_conleth.
#
# The CEO slug is verified separately below before installation.
# ---------------------------------------------------------------------

CAST = {
    "ceo": "aeble",
    "coach_carville": "coach_carville",
    "coach_toland": "jji_coach_toland",
    "coach_hill": "jji_coach_hill",
    "scramble_steve": "scramble_steve",
    "sensei_duncan": "sensai_duncan",
    "d1_elliott": "classic_gym_leader_mila",
    "brown_belt_bruce": "brownbelt_tavern_enforcer",
    "coach_conleth": "brownbelt_tavern_coach_conleth",
}

OFFICER_TEMPLATE = "jji_mansion_gate_officer_left"


# ---------------------------------------------------------------------
# Mansion tile positions
#
# Coordinates use the 16×16 map grid.
#
# Change only these constants if testing shows that a character needs
# moved by one or two tiles.
# ---------------------------------------------------------------------

CEO_POSITION = (10, 8)
CEO_FINAL_POSITION = (10, 5)

COACH_POSITIONS = {
    "coach_carville": (9, 10),
    "brown_belt_bruce": (11, 10),
    "coach_toland": (9, 11),
    "coach_conleth": (11, 11),
    "coach_hill": (9, 12),
    "sensei_duncan": (11, 12),
    "scramble_steve": (9, 13),
    "d1_elliott": (11, 13),
}

OFFICER_POSITIONS = [
    (2, 4),
    (15, 4),
    (3, 8),
    (16, 8),
    (3, 12),
    (16, 12),
    (2, 15),
    (15, 15),
]

# Three tiles across the lower central entrance.
ENTRY_TRIGGER = {
    "x": 9,
    "y": 16,
    "width": 3,
    "height": 2,
}

# Player stops below the assembled coaches.
PLAYER_CEREMONY_POSITION = (10, 9)


DIALOGUE = {
    "black_belt": "Black Belt",

    "black_belt_description":
        "The rank of a true Jiu-Jitsu expert. Grants entry to King Of The Hill.",

    

    "jji_koth_ceo_after_1":
        "KOTH CEO: My officers inform me Coach Atlas has entered King Of The Hill.",

    "jji_koth_ceo_after_2":
        "KOTH CEO: He is waiting for challengers.",

    "jji_koth_ceo_after_3":
        "KOTH CEO: This is your chance... go and get your revenge!",

    "jji_koth_blackbelt_received":
        "You received the Black Belt!",

    "jji_koth_ceo_ceremony_1":
        "KOTH CEO: Welcome. You have overcome every challenge placed before you.",

    "jji_koth_ceo_ceremony_2":
        "KOTH CEO: Today, before these respected coaches, I recognise your dedication.",

    "jji_koth_ceo_ceremony_3":
        "KOTH CEO: It is my honour to award you your Black Belt.",

    "jji_koth_ceo_ceremony_4":
        "KOTH CEO: One challenge remains: King Of The Hill.",

    "jji_koth_ceo_ceremony_5":
        "KOTH CEO: Please speak with me after.",

    # removed old CEO dialogue
#"jji_koth_ceo_after":
        "KOTH CEO: My officers inform me Coach Atlas has entered King Of The Hill. This is your opportunity to get your revenge!",

    "jji_koth_carville_thanks":
        "Coach Carville: You earned every belt. Now go finish what you started.",

    "jji_koth_toland_thanks":
        "Coach Toland: The Black Belt is only the beginning. Keep learning.",

    "jji_koth_hill_thanks":
        "Coach Hill: Hard work always wins. Congratulations.",

    "jji_koth_scramble_thanks":
        "Scramble Steve: I always knew you would get there!",

    "jji_koth_duncan_thanks":
        "Sensei Duncan: Wear that belt with humility.",

    "jji_koth_elliott_thanks":
        "D1 Elliott: You earned everyone's respect. Keep Oil Checking!",

    "jji_koth_bruce_thanks":
        "Brown Belt Bruce: Guess I cannot call you kid anymore.",

    "jji_koth_conleth_thanks":
        "Coach Conleth: I am proud of you. Good luck with King Of The Hill.",
}


def fail(message: str) -> None:
    raise SystemExit(f"\nERROR: {message}\n")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def yaml_slug(path: Path) -> str | None:
    match = re.search(
        r"^slug:\s*([^\s#]+)",
        read(path),
        flags=re.MULTILINE,
    )
    return match.group(1) if match else None


def find_slug_in_npc_database(slug: str) -> Path | None:
    """
    Finds a slug even when it is stored inside a shared multi-NPC YAML file.
    """

    pattern = re.compile(
        rf"(?m)^\s*(?:-\s*)?slug:\s*{re.escape(slug)}\s*$"
    )

    for path in sorted(NPC_DIR.glob("*.yaml")):
        if pattern.search(read(path)):
            return path

    # Some project NPC files use the filename as the slug while the template
    # data lives under a nested structure.
    direct = NPC_DIR / f"{slug}.yaml"

    if direct.exists():
        return direct

    return None


def verify_cast() -> dict[str, Path]:
    sources: dict[str, Path] = {}

    for role, slug in CAST.items():
        source = find_slug_in_npc_database(slug)

        if source is None:
            fail(
                f"Required NPC slug '{slug}' for '{role}' was not found "
                f"inside {NPC_DIR}."
            )

        sources[role] = source
        print(f"{role:20} -> {slug:36} ({source.name})")

    return sources


def verify_ceo(source: Path) -> None:
    """
    Prevents the earlier fuzzy-search problem from silently assigning an
    unrelated NPC as the CEO.

    The aeble definition must contain a KOTH/CEO-related label somewhere in
    its data. If it does not, installation stops before modifying the map.
    """

    text = read(source).lower()

    identity_terms = (
        "ceo",
        "king of the hill",
        "koth",
    )

    if any(term in text for term in identity_terms):
        print(f"CEO identity verified from: {source}")
        return

    print()
    print("The current aeble NPC definition is:")
    print("------------------------------------------------------------")
    print(read(source).rstrip())
    print("------------------------------------------------------------")
    print()

    fail(
        "The installer cannot verify that 'aeble' is the KOTH CEO. "
        "No files were modified. Inspect the definition printed above."
    )


def create_black_belt_item() -> None:
    source_candidates = [
        ITEM_DIR / "brown_belt.yaml",
        ITEM_DIR / "blue_belt.yaml",
    ]

    source = next(
        (candidate for candidate in source_candidates if candidate.exists()),
        None,
    )

    if source is None:
        fail(
            "Could not create black_belt.yaml because neither "
            "brown_belt.yaml nor blue_belt.yaml exists."
        )

    target = ITEM_DIR / "black_belt.yaml"
    text = read(source)

    old_slug = yaml_slug(source)

    if old_slug:
        text = re.sub(
            r"^slug:\s*[^\s#]+",
            "slug: black_belt",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        text = "slug: black_belt\n" + text

    # Replace internal translation/resource references while preserving the
    # working item schema and its existing sprite.
    for source_name in (
        "brown_belt",
        "blue_belt",
    ):
        text = text.replace(source_name, "black_belt")

    # A progression belt must not be consumed.
    if re.search(r"(?m)^\s*consumable:\s*", text):
        text = re.sub(
            r"(?m)^(\s*consumable:\s*).*$",
            r"\1false",
            text,
        )

    # Remove sale values if the template includes them.
    text = re.sub(
        r"(?m)^\s*(?:sell_price|resale_price):.*\n?",
        "",
        text,
    )

    target.write_text(text.rstrip() + "\n", encoding="utf-8")

    print(f"Created Black Belt item from {source.name}: {target}")


def clone_officers(officer_source: Path) -> list[str]:
    source_text = read(officer_source)
    created_slugs: list[str] = []

    for index, _position in enumerate(OFFICER_POSITIONS, start=1):
        slug = f"jji_koth_mansion_officer_{index:02d}"
        target = NPC_DIR / f"{slug}.yaml"

        text = source_text

        if re.search(r"(?m)^slug:\s*", text):
            text = re.sub(
                r"(?m)^slug:\s*[^\s#]+",
                f"slug: {slug}",
                text,
                count=1,
            )
        else:
            text = f"slug: {slug}\n{text}"

        target.write_text(text.rstrip() + "\n", encoding="utf-8")
        created_slugs.append(slug)

    print(f"Created {len(created_slugs)} ceremonial officer definitions.")
    return created_slugs


def ensure_object_group(root: ET.Element) -> ET.Element:
    for group in root.findall("objectgroup"):
        if group.get("name", "").strip().lower() == "events":
            return group

    ids = [
        int(node.get("id", "0"))
        for node in root.findall("objectgroup")
        if node.get("id", "0").isdigit()
    ]

    return ET.SubElement(
        root,
        "objectgroup",
        {
            "id": str(max(ids or [0]) + 1),
            "name": "Events",
        },
    )


def next_object_id(root: ET.Element) -> int:
    values: list[int] = []

    for obj in root.findall(".//object"):
        raw = obj.get("id", "0")

        if raw.isdigit():
            values.append(int(raw))

    return max(values or [0]) + 1


def remove_previous_install(events: ET.Element) -> int:
    removed = 0

    for obj in list(events.findall("object")):
        if obj.get("name", "").startswith(INSTALL_PREFIX):
            events.remove(obj)
            removed += 1

    return removed


def add_event(
    events: ET.Element,
    object_id: int,
    name: str,
    tile_x: int,
    tile_y: int,
    *,
    tile_width: int = 1,
    tile_height: int = 1,
    actions: list[str] | None = None,
    conditions: list[str] | None = None,
    behaviours: list[str] | None = None,
    tile_size: int = 16,
) -> int:
    obj = ET.SubElement(
        events,
        "object",
        {
            "id": str(object_id),
            "name": f"{INSTALL_PREFIX} - {name}",
            "type": "event",
            "x": str(tile_x * tile_size),
            "y": str(tile_y * tile_size),
            "width": str(tile_width * tile_size),
            "height": str(tile_height * tile_size),
        },
    )

    props = ET.SubElement(obj, "properties")

    for index, action in enumerate(actions or [], start=1):
        ET.SubElement(
            props,
            "property",
            {
                "name": f"act{index * 10:03d}",
                "value": action,
            },
        )

    for index, condition in enumerate(conditions or [], start=1):
        ET.SubElement(
            props,
            "property",
            {
                "name": f"cond{index * 10:03d}",
                "value": condition,
            },
        )

    for index, behaviour in enumerate(behaviours or [], start=1):
        ET.SubElement(
            props,
            "property",
            {
                "name": f"behav{index * 10:03d}",
                "value": behaviour,
            },
        )

    return object_id + 1


def build_spawn_actions(officer_slugs: list[str]) -> list[str]:
    actions: list[str] = []

    ceo_x, ceo_y = CEO_POSITION

    actions.extend([
        f"create_npc {CAST['ceo']},{ceo_x},{ceo_y},stand",
        f"char_face {CAST['ceo']},down",
    ])

    for role, (x, y) in COACH_POSITIONS.items():
        slug = CAST[role]

        actions.extend([
            f"create_npc {slug},{x},{y},stand",
            f"char_face {slug},down",
        ])

    for slug, (x, y) in zip(
        officer_slugs,
        OFFICER_POSITIONS,
        strict=True,
    ):
        facing = "right" if x < CEO_POSITION[0] else "left"

        actions.extend([
            f"create_npc {slug},{x},{y},stand",
            f"char_face {slug},{facing}",
        ])

    return actions


def install_map(officer_slugs: list[str]) -> None:
    tree = ET.parse(MAP_PATH)
    root = tree.getroot()

    tile_width = int(root.get("tilewidth", "16"))
    tile_height = int(root.get("tileheight", "16"))

    if tile_width != tile_height:
        fail(
            f"Mansion uses non-square tiles: {tile_width}×{tile_height}."
        )

    events = ensure_object_group(root)
    removed = remove_previous_install(events)

    if removed:
        print(f"Removed {removed} previous ceremony events.")

    object_id = next_object_id(root)

    # Spawn the complete cast.
    object_id = add_event(
        events,
        object_id,
        "Spawn Cast",
        0,
        0,
        actions=build_spawn_actions(officer_slugs),
        conditions=[
            f"not char_exists {CAST['ceo']}",
        ],
        tile_size=tile_width,
    )

    # Short locked CEO ceremony.
    ceremony_actions = [
        "set_variable jji_koth_blackbelt_ceremony_started:yes",
        "lock_controls",
        "char_face player,up",
        (
            f"pathfind player,"
            f"{PLAYER_CEREMONY_POSITION[0]},"
            f"{PLAYER_CEREMONY_POSITION[1]}"
        ),
        "wait 0.4",
    ]

    # Everyone turns toward the centre.
    for role in COACH_POSITIONS:
        ceremony_actions.append(
            f"char_face {CAST[role]},player"
        )

    ceremony_actions.extend([
        f"char_face {CAST['ceo']},player",
        "wait 0.3",
        "translated_dialog jji_koth_ceo_ceremony_1",
        "translated_dialog jji_koth_ceo_ceremony_2",
        "translated_dialog jji_koth_ceo_ceremony_3",
        "add_item black_belt,1",
        "translated_dialog jji_koth_blackbelt_received",
        "translated_dialog jji_koth_ceo_ceremony_4",
        "translated_dialog jji_koth_ceo_ceremony_5",
        "char_move aeble,up 3",
        "char_face aeble,down",
        f"set_variable {CEREMONY_VARIABLE}",
        "clear_variable jji_koth_blackbelt_ceremony_started",
        "unlock_controls",
    ])

    object_id = add_event(
        events,
        object_id,
        "Award Black Belt",
        ENTRY_TRIGGER["x"],
        ENTRY_TRIGGER["y"],
        tile_width=ENTRY_TRIGGER["width"],
        tile_height=ENTRY_TRIGGER["height"],
        actions=ceremony_actions,
        conditions=[
            "is char_at player",
            "not has_item player,black_belt",
            f"not variable_set {CEREMONY_VARIABLE}",
            "not variable_set jji_koth_blackbelt_ceremony_started:yes",
        ],
        tile_size=tile_width,
    )

    # Safety event in case a save was interrupted at the end of the ceremony.

    # CEO optional post-ceremony conversation.
    object_id = add_event(
        events,
        object_id,
        "CEO Optional Dialogue",
        CEO_FINAL_POSITION[0],
        CEO_FINAL_POSITION[1],
        actions=[
            f"char_face {CAST['ceo']},player",
            "translated_dialog jji_koth_ceo_after_1",
            "translated_dialog jji_koth_ceo_after_2",
            "translated_dialog jji_koth_ceo_after_3",
        ],
        conditions=[
            f"is variable_set {CEREMONY_VARIABLE}",
        ],
        behaviours=[
            f"talk {CAST['ceo']}",
        ],
        tile_size=tile_width,
    )

    optional_dialogue = {
        "coach_carville": "jji_koth_carville_thanks",
        "coach_toland": "jji_koth_toland_thanks",
        "coach_hill": "jji_koth_hill_thanks",
        "scramble_steve": "jji_koth_scramble_thanks",
        "sensei_duncan": "jji_koth_duncan_thanks",
        "d1_elliott": "jji_koth_elliott_thanks",
        "brown_belt_bruce": "jji_koth_bruce_thanks",
        "coach_conleth": "jji_koth_conleth_thanks",
    }

    for role, dialogue_key in optional_dialogue.items():
        x, y = COACH_POSITIONS[role]
        slug = CAST[role]

        object_id = add_event(
            events,
            object_id,
            f"{role} Optional Dialogue",
            x,
            y,
            actions=[
                f"char_face {slug},player",
                f"translated_dialog {dialogue_key}",
            ],
            conditions=[
                f"is variable_set {CEREMONY_VARIABLE}",
            ],
            behaviours=[
                f"talk {slug}",
            ],
            tile_size=tile_width,
        )

    current_next = int(root.get("nextobjectid", "1"))
    root.set("nextobjectid", str(max(current_next, object_id)))

    if not BACKUP_PATH.exists():
        shutil.copy2(MAP_PATH, BACKUP_PATH)
        print(f"Created map backup: {BACKUP_PATH}")

    ET.indent(tree, space=" ", level=0)

    tree.write(
        MAP_PATH,
        encoding="UTF-8",
        xml_declaration=True,
    )

    ET.parse(MAP_PATH)

    print(f"Installed ceremony into: {MAP_PATH}")


def escape_po(value: str) -> str:
    return (
        value
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
    )


def set_po_entry(content: str, msgid: str, msgstr: str) -> str:
    escaped_id = re.escape(msgid)
    escaped_value = escape_po(msgstr)

    pattern = re.compile(
        rf'(?m)^msgid "{escaped_id}"\n'
        rf'msgstr "(?:[^"\\]|\\.)*"\n?'
    )

    replacement = (
        f'msgid "{msgid}"\n'
        f'msgstr "{escaped_value}"\n'
    )

    if pattern.search(content):
        return pattern.sub(replacement, content, count=1)

    return content.rstrip() + "\n\n" + replacement


def install_dialogue() -> None:
    content = read(PO_PATH)

    for key, value in DIALOGUE.items():
        content = set_po_entry(content, key, value)

    PO_PATH.write_text(
        content.rstrip() + "\n",
        encoding="utf-8",
    )

    print(f"Installed dialogue into: {PO_PATH}")


def restore() -> None:
    if not BACKUP_PATH.exists():
        fail(f"No backup exists at {BACKUP_PATH}.")

    shutil.copy2(BACKUP_PATH, MAP_PATH)

    for path in NPC_DIR.glob("jji_koth_mansion_officer_*.yaml"):
        path.unlink()

    print(f"Restored map from: {BACKUP_PATH}")
    print("Removed generated ceremonial officer definitions.")
    print("The Black Belt item and translations were left intact.")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--restore",
        action="store_true",
        help="Restore the mansion map and remove generated officers.",
    )

    args = parser.parse_args()

    if args.restore:
        restore()
        return

    for required in (
        MAP_PATH,
        NPC_DIR,
        ITEM_DIR,
        PO_PATH,
    ):
        if not required.exists():
            fail(f"Required project path is missing: {required}")

    print("Verifying ceremony cast...")
    sources = verify_cast()
    verify_ceo(sources["ceo"])

    officer_source = find_slug_in_npc_database(OFFICER_TEMPLATE)

    if officer_source is None:
        fail(
            f"Officer template '{OFFICER_TEMPLATE}' could not be found."
        )

    print()
    create_black_belt_item()
    officer_slugs = clone_officers(officer_source)
    install_map(officer_slugs)
    install_dialogue()

    print()
    print("KOTH Black Belt ceremony installed successfully.")
    print()
    print("Next commands:")
    print("  pybabel compile -d mods/tuxemon/l18n -D base")
    print("  python3 run_tuxemon.py")


if __name__ == "__main__":
    main()
