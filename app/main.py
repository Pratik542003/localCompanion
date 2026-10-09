from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.repositories.database import init_db
from app.repositories.memory_repo import SQLiteMemoryRepository
from app.repositories.task_repo import SQLiteTaskRepository
from app.repositories.interaction_repo import SQLiteInteractionRepository
from app.repositories.network_event_repo import SQLiteNetworkEventRepository
from app.providers.reasoning import get_reasoning_provider
from app.providers.online_lookup import get_weather_provider, get_news_provider
from app.providers.speech_to_text import get_speech_to_text
from app.providers.text_to_speech import get_text_to_speech
from app.services.command_processor import CommandProcessor
from app.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Local Companion...")
    logger.info("Mode: %s", settings.companion_mode)

    await init_db()
    logger.info("Database initialized at %s", settings.database_path)

    memory_repo = SQLiteMemoryRepository()
    task_repo = SQLiteTaskRepository()
    interaction_repo = SQLiteInteractionRepository()
    network_event_repo = SQLiteNetworkEventRepository()

    reasoning = get_reasoning_provider()
    logger.info("Reasoning provider: %s", reasoning.provider_name())

    weather = get_weather_provider()
    news = get_news_provider()
    stt = get_speech_to_text()
    tts = get_text_to_speech()

    processor = CommandProcessor(
        reasoning=reasoning,
        memory_repo=memory_repo,
        task_repo=task_repo,
        interaction_repo=interaction_repo,
        network_event_repo=network_event_repo,
        weather_provider=weather,
        news_provider=news,
    )

    app.state.command_processor = processor
    app.state.memory_repo = memory_repo
    app.state.task_repo = task_repo
    app.state.network_event_repo = network_event_repo
    app.state.stt = stt
    app.state.tts = tts

    logger.info("Local Companion is ready!")
    yield
    logger.info("Shutting down Local Companion.")


app = FastAPI(
    title="Local Companion",
    description="Private, offline-first personal AI companion",
    version="0.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(router)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")
