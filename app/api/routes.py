from __future__ import annotations

import logging
import os
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.state_manager import state_manager
from app.core.mute_controller import mute_controller
from app.domain.models import (
    CommandRequest,
    CommandResponse,
    CompanionState,
    Memory,
    ProcessingMode,
    Task,
    TaskStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_processor(request: Request):
    return request.app.state.command_processor


def _get_memory_repo(request: Request):
    return request.app.state.memory_repo


def _get_task_repo(request: Request):
    return request.app.state.task_repo


def _get_network_event_repo(request: Request):
    return request.app.state.network_event_repo


def _get_stt(request: Request):
    return request.app.state.stt


@router.get("/health")
async def health():
    return {
        "status": "healthy",
        "mode": settings.companion_mode,
        "state": state_manager.get_state().value,
    }


@router.get("/api/state")
async def get_state():
    state = state_manager.get_state()
    return {
        "state": state.value,
        "color": state_manager.get_color(),
        "muted": mute_controller.is_muted(),
        "mode": settings.companion_mode,
    }


@router.post("/api/mute")
async def mute():
    mute_controller.mute()
    return {"muted": True, "state": CompanionState.MUTED.value}


@router.post("/api/unmute")
async def unmute():
    mute_controller.unmute()
    return {"muted": False, "state": CompanionState.ARMED.value}


@router.post("/api/command")
async def process_command(request: Request, cmd: CommandRequest) -> CommandResponse:
    processor = _get_processor(request)
    return await processor.process_text(cmd.text)


@router.post("/api/audio")
async def process_audio(request: Request, file: UploadFile = File(...)):
    stt = _get_stt(request)
    processor = _get_processor(request)

    if mute_controller.is_muted():
        return JSONResponse(
            status_code=200,
            content={
                "success": False,
                "error": "Companion is muted.",
                "state": CompanionState.MUTED.value,
            },
        )

    ext = Path(file.filename or "audio.wav").suffix.lower()
    if ext not in settings.allowed_audio_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {ext}. Allowed: {settings.allowed_audio_extensions}",
        )

    if stt is None or not stt.is_available():
        raise HTTPException(
            status_code=503,
            detail="Speech-to-text is not available. Configure whisper.cpp to enable audio input.",
        )

    tmp_path = None
    try:
        content = await file.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > settings.max_audio_size_mb:
            raise HTTPException(
                status_code=400,
                detail=f"Audio file too large ({size_mb:.1f}MB). Max: {settings.max_audio_size_mb}MB.",
            )

        tmp_dir = Path(tempfile.gettempdir()) / "local_companion_audio"
        tmp_dir.mkdir(exist_ok=True)
        tmp_path = tmp_dir / f"{uuid.uuid4().hex}{ext}"
        tmp_path.write_bytes(content)

        await state_manager.set_state(CompanionState.TRANSCRIBING)
        transcription = await stt.transcribe(tmp_path)

        if not transcription.strip():
            await state_manager.set_state(CompanionState.ARMED)
            return JSONResponse(
                content={
                    "success": False,
                    "transcription": "",
                    "error": "Could not transcribe audio — no speech detected.",
                    "state": CompanionState.ARMED.value,
                }
            )

        result = await processor.process_text(transcription)
        return JSONResponse(
            content={
                "success": result.success,
                "transcription": transcription,
                "action": result.action,
                "processing_mode": result.processing_mode,
                "response": result.response,
                "state": result.state,
            }
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Audio processing failed")
        await state_manager.set_state(CompanionState.ERROR)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(exc), "state": CompanionState.ERROR.value},
        )
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                logger.warning("Failed to delete temporary audio file: %s", tmp_path)


@router.get("/api/memories")
async def list_memories(request: Request):
    repo = _get_memory_repo(request)
    memories = await repo.get_all()
    return {
        "memories": [
            {
                "id": m.id,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "source": m.source,
            }
            for m in memories
        ]
    }


@router.get("/api/memories/search")
async def search_memories(request: Request, q: str = ""):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required.")
    repo = _get_memory_repo(request)
    memories = await repo.search(q)
    return {
        "query": q,
        "results": [
            {
                "id": m.id,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "source": m.source,
            }
            for m in memories
        ],
    }


@router.delete("/api/memories/{memory_id}")
async def delete_memory(request: Request, memory_id: int):
    repo = _get_memory_repo(request)
    deleted = await repo.soft_delete(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found.")
    return {"deleted": True, "id": memory_id}


@router.get("/api/tasks")
async def list_tasks(request: Request, status: str | None = None):
    repo = _get_task_repo(request)
    tasks = await repo.get_all(status=status)
    return {
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "status": t.status if isinstance(t.status, str) else t.status.value,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tasks
        ]
    }


@router.post("/api/tasks")
async def create_task(request: Request, task: Task):
    repo = _get_task_repo(request)
    created = await repo.create(task)
    return {
        "id": created.id,
        "title": created.title,
        "status": created.status if isinstance(created.status, str) else created.status.value,
    }


@router.patch("/api/tasks/{task_id}")
async def update_task(request: Request, task_id: int, body: dict):
    repo = _get_task_repo(request)
    new_status = body.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Field 'status' is required.")
    updated = await repo.update_status(task_id, new_status)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found.")
    return {"id": task_id, "status": new_status}


@router.get("/api/network-events")
async def list_network_events(request: Request):
    repo = _get_network_event_repo(request)
    events = await repo.get_all()
    return {
        "events": [
            {
                "id": e.id,
                "provider": e.provider,
                "request_type": e.request_type,
                "sanitized_query": e.sanitized_query,
                "destination": e.destination,
                "success": e.success,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]
    }


@router.post("/api/mode")
async def set_mode(body: dict):
    mode = body.get("mode", "").lower()
    if mode not in ("demo", "local_ai"):
        raise HTTPException(status_code=400, detail="Mode must be 'demo' or 'local_ai'.")
    settings.companion_mode = mode
    return {"mode": mode}
