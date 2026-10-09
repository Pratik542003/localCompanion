from __future__ import annotations

from datetime import datetime

from app.domain.interfaces import TaskRepository
from app.domain.models import Task, TaskStatus
from app.repositories.database import get_db


class SQLiteTaskRepository(TaskRepository):
    """Concrete task repository backed by SQLite."""

    async def create(self, task: Task) -> Task:
        now = datetime.now().isoformat()
        async with get_db() as db:
            cursor = await db.execute(
                """
                INSERT INTO tasks (title, description, status, due_at,
                                   created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    task.title,
                    task.description,
                    task.status.value if isinstance(task.status, TaskStatus) else task.status,
                    task.due_at.isoformat() if task.due_at else None,
                    now,
                    now,
                ),
            )
            await db.commit()
            task.id = cursor.lastrowid
            task.created_at = datetime.fromisoformat(now)
            task.updated_at = datetime.fromisoformat(now)
        return task

    async def get_all(self, status: str | None = None) -> list[Task]:
        async with get_db() as db:
            if status is not None:
                cursor = await db.execute(
                    "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC",
                    (status,),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM tasks ORDER BY created_at DESC"
                )
            rows = await cursor.fetchall()
        return [_row_to_task(row) for row in rows]

    async def update_status(self, task_id: int, status: str) -> bool:
        now = datetime.now().isoformat()
        async with get_db() as db:
            cursor = await db.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, task_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def find_by_title(self, title: str) -> Task | None:
        pattern = f"%{title}%"
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE title LIKE ? LIMIT 1",
                (pattern,),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_task(row)


def _row_to_task(row: dict) -> Task:
    return Task(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        status=TaskStatus(row["status"]),
        due_at=_parse_dt(row["due_at"]),
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


def _parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)
