import asyncio
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_KEYS = (
    "total_requests",
    "total_tasks",
    "total_images",
    "total_visitors",
)


def _connect(db_path: str):
    return sqlite3.connect(db_path, timeout=5)


def init_db(db_path: str):
    path = Path(db_path)
    if path.parent:
        path.parent.mkdir(parents=True, exist_ok=True)

    with _connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stats (
                key TEXT PRIMARY KEY,
                value INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS visitors (
                visitor_id TEXT PRIMARY KEY,
                first_seen TEXT NOT NULL
            )
            """
        )
        for key in DEFAULT_KEYS:
            conn.execute(
                "INSERT OR IGNORE INTO stats (key, value) VALUES (?, 0)", (key,)
            )
        conn.commit()


def increment_stat(db_path: str, key: str, amount: int = 1):
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO stats (key, value)
            VALUES (?, ?)
            ON CONFLICT(key)
            DO UPDATE SET value = value + excluded.value
            """,
            (key, amount),
        )
        conn.commit()


def increment_stats(db_path: str, updates: dict[str, int]):
    with _connect(db_path) as conn:
        for key, amount in updates.items():
            conn.execute(
                """
                INSERT INTO stats (key, value)
                VALUES (?, ?)
                ON CONFLICT(key)
                DO UPDATE SET value = value + excluded.value
                """,
                (key, amount),
            )
        conn.commit()


def record_visitor(db_path: str, visitor_id: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO visitors (visitor_id, first_seen) VALUES (?, ?)",
            (visitor_id, now),
        )
        is_new = cursor.rowcount == 1
        if is_new:
            conn.execute(
                "UPDATE stats SET value = value + 1 WHERE key = 'total_visitors'"
            )
        conn.commit()
    return is_new


def get_stats(db_path: str):
    stats = {key: 0 for key in DEFAULT_KEYS}
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT key, value FROM stats").fetchall()
    for key, value in rows:
        stats[key] = value
    return stats


async def init_db_async(db_path: str):
    await asyncio.to_thread(init_db, db_path)


async def increment_stat_async(db_path: str, key: str, amount: int = 1):
    await asyncio.to_thread(increment_stat, db_path, key, amount)


async def increment_stats_async(db_path: str, updates: dict[str, int]):
    await asyncio.to_thread(increment_stats, db_path, updates)


async def record_visitor_async(db_path: str, visitor_id: str) -> bool:
    return await asyncio.to_thread(record_visitor, db_path, visitor_id)


async def get_stats_async(db_path: str):
    return await asyncio.to_thread(get_stats, db_path)
