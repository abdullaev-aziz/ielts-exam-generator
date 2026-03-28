"""Blueprint history store — tracks previously generated blueprints so
Agent 1 can avoid reusing the same names, scenarios, and role combos.

Uses asyncpg for async PostgreSQL access.
"""

import logging
from datetime import datetime, timezone

import asyncpg

from listening.agents.part1.config import DATABASE_URL

logger = logging.getLogger("ielts.pipeline")

_pool: asyncpg.Pool | None = None


async def _get_pool() -> asyncpg.Pool:
    """Return a shared connection pool, creating it on first call."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=3)
        async with _pool.acquire() as con:
            await con.execute("""
                CREATE TABLE IF NOT EXISTS blueprints (
                    id SERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL,
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
    return _pool


async def get_exclusion_context(limit: int = 30) -> str:
    """Return a formatted exclusion list from the last *limit* blueprints."""
    pool = await _get_pool()
    rows = await pool.fetch(
        "SELECT topic, scenario, speaker_a_name, speaker_b_name, "
        "speaker_a_role, speaker_b_role, speaker_a_gender, speaker_b_gender "
        "FROM blueprints ORDER BY id DESC LIMIT $1",
        limit,
    )

    if not rows:
        return ""

    names = sorted({n for r in rows for n in (r["speaker_a_name"], r["speaker_b_name"])})
    scenarios = [r["scenario"] for r in rows]
    combos = sorted({
        f"{r['speaker_a_gender']}={r['speaker_a_role']} / "
        f"{r['speaker_b_gender']}={r['speaker_b_role']}"
        for r in rows
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
    pool = await _get_pool()
    await pool.execute(
        "INSERT INTO blueprints "
        "(created_at, topic, scenario, speaker_a_name, speaker_b_name, "
        " speaker_a_role, speaker_b_role, speaker_a_gender, speaker_b_gender) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
        datetime.now(timezone.utc),
        blueprint.topic,
        blueprint.scenario,
        blueprint.speaker_a_name,
        blueprint.speaker_b_name,
        blueprint.speaker_a_role,
        blueprint.speaker_b_role,
        blueprint.speaker_a_gender,
        blueprint.speaker_b_gender,
    )
