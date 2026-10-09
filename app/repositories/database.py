from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from pathlib import Path

import aiosqlite

from app.core.config import settings

_CREATE_MEMORIES = """
CREATE TABLE IF NOT EXISTS memories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    content         TEXT NOT NULL,
    normalized_content TEXT NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source          TEXT DEFAULT 'text',
    deleted_at      TIMESTAMP NULL
);
"""

_CREATE_TASKS = """
CREATE TABLE IF NOT EXISTS tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    description     TEXT DEFAULT '',
    status          TEXT DEFAULT 'pending',
    due_at          TIMESTAMP NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_INTERACTIONS = """
CREATE TABLE IF NOT EXISTS interactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_action TEXT NOT NULL,
    processing_mode TEXT NOT NULL,
    response_summary TEXT NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_NETWORK_EVENTS = """
CREATE TABLE IF NOT EXISTS network_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    provider        TEXT NOT NULL,
    request_type    TEXT NOT NULL,
    sanitized_query TEXT NOT NULL,
    destination     TEXT NOT NULL,
    success         BOOLEAN NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_MEMORIES_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
USING fts5(content, normalized_content, content=memories, content_rowid=id);
"""

_TRIGGER_INSERT = """
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, content, normalized_content)
    VALUES (new.id, new.content, new.normalized_content);
END;
"""

_TRIGGER_DELETE = """
CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, normalized_content)
    VALUES ('delete', old.id, old.content, old.normalized_content);
END;
"""

_TRIGGER_UPDATE = """
CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, normalized_content)
    VALUES ('delete', old.id, old.content, old.normalized_content);
    INSERT INTO memories_fts(rowid, content, normalized_content)
    VALUES (new.id, new.content, new.normalized_content);
END;
"""


async def init_db() -> None:
    """Create all tables, FTS indexes, and triggers.

    The database file and its parent directories are created automatically
    if they do not already exist.  WAL journal mode is enabled for
    better concurrent-read performance.
    """
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute("PRAGMA journal_mode=WAL;")

        await db.execute(_CREATE_MEMORIES)
        await db.execute(_CREATE_TASKS)
        await db.execute(_CREATE_INTERACTIONS)
        await db.execute(_CREATE_NETWORK_EVENTS)

        await db.execute(_CREATE_MEMORIES_FTS)
        await db.execute(_TRIGGER_INSERT)
        await db.execute(_TRIGGER_DELETE)
        await db.execute(_TRIGGER_UPDATE)

        await db.commit()


@contextlib.asynccontextmanager
async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    """Yield an aiosqlite connection with row_factory set to
    ``aiosqlite.Row`` so columns can be accessed by name."""
    db_path = Path(settings.database_path)
    db = await aiosqlite.connect(str(db_path))
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()
