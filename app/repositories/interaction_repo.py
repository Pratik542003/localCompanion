from __future__ import annotations

from app.domain.interfaces import InteractionRepository
from app.repositories.database import get_db


class SQLiteInteractionRepository(InteractionRepository):
    """Concrete interaction repository backed by SQLite."""

    async def record(self, action: str, mode: str, summary: str) -> None:
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO interactions (detected_action, processing_mode,
                                          response_summary)
                VALUES (?, ?, ?)
                """,
                (action, mode, summary),
            )
            await db.commit()
