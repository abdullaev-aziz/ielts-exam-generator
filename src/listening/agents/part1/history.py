"""Blueprint history store — tracks previously generated blueprints so
Agent 1 can avoid reusing the same names, scenarios, and role combos.

Uses aiosqlite for async SQLite access.
"""

import logging
from datetime import datetime, timezone

import aiosqlite

from listening.agents.part1.config import HISTORY_DB

logger = logging.getLogger("ielts.pipeline")


async def _init_history_db(db: aiosqlite.Connection) -> None:
    """Create the blueprints history table if it doesn't exist."""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS blueprints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            topic TEXT NOT NULL,
            scenario TEXT NOT NULL,
            speaker_a_name TEXT NOT NULL,
            speaker_b_name TEXT NOT NULL,
            speaker_a_role TEXT NOT NULL,
            speaker_b_role TEXT NOT NULL,
            speaker_a_gender TEXT NOT NULL,
            speaker_b_gender TEXT NOT NULL
        )
    """)
    await db.commit()


async def get_exclusion_context(limit: int = 30) -> str:
    """Return a formatted exclusion list from the last *limit* blueprints."""
    async with aiosqlite.connect(HISTORY_DB) as db:
        await _init_history_db(db)
        cursor = await db.execute(
            "SELECT topic, scenario, speaker_a_name, speaker_b_name, "
            "speaker_a_role, speaker_b_role, speaker_a_gender, speaker_b_gender "
            "FROM blueprints ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()

    if not rows:
        return ""

    names = sorted({n for r in rows for n in (r[2], r[3])})
    scenarios = [r[1] for r in rows]
    combos = sorted({
        f"{r[6]}={r[4]} / {r[7]}={r[5]}" for r in rows
    })

    lines = ["Previously used — DO NOT reuse these:"]
    lines.append(f"- Names: {', '.join(names)}")
    lines.append("- Scenarios:")
    for s in scenarios:
        lines.append(f'  \u2022 "{s}"')
    lines.append(f"- Role-gender combos: {'; '.join(combos)}")
    return "\n".join(lines)


async def save_blueprint(blueprint) -> None:
    """Persist a completed blueprint for future exclusion.

    Accepts any object with the IELTSBlueprint fields (duck-typed to
    avoid circular imports).
    """
    async with aiosqlite.connect(HISTORY_DB) as db:
        await _init_history_db(db)
        await db.execute(
            "INSERT INTO blueprints "
            "(created_at, topic, scenario, speaker_a_name, speaker_b_name, "
            " speaker_a_role, speaker_b_role, speaker_a_gender, speaker_b_gender) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                blueprint.topic,
                blueprint.scenario,
                blueprint.speaker_a_name,
                blueprint.speaker_b_name,
                blueprint.speaker_a_role,
                blueprint.speaker_b_role,
                blueprint.speaker_a_gender,
                blueprint.speaker_b_gender,
            ),
        )
        await db.commit()
