"""Application service container attached to FastAPI app.state."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.core.database import VoiceCityDB
from app.core.jobs import GenerationJobQueue
from app.core.storage import LocalStorage
from app.engine.registry import EngineRegistry


@dataclass
class AppContext:
    settings: Settings
    storage: LocalStorage
    db: VoiceCityDB
    engines: EngineRegistry
    jobs: GenerationJobQueue
