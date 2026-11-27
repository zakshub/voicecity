"""VoiceCity local-first FastAPI application."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import generations, system, voices
from app.core.config import Settings, load_settings
from app.core.database import VoiceCityDB
from app.core.jobs import GenerationJobQueue
from app.core.state import AppContext
from app.core.storage import LocalStorage, StorageSecurityError
from app.engine.registry import EngineRegistry, build_default_registry

REPO_ROOT = Path(__file__).resolve().parent.parent


def create_app(
    settings: Settings | None = None,
    engine_registry: EngineRegistry | None = None,
) -> FastAPI:
    cfg = settings or load_settings()
    storage = LocalStorage(cfg)
    db = VoiceCityDB(cfg.db_path)
    registry = engine_registry or build_default_registry(cfg)
    jobs = GenerationJobQueue(db=db, storage=storage)

    application = FastAPI(
        title="VoiceCity",
        description=(
            "Original local-first personal voice studio for Urdu, English, and mixed "
            "Urdu-English speech generation."
        ),
        version="0.3.0",
    )

    application.state.ctx = AppContext(
        settings=cfg,
        storage=storage,
        db=db,
        engines=registry,
        jobs=jobs,
    )

    # Restrict browser origins to local loopback interfaces only
    application.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$",
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @application.exception_handler(StorageSecurityError)
    async def storage_security_handler(
        request: Request, exc: StorageSecurityError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )

    application.include_router(system.router)
    application.include_router(voices.router)
    application.include_router(generations.router)

    # Serve local web studio UI when frontend files are present
    frontend_dir = REPO_ROOT / "frontend"
    if (frontend_dir / "index.html").is_file():
        assets_dir = frontend_dir / "assets"
        if assets_dir.is_dir():
            application.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @application.get("/", include_in_schema=False)
        def serve_index() -> FileResponse:
            return FileResponse(frontend_dir / "index.html")

    return application


app = create_app()
