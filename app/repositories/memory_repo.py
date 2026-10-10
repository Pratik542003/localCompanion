from __future__ import annotations

import re
from datetime import datetime

from app.domain.interfaces import MemoryRepository
from app.domain.models import Memory
from app.repositories.database import get_db


_STOP_WORDS = frozenset(
    "a an the is are was were am be been being do does did "
    "have has had having will would shall should can could may might must "
    "i me my mine we us our ours you your yours he him his she her hers "
    "it its they them their theirs this that these those "
    "what when where who whom which how why "
    "of in on at to for with by from about into through during before after "
    "and or but not no nor so yet if then else "
    "is there here all any each every both few many much some such "
    "get got tell told know knew find time date please".split()
)


def _sanitize_fts_query(query: str) -> str:
    sanitized = re.sub(r"[^\w\s]", " ", query)
    tokens = [t for t in sanitized.split() if t.lower() not in _STOP_WORDS]
    if not tokens:
        return ""
    return " AND ".join('"' + t + '"' for t in tokens)


class SQLiteMemoryRepository(MemoryRepository):

    async def save(self, memory: Memory) -> Memory:
        now = datetime.now().isoformat()
        async with get_db() as db:
            cursor = await db.execute(
                """
                INSERT INTO memories (content, normalized_content, created_at,
                                      updated_at, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    memory.content,
                    memory.normalized_content,
                    now,
                    now,
                    memory.source,
                ),
            )
            await db.commit()
            memory.id = cursor.lastrowid
            memory.created_at = datetime.fromisoformat(now)
            memory.updated_at = datetime.fromisoformat(now)
        return memory

    async def search(self, query: str) -> list[Memory]:
        fts_query = _sanitize_fts_query(query)
        if not fts_query:
            return []

        async with get_db() as db:
            try:
                cursor = await db.execute(
                    """
                    SELECT m.*
                    FROM memories m
                    JOIN memories_fts fts ON m.id = fts.rowid
                    WHERE memories_fts MATCH ?
                      AND m.deleted_at IS NULL
                    ORDER BY rank
                    """,
                    (fts_query,),
                )
                rows = await cursor.fetchall()
            except Exception:
                pattern = f"%{query}%"
                cursor = await db.execute(
                    """
                    SELECT * FROM memories
                    WHERE deleted_at IS NULL
                      AND (content LIKE ? OR normalized_content LIKE ?)
                    ORDER BY created_at DESC
                    """,
                    (pattern, pattern),
                )
                rows = await cursor.fetchall()
        return [_row_to_memory(row) for row in rows]

    async def get_all(self) -> list[Memory]:
        async with get_db() as db:
            cursor = await db.execute(
                """
                SELECT * FROM memories
                WHERE deleted_at IS NULL
                ORDER BY created_at DESC
                """
            )
            rows = await cursor.fetchall()
        return [_row_to_memory(row) for row in rows]

    async def soft_delete(self, memory_id: int) -> bool:
        now = datetime.now().isoformat()
        async with get_db() as db:
            cursor = await db.execute(
                """
                UPDATE memories SET deleted_at = ?
                WHERE id = ? AND deleted_at IS NULL
                """,
                (now, memory_id),
            )
            await db.commit()
            return cursor.rowcount > 0


def _row_to_memory(row: dict) -> Memory:
    return Memory(
        id=row["id"],
        content=row["content"],
        normalized_content=row["normalized_content"],
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
        source=row["source"],
        deleted_at=_parse_dt(row["deleted_at"]),
    )


def _parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)
