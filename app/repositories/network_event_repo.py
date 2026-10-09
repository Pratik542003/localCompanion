from __future__ import annotations

from datetime import datetime

from app.domain.interfaces import NetworkEventRepository
from app.domain.models import NetworkEvent
from app.repositories.database import get_db


class SQLiteNetworkEventRepository(NetworkEventRepository):
    """Concrete network-event repository backed by SQLite."""

    async def record(self, event: NetworkEvent) -> None:
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO network_events (provider, request_type,
                                            sanitized_query, destination,
                                            success)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event.provider,
                    event.request_type,
                    event.sanitized_query,
                    event.destination,
                    event.success,
                ),
            )
            await db.commit()

    async def get_all(self) -> list[NetworkEvent]:
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM network_events ORDER BY created_at DESC"
            )
            rows = await cursor.fetchall()
        return [_row_to_event(row) for row in rows]


def _row_to_event(row: dict) -> NetworkEvent:
    return NetworkEvent(
        id=row["id"],
        provider=row["provider"],
        request_type=row["request_type"],
        sanitized_query=row["sanitized_query"],
        destination=row["destination"],
        success=bool(row["success"]),
        created_at=_parse_dt(row["created_at"]),
    )


def _parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)
