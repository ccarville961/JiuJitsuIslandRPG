#!/usr/bin/env python3
from __future__ import annotations

import copy
import re
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT = Path.cwd()

MAP_DIR = ROOT / "mods/tuxemon/maps"
NPC_DIR = ROOT / "mods/tuxemon/db/npc"
MONSTER_DIR = ROOT / "mods/tuxemon/db/monster"
ITEM_DIR = ROOT / "mods/tuxemon/db/item"
PO_PATH = ROOT / "mods/tuxemon/l18n/en_US/LC_MESSAGES/base.po"

TOLAND_MAP = MAP_DIR / "dojo2.tmx"
HILL_MAP = MAP_DIR / "dojo3.tmx"

TOLAND_MONSTER = "coach_toland"
HILL_MONSTER = "coach_hill"

TOLAND_NPC = "jji_coach_toland"
HILL_NPC = "jji_coach_hill"

PATCH_PREFIX = "JJI Black Belt Assessment"

TOLAND_DONE = "jji_blackbelt_toland:defeated"
HILL_DONE = "jji_blackbelt_hill:defeated"
REWARDS_DONE = "jji_blackbelt_rewards:granted"

TOLAND_STARTED = "jji_blackbelt_toland:started"
HILL_STARTED = "jji_blackbelt_hill:started"

BLACK_BELT_CANDIDATES = (
    "black_belt",
    "blackbelt",
)

INVITE_CANDIDATES = (
    "mansion_invitation",
    "mansion_invite",
    "black_belt_mansion_invitation",
    "special_invitation",
)

DIALOGUE = {
    "jji_blackbelt_toland_intro": (
        "Coach Toland: Technique is not something you simply remember.\n"
        "Technique is something you become.\n"
        "Show me what your years of training have taught you."
    ),
    "jji_blackbelt_toland_first_win": (
        "Coach Toland: Excellent.\n"
        "Your fundamentals remained strong under pressure.\n"
        "Coach Hill still awaits. Complete his assessment to finish "
        "your Black Belt trial."
    ),
    "jji_blackbelt_toland_final_win": (
        "Coach Toland: Excellent work.\n"
        "You have completed both Black Belt assessments."
    ),
    "jji_blackbelt_toland_after": (
        "Coach Toland: Your assessment with me is complete.\n"
        "A Black Belt is not the end of learning."
    ),
    "jji_blackbelt_hill_intro": (
        "Coach Hill: I have watched you grow through every belt.\n"
        "Now I want to see the practitioner you have become.\n"
        "Show me that you are ready."
    ),
    "jji_blackbelt_hill_first_win": (
        "Coach Hill: Outstanding.\n"
        "You have earned my approval.\n"
        "Coach Toland still awaits. Complete his assessment to finish "
        "your Black Belt trial."
    ),
    "jji_blackbelt_hill_final_win": (
        "Coach Hill: Outstanding.\n"
        "You have completed both Black Belt assessments."
    ),
    "jji_blackbelt_hill_after": (
        "Coach Hill: You have passed my assessment.\n"
        "Keep developing the habits that brought you this far."
    ),
    "jji_blackbelt_ceremony_1": (
        "Coach Hill: Every belt before this represented another step "
        "in your development."
    ),
    "jji_blackbelt_ceremony_2": (
        "Coach Toland: A Black Belt represents what you have proven "
        "through discipline, courage and consistency."
    ),
    "jji_blackbelt_ceremony_3": (
        "Coach Hill: Congratulations.\n"
        "You have earned your Black Belt."
    ),
    "jji_blackbelt_received": (
        "You received the Black Belt!"
    ),
    "jji_mansion_invitation_received": (
        "You received the Mansion Invitation!"
    ),
    "jji_blackbelt_ceremony_4": (
        "Coach Toland: The invitation grants access to the Mansion, "
        "where the island's strongest practitioners gather."
    ),
    "jji_blackbelt_ceremony_5": (
        "Coach Hill: Your journey is not over.\n"
        "In many ways, it is only beginning."
    ),
}


@dataclass(frozen=True)
class Boss:
    key: str
    display_name: str
    monster_slug: str
    npc_slug: str
    environment_slug: str
    map_path: Path
    defeated_var: str
    started_var: str
    other_defeated_var: str
    intro_key: str
    first_win_key: str
    final_win_key: str
    after_key: str


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def save_yaml(path: Path, data: Any) -> None:
    path.write_text(
        yaml.safe_dump(
            data,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def records_from_yaml(path: Path) -> list[dict[str, Any]]:
    try:
        data = load_yaml(path)
    except Exception:
        return []

    if isinstance(data, list):
        return [
            item
            for item in data
            if isinstance(item, dict)
        ]

    if isinstance(data, dict):
        if isinstance(data.get("slug"), str):
            return [data]

        records: list[dict[str, Any]] = []

        for value in data.values():
            if isinstance(value, list):
                records.extend(
                    item
                    for item in value
                    if isinstance(item, dict)
                )

        return records

    return []


def properties(obj: ET.Element) -> list[ET.Element]:
    return obj.findall("./properties/property")


def events_layer(root: ET.Element) -> ET.Element:
    for group in root.findall("objectgroup"):
        if group.get("name", "").lower() == "events":
            return group

    fail("Map has no Events object layer.")


def add_property(
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
    layer: ET.Element,
    object_id: int,
    *,
    name: str,
    x: int,
    y: int,
    actions: list[str],
    conditions: list[str],
    behaviours: list[str] | None = None,
    width: int = 16,
    height: int = 16,
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
            "width": str(width),
            "height": str(height),
        },
    )

    props = ET.SubElement(obj, "properties")

    for index, action in enumerate(actions, start=1):
        add_property(
            props,
            f"act{index * 10}",
            action,
        )

    for index, behaviour in enumerate(
        behaviours or [],
        start=1,
    ):
        add_property(
            props,
            f"behav{index * 10}",
            behaviour,
        )

    for index, condition in enumerate(
        conditions,
        start=1,
    ):
        add_property(
            props,
            f"cond{index * 10}",
            condition,
        )

    return object_id + 1


def recursively_replace_monster(
    value: Any,
    new_monster_slug: str,
) -> tuple[Any, int]:
    """
    Replace monster references inside an existing trainer NPC record.

    The project may represent a trainer's party with fields such as:
      monster: slug
      monsters:
        - slug: slug
      party:
        - monster: slug
      party:
        - slug

    This recursively preserves the source schema while changing the
    owned combat monster.
    """
    replacements = 0

    monster_keys = {
        "monster",
        "monster_slug",
        "species",
        "tuxemon",
    }

    collection_keys = {
        "monsters",
        "party",
        "team",
    }

    def visit(
        node: Any,
        parent_key: str | None = None,
    ) -> Any:
        nonlocal replacements

        if isinstance(node, dict):
            result: dict[str, Any] = {}

            for key, child in node.items():
                key_lower = str(key).lower()

                if (
                    key_lower in monster_keys
                    and isinstance(child, str)
                ):
                    result[key] = new_monster_slug
                    replacements += 1
                    continue

                result[key] = visit(child, key_lower)

            return result

        if isinstance(node, list):
            result_list = []

            for child in node:
                if (
                    parent_key in collection_keys
                    and isinstance(child, str)
                ):
                    result_list.append(new_monster_slug)
                    replacements += 1
                else:
                    result_list.append(
                        visit(child, parent_key)
                    )

            return result_list

        return node

    return visit(value), replacements


def trainer_score(
    path: Path,
    record: dict[str, Any],
) -> int:
    searchable = (
        path.stem
        + "\n"
        + yaml.safe_dump(record, sort_keys=False)
    ).lower()

    score = 0

    for term, points in (
        ("coach_carville", 500),
        ("trainer", 120),
        ("coach", 100),
        ("leader", 80),
        ("combat", 60),
        ("party", 60),
        ("monster", 60),
        ("monsters", 60),
        ("team", 40),
    ):
        if term in searchable:
            score += points

    for risky in (
        "jji_blackbelt_dojo_",
        "test_npc",
        "professor",
        "nurse",
        "merchant",
    ):
        if risky in searchable:
            score -= 100

    return score


def create_coach_overworld_npc(
    *,
    npc_slug: str,
    preferred_sprite_terms: tuple[str, ...],
) -> None:
    """
    Create only an overworld NPC.

    The scripted battle uses the existing monster directly:
        start_battle coach_toland
        start_battle coach_hill

    Therefore, this NPC does not need a party or monster schema.
    """
    destination = NPC_DIR / f"{npc_slug}.yaml"

    candidates: list[
        tuple[int, Path, dict[str, Any]]
    ] = []

    for source_path in sorted(NPC_DIR.glob("*.yaml")):
        if source_path.name.startswith("jji_coach_"):
            continue

        for record in records_from_yaml(source_path):
            template = record.get("template")

            if not isinstance(template, dict):
                continue

            if not isinstance(template.get("slug"), str):
                continue

            searchable = (
                source_path.stem
                + "\n"
                + yaml.safe_dump(
                    record,
                    sort_keys=False,
                )
            ).lower()

            score = 0

            for index, term in enumerate(
                preferred_sprite_terms
            ):
                if term in searchable:
                    score += 200 - index * 10

            if "professor" in searchable:
                score += 80

            if "coach" in searchable:
                score += 70

            if "sensei" in searchable:
                score += 60

            if "trainer" in searchable:
                score += 50

            for unsuitable in (
                "nurse",
                "merchant",
                "child",
                "soldier",
                "magician",
                "wizard",
                "officer",
            ):
                if unsuitable in searchable:
                    score -= 100

            candidates.append(
                (
                    score,
                    source_path,
                    copy.deepcopy(record),
                )
            )

    if not candidates:
        fail(
            "Could not find an NPC definition with a valid "
            "overworld template."
        )

    candidates.sort(
        key=lambda item: (
            -item[0],
            item[1].name,
        )
    )

    _, source_path, npc = candidates[0]

    npc["slug"] = npc_slug

    # Dialogue and battle behaviour are controlled by map events.
    npc["speech"] = {
        "profile": {
            "default": {}
        }
    }

    # Remove inherited combat configuration. The battle is started
    # directly with the existing monster slug.
    for field in (
        "combat",
        "party",
        "team",
        "monster",
        "monsters",
    ):
        npc.pop(field, None)

    backup = destination.with_suffix(
        ".yaml.bak-before-blackbelt-assessment"
    )

    if destination.exists() and not backup.exists():
        shutil.copy2(destination, backup)

    save_yaml(destination, npc)

    template = npc.get("template", {})

    print(
        f"Created overworld NPC {npc_slug} from "
        f"{source_path.name}: "
        f"template={template.get('slug')}, "
        f"sprite={template.get('sprite_name')}"
    )

def discover_item(
    candidates: tuple[str, ...],
    search_terms: tuple[str, ...],
) -> str | None:
    records: list[tuple[str, str, Path]] = []

    for path in sorted(ITEM_DIR.glob("*.yaml")):
        for record in records_from_yaml(path):
            slug = record.get("slug")

            if not isinstance(slug, str):
                continue

            searchable = (
                path.stem
                + "\n"
                + yaml.safe_dump(
                    record,
                    sort_keys=False,
                )
            ).lower()

            records.append(
                (
                    slug,
                    searchable,
                    path,
                )
            )

    for candidate in candidates:
        for slug, _, path in records:
            if slug == candidate:
                print(
                    f"Found item {slug} in {path.name}"
                )
                return slug

    ranked = []

    for slug, searchable, path in records:
        score = sum(
            100 - index * 5
            for index, term in enumerate(search_terms)
            if term in searchable
        )

        if score:
            ranked.append(
                (
                    -score,
                    slug,
                    path,
                )
            )

    if not ranked:
        return None

    ranked.sort()
    _, slug, path = ranked[0]

    print(f"Found item {slug} in {path.name}")
    return slug


def create_invitation_item(
    black_belt_slug: str,
) -> str:
    source_record = None

    for path in ITEM_DIR.glob("*.yaml"):
        for record in records_from_yaml(path):
            if record.get("slug") == black_belt_slug:
                source_record = copy.deepcopy(record)
                break

        if source_record is not None:
            break

    if source_record is None:
        fail(
            "Cannot create Mansion Invitation because the "
            "Black Belt item record could not be loaded."
        )

    invitation_slug = "mansion_invitation"
    invitation = source_record
    invitation["slug"] = invitation_slug

    for key in (
        "effects",
        "modifiers",
        "techniques",
        "conditions",
    ):
        if isinstance(invitation.get(key), list):
            invitation[key] = []

    destination = (
        ITEM_DIR / f"{invitation_slug}.yaml"
    )

    save_yaml(destination, invitation)

    print(
        f"Created item {invitation_slug} by cloning "
        f"the Black Belt item schema."
    )

    return invitation_slug


def map_corpus() -> str:
    chunks = []

    for path in MAP_DIR.glob("*"):
        if path.suffix.lower() not in {
            ".tmx",
            ".yaml",
        }:
            continue

        chunks.append(
            path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        )

    return "\n".join(chunks)


def detect_add_item(
    item_slug: str,
    corpus: str,
) -> str:
    examples = re.findall(
        r'(?:value="|\-\s+)'
        r'(add_item\s+[^"\n<]+)',
        corpus,
    )

    for example in examples:
        args = example.split(None, 1)[1]
        parts = [
            part.strip()
            for part in args.split(",")
        ]

        if len(parts) >= 3 and parts[0] == "player":
            return (
                f"add_item player,{item_slug},1"
            )

        if len(parts) >= 2:
            return f"add_item {item_slug},1"

    return f"add_item player,{item_slug},1"


def collision_rectangles(
    root: ET.Element,
) -> list[tuple[float, float, float, float]]:
    result = []

    for group in root.findall("objectgroup"):
        if "collision" not in (
            group.get("name", "").lower()
        ):
            continue

        for obj in group.findall("object"):
            left = float(obj.get("x", "0"))
            top = float(obj.get("y", "0"))
            width = float(obj.get("width", "0"))
            height = float(obj.get("height", "0"))

            result.append(
                (
                    left,
                    top,
                    left + width,
                    top + height,
                )
            )

    return result


def tile_blocked(
    rectangles: list[
        tuple[float, float, float, float]
    ],
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


def teleport_tiles(
    root: ET.Element,
) -> set[tuple[int, int]]:
    result: set[tuple[int, int]] = set()

    for group in root.findall("objectgroup"):
        for obj in group.findall("object"):
            if not any(
                prop.get("value", "").startswith(
                    "transition_teleport "
                )
                for prop in properties(obj)
            ):
                continue

            x = int(float(obj.get("x", "0"))) // 16
            y = int(float(obj.get("y", "0"))) // 16
            width = max(
                1,
                int(float(obj.get("width", "16")))
                // 16,
            )
            height = max(
                1,
                int(float(obj.get("height", "16")))
                // 16,
            )

            for tx in range(x, x + width):
                for ty in range(y, y + height):
                    result.add((tx, ty))

    return result


def choose_position(
    root: ET.Element,
) -> tuple[int, int]:
    width = int(root.get("width", "0"))
    height = int(root.get("height", "0"))

    rectangles = collision_rectangles(root)
    reserved = teleport_tiles(root)

    target_x = width // 2
    target_y = max(2, height // 3)

    candidates = []

    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if (x, y) in reserved:
                continue

            if tile_blocked(rectangles, x, y):
                continue

            # Ensure the player can stand below the coach.
            if (x, y + 1) in reserved:
                continue

            if tile_blocked(
                rectangles,
                x,
                y + 1,
            ):
                continue

            score = (
                abs(x - target_x) * 4
                + abs(y - target_y) * 3
            )

            candidates.append(
                (
                    score,
                    x,
                    y,
                )
            )

    if not candidates:
        fail(
            "Could not find a clear coach position."
        )

    candidates.sort()
    _, x, y = candidates[0]

    return x, y


def remove_previous_patch(
    events: ET.Element,
) -> None:
    for obj in list(events.findall("object")):
        if obj.get("name", "").startswith(
            PATCH_PREFIX
        ):
            events.remove(obj)


def patch_boss_map(
    boss: Boss,
    black_belt_action: str,
    invitation_action: str,
) -> None:
    backup = boss.map_path.with_suffix(
        ".tmx.bak-before-blackbelt-assessment"
    )

    if not backup.exists():
        shutil.copy2(
            boss.map_path,
            backup,
        )
        print(f"Created backup: {backup}")

    tree = ET.parse(boss.map_path)
    root = tree.getroot()
    events = events_layer(root)

    remove_previous_patch(events)

    coach_x, coach_y = choose_position(root)

    object_ids = [
        int(obj.get("id", "0"))
        for group in root.findall("objectgroup")
        for obj in group.findall("object")
    ]

    next_id = max(object_ids, default=0) + 1

    # Spawn continuously so the coach returns when the player
    # leaves and re-enters the map.
    next_id = add_event(
        events,
        next_id,
        name=(
            f"{PATCH_PREFIX} - "
            f"Spawn {boss.display_name}"
        ),
        x=0,
        y=0,
        actions=[
            (
                f"create_npc {boss.npc_slug},"
                f"{coach_x},{coach_y},stand"
            ),
            (
                f"add_monster {boss.monster_slug},"
                f"50,{boss.npc_slug}"
            ),
            f"char_face {boss.npc_slug},down",
        ],
        conditions=[
            f"not char_exists {boss.npc_slug}",
        ],
    )

    # Deliberate action-button interaction.
    next_id = add_event(
        events,
        next_id,
        name=(
            f"{PATCH_PREFIX} - "
            f"Challenge {boss.display_name}"
        ),
        x=coach_x * 16,
        y=coach_y * 16,
        actions=[
            f"char_face {boss.npc_slug},player",
            "set_variable battle_last_winner:none",
            "set_variable battle_last_loser:none",
            f"translated_dialog {boss.intro_key}",
            f"set_variable {boss.started_var}",
            f"set_environment {boss.environment_slug}",
            f"start_battle {boss.npc_slug},player",
        ],
        conditions=[
            f"not variable_set {boss.defeated_var}",
        ],
        behaviours=[
            f"talk {boss.npc_slug}",
        ],
    )

    # If the player loses, clear the started state so the coach
    # can be challenged again.
    next_id = add_event(
        events,
        next_id,
        name=(
            f"{PATCH_PREFIX} - "
            f"Reset Loss {boss.display_name}"
        ),
        x=0,
        y=0,
        actions=[
            f"clear_variable {boss.started_var.split(':', 1)[0]}",
        ],
        conditions=[
            "is variable_set battle_last_loser:player",
            f"is variable_set {boss.started_var}",
            f"not variable_set {boss.defeated_var}",
        ],
    )

    # First coach defeated.
    next_id = add_event(
        events,
        next_id,
        name=(
            f"{PATCH_PREFIX} - "
            f"First Victory {boss.display_name}"
        ),
        x=0,
        y=0,
        actions=[
            f"set_variable {boss.defeated_var}",
            f"clear_variable {boss.started_var.split(':', 1)[0]}",
            f"char_face {boss.npc_slug},player",
            f"translated_dialog {boss.first_win_key}",
        ],
        conditions=[
            "is variable_set battle_last_winner:player",
            f"is variable_set {boss.started_var}",
            f"not variable_set {boss.defeated_var}",
            f"not variable_set {boss.other_defeated_var}",
        ],
    )

    # Second coach defeated: ceremony and rewards.
    next_id = add_event(
        events,
        next_id,
        name=(
            f"{PATCH_PREFIX} - "
            f"Final Victory {boss.display_name}"
        ),
        x=0,
        y=0,
        actions=[
            f"set_variable {boss.defeated_var}",
            f"clear_variable {boss.started_var.split(':', 1)[0]}",
            f"char_face {boss.npc_slug},player",
            f"translated_dialog {boss.final_win_key}",
            "translated_dialog jji_blackbelt_ceremony_1",
            "translated_dialog jji_blackbelt_ceremony_2",
            "translated_dialog jji_blackbelt_ceremony_3",
            black_belt_action,
            "translated_dialog jji_blackbelt_received",
            invitation_action,
            "translated_dialog jji_mansion_invitation_received",
            "translated_dialog jji_blackbelt_ceremony_4",
            "translated_dialog jji_blackbelt_ceremony_5",
            f"set_variable {REWARDS_DONE}",
        ],
        conditions=[
            "is variable_set battle_last_winner:player",
            f"is variable_set {boss.started_var}",
            f"not variable_set {boss.defeated_var}",
            f"is variable_set {boss.other_defeated_var}",
            f"not variable_set {REWARDS_DONE}",
        ],
    )

    # Post-defeat conversation. No repeated battle.
    next_id = add_event(
        events,
        next_id,
        name=(
            f"{PATCH_PREFIX} - "
            f"After {boss.display_name}"
        ),
        x=coach_x * 16,
        y=coach_y * 16,
        actions=[
            f"char_face {boss.npc_slug},player",
            f"translated_dialog {boss.after_key}",
        ],
        conditions=[
            f"is variable_set {boss.defeated_var}",
        ],
        behaviours=[
            f"talk {boss.npc_slug}",
        ],
    )

    # Recovery event in case the game is interrupted between the
    # second completion flag and the reward sequence.
    next_id = add_event(
        events,
        next_id,
        name=(
            f"{PATCH_PREFIX} - "
            "Reward Recovery"
        ),
        x=0,
        y=0,
        actions=[
            "translated_dialog jji_blackbelt_ceremony_3",
            black_belt_action,
            "translated_dialog jji_blackbelt_received",
            invitation_action,
            "translated_dialog jji_mansion_invitation_received",
            "translated_dialog jji_blackbelt_ceremony_4",
            "translated_dialog jji_blackbelt_ceremony_5",
            f"set_variable {REWARDS_DONE}",
        ],
        conditions=[
            f"is variable_set {TOLAND_DONE}",
            f"is variable_set {HILL_DONE}",
            f"not variable_set {REWARDS_DONE}",
        ],
    )

    root.set("nextobjectid", str(next_id))

    ET.indent(tree, space=" ", level=0)
    tree.write(
        boss.map_path,
        encoding="UTF-8",
        xml_declaration=True,
    )

    ET.parse(boss.map_path)

    print(
        f"Installed {boss.display_name} in "
        f"{boss.map_path.name} at "
        f"({coach_x}, {coach_y})."
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

    indexes = [
        index
        for index, line in enumerate(lines)
        if line == msgid
    ]

    if len(indexes) > 1:
        fail(f"Duplicate PO entry: {key}")

    if not indexes:
        if lines and lines[-1] != "":
            lines.append("")

        lines.extend(
            [
                "# JJI Black Belt Assessment",
                msgid,
                msgstr,
                "",
            ]
        )
        return

    index = indexes[0]
    msgstr_index = index + 1

    while (
        msgstr_index < len(lines)
        and not lines[msgstr_index].startswith(
            "msgstr "
        )
    ):
        msgstr_index += 1

    if msgstr_index >= len(lines):
        fail(f"No msgstr found for {key}")

    end = msgstr_index + 1

    while (
        end < len(lines)
        and lines[end].startswith('"')
    ):
        end += 1

    lines[msgstr_index:end] = [msgstr]


def patch_dialogue() -> None:
    backup = PO_PATH.with_suffix(
        ".po.bak-before-blackbelt-assessment"
    )

    if not backup.exists():
        shutil.copy2(PO_PATH, backup)
        print(f"Created backup: {backup}")

    lines = PO_PATH.read_text(
        encoding="utf-8"
    ).splitlines()

    for key, value in DIALOGUE.items():
        set_po_entry(lines, key, value)

    # Monster and trainer-facing display names.
    set_po_entry(
        lines,
        TOLAND_MONSTER,
        "Coach Toland",
    )
    set_po_entry(
        lines,
        HILL_MONSTER,
        "Coach Hill",
    )
    set_po_entry(
        lines,
        TOLAND_NPC,
        "Coach Toland",
    )
    set_po_entry(
        lines,
        HILL_NPC,
        "Coach Hill",
    )

    lines = [
        line.replace("Coach Dave", "Coach Hill")
        for line in lines
    ]

    PO_PATH.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print("Installed assessment dialogue.")


def main() -> None:
    required = (
        TOLAND_MAP,
        HILL_MAP,
        MONSTER_DIR / f"{TOLAND_MONSTER}.yaml",
        MONSTER_DIR / f"{HILL_MONSTER}.yaml",
        NPC_DIR,
        ITEM_DIR,
        PO_PATH,
    )

    for path in required:
        if not path.exists():
            fail(f"Missing required path: {path}")

    # Create overworld trainer wrappers around the existing bosses.
    create_coach_overworld_npc(
        npc_slug=TOLAND_NPC,
        preferred_sprite_terms=(
            "coach_toland",
            "toland",
            "coach",
            "sensei",
            "professor",
            "disciple",
        ),
    )

    create_coach_overworld_npc(
        npc_slug=HILL_NPC,
        preferred_sprite_terms=(
            "coach_hill",
            "hill",
            "coach",
            "sensei",
            "professor",
            "disciple",
        ),
    )

    black_belt_slug = discover_item(
        BLACK_BELT_CANDIDATES,
        (
            "black belt",
            "black_belt",
            "blackbelt",
        ),
    )

    if black_belt_slug is None:
        fail("No Black Belt item was found.")

    invitation_slug = discover_item(
        INVITE_CANDIDATES,
        (
            "mansion invitation",
            "mansion_invitation",
            "mansion invite",
            "invitation",
        ),
    )

    if invitation_slug is None:
        invitation_slug = create_invitation_item(
            black_belt_slug
        )

    corpus = map_corpus()

    black_belt_action = detect_add_item(
        black_belt_slug,
        corpus,
    )
    invitation_action = detect_add_item(
        invitation_slug,
        corpus,
    )

    print(
        "Black Belt action:",
        black_belt_action,
    )
    print(
        "Invitation action:",
        invitation_action,
    )

    bosses = (
        Boss(
            key="toland",
            display_name="Coach Toland",
            monster_slug=TOLAND_MONSTER,
            npc_slug=TOLAND_NPC,
            environment_slug="talos_gym",
            map_path=TOLAND_MAP,
            defeated_var=TOLAND_DONE,
            started_var=TOLAND_STARTED,
            other_defeated_var=HILL_DONE,
            intro_key="jji_blackbelt_toland_intro",
            first_win_key="jji_blackbelt_toland_first_win",
            final_win_key="jji_blackbelt_toland_final_win",
            after_key="jji_blackbelt_toland_after",
        ),
        Boss(
            key="hill",
            display_name="Coach Hill",
            monster_slug=HILL_MONSTER,
            npc_slug=HILL_NPC,
            environment_slug="icon_gym",
            map_path=HILL_MAP,
            defeated_var=HILL_DONE,
            started_var=HILL_STARTED,
            other_defeated_var=TOLAND_DONE,
            intro_key="jji_blackbelt_hill_intro",
            first_win_key="jji_blackbelt_hill_first_win",
            final_win_key="jji_blackbelt_hill_final_win",
            after_key="jji_blackbelt_hill_after",
        ),
    )

    for boss in bosses:
        patch_boss_map(
            boss,
            black_belt_action,
            invitation_action,
        )

    patch_dialogue()

    print()
    print("Black Belt assessment installed.")
    print("Coach Toland: dojo2.tmx")
    print("Coach Hill: dojo3.tmx")
    print()
    print("Next:")
    print(
        "  msgfmt --check "
        "mods/tuxemon/l18n/en_US/LC_MESSAGES/base.po "
        "-o /tmp/jji-blackbelt-assessment.mo"
    )
    print(
        "  pybabel compile -f "
        "-d mods/tuxemon/l18n -D base"
    )
    print("  python3 run_tuxemon.py")


if __name__ == "__main__":
    main()
