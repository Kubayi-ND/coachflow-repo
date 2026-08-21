"""Generates backend/app/session_types_generated.py from session-types.json.

Run manually or as part of `uv run` setup:
    python shared/types/scripts/generate_session_types.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "session-types.json"
OUT = HERE.parent.parent.parent / "backend" / "app" / "session_types_generated.py"


def main() -> None:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    session_types = data["sessionTypes"]

    lines = [
        "# AUTO-GENERATED from shared/types/session-types.json. Do not edit by hand.",
        "# Regenerate: python shared/types/scripts/generate_session_types.py",
        "",
        "from enum import Enum",
        "from typing import NamedTuple",
        "",
        "",
        "class SessionType(str, Enum):",
    ]
    for t in session_types:
        lines.append(f'    {t["id"].upper()} = "{t["id"]}"')

    lines += [
        "",
        "",
        "class SessionTypeDefinition(NamedTuple):",
        "    id: SessionType",
        "    label: str",
        "    naming_pattern: str",
        "    lead_time_working_days: int",
        "",
        "",
        "SESSION_TYPES: dict[SessionType, SessionTypeDefinition] = {",
    ]
    for t in session_types:
        lines.append(
            f'    SessionType.{t["id"].upper()}: SessionTypeDefinition('
            f'SessionType.{t["id"].upper()}, {t["label"]!r}, {t["namingPattern"]!r}, {t["leadTimeWorkingDays"]}),'
        )
    lines.append("}")
    lines.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {OUT}")


if __name__ == "__main__":
    main()
