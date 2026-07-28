from __future__ import annotations

from pathlib import Path
from typing import Any
import re
import sys

try:
    import yaml
except ImportError:
    print("PyYAML is required. Install it with:")
    print("python3 -m pip install PyYAML")
    sys.exit(1)


ROOT = Path("mods/tuxemon")
ENCOUNTER_DIR = ROOT / "db" / "encounter"
MONSTER_DIR = ROOT / "db" / "monster"
MAP_DIR = ROOT / "maps"
BATTLE_DIR = ROOT / "gfx" / "sprites" / "battle"
REPORT_PATH = Path("random_encounter_sprite_audit.txt")


def load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_load_error": str(exc)}


def collect_monsters(value: Any) -> set[str]:
    monsters: set[str] = set()

    if isinstance(value, dict):
        for key, child in value.items():
            if key == "monster" and isinstance(child, str):
                monsters.add(child.strip())
            else:
                monsters.update(collect_monsters(child))

    elif isinstance(value, list):
        for child in value:
            monsters.update(collect_monsters(child))

    return monsters


def get_monster_sheet(monster_slug: str) -> tuple[str, str]:
    monster_path = MONSTER_DIR / f"{monster_slug}.yaml"

    if not monster_path.exists():
        return "MISSING MONSTER YAML", "missing"

    data = load_yaml(monster_path)

    if not isinstance(data, dict):
        return "INVALID MONSTER YAML", "missing"

    sprites = data.get("sprites", {})
    sheet = sprites.get("sheet") if isinstance(sprites, dict) else None

    if not sheet:
        return "NO SHEET CONFIGURED", "missing"

    relative_sheet = str(sheet)
    sheet_path = ROOT / f"{relative_sheet}.png"

    if sheet_path.exists():
        return relative_sheet, "exists"

    return relative_sheet, "missing"


def find_map_references(encounter_slug: str) -> list[str]:
    references: list[str] = []
    pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(encounter_slug)}(?![A-Za-z0-9_])")

    for map_path in sorted(MAP_DIR.glob("*.tmx")):
        try:
            text = map_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        if pattern.search(text):
            references.append(map_path.name)

    return references


def find_candidate_art(monster_slug: str) -> list[str]:
    candidates: list[str] = []

    for path in sorted(BATTLE_DIR.glob("*.png")):
        lower_name = path.name.lower()

        if monster_slug.lower() in lower_name:
            candidates.append(path.name)

    return candidates


def main() -> None:
    if not ENCOUNTER_DIR.exists():
        print(f"Encounter directory not found: {ENCOUNTER_DIR}")
        sys.exit(1)

    lines: list[str] = []
    all_monsters: set[str] = set()

    encounter_files = sorted(ENCOUNTER_DIR.glob("*.yaml"))

    lines.append("RANDOM ENCOUNTER SPRITE AUDIT")
    lines.append("=" * 80)
    lines.append(f"Encounter files found: {len(encounter_files)}")
    lines.append("")

    for encounter_path in encounter_files:
        encounter_slug = encounter_path.stem
        data = load_yaml(encounter_path)

        if isinstance(data, dict) and "_load_error" in data:
            lines.append(f"ENCOUNTER: {encounter_slug}")
            lines.append(f"  YAML ERROR: {data['_load_error']}")
            lines.append("")
            continue

        monsters = sorted(collect_monsters(data))
        all_monsters.update(monsters)
        maps = find_map_references(encounter_slug)

        lines.append(f"ENCOUNTER: {encounter_slug}")
        lines.append(
            "  MAPS: " + (", ".join(maps) if maps else "No direct map reference found")
        )

        if not monsters:
            lines.append("  MONSTERS: None found")
            lines.append("")
            continue

        for monster_slug in monsters:
            sheet, status = get_monster_sheet(monster_slug)
            candidates = find_candidate_art(monster_slug)

            lines.append(f"  MONSTER: {monster_slug}")
            lines.append(f"    SHEET: {sheet}")
            lines.append(f"    SHEET STATUS: {status}")
            lines.append(
                "    MATCHING ART: "
                + (", ".join(candidates) if candidates else "None found")
            )

        lines.append("")

    lines.append("=" * 80)
    lines.append(f"UNIQUE RANDOM-ENCOUNTER MONSTERS: {len(all_monsters)}")
    lines.append("")

    for monster_slug in sorted(all_monsters):
        sheet, status = get_monster_sheet(monster_slug)
        lines.append(f"{monster_slug} | {sheet} | {status}")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Created: {REPORT_PATH.resolve()}")
    print(f"Encounter files checked: {len(encounter_files)}")
    print(f"Unique encounter monsters found: {len(all_monsters)}")


if __name__ == "__main__":
    main()
