"""Environment-backed application configuration with local-first safe defaults."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_ENGINE_ID = "dual_cloning_router"


@dataclass
class Settings:
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 8765
    data_dir: Path = Path("./data").resolve()
    model_dir: Path = Path("./models").resolve()
    tts_provider: str = DEFAULT_ENGINE_ID
    allow_remote_inference: bool = False
    max_upload_mb: int = 100
    max_text_chars: int = 4000

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def db_path(self) -> Path:
        return self.data_dir / "voicecity.db"

    @property
    def voice_profiles_dir(self) -> Path:
        return self.data_dir / "voice_profiles"

    @property
    def generated_dir(self) -> Path:
        return self.data_dir / "generated"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"


def load_settings(env_file: Path | None = None) -> Settings:
    """Load VoiceCity settings from optional .env file and environment variables."""
    if env_file is not None and env_file.is_file():
        load_dotenv(env_file, override=False)
    else:
        default_env = Path(".env")
        if default_env.is_file():
            load_dotenv(default_env, override=False)

    provider = os.getenv("VOICECITY_TTS_PROVIDER", "").strip() or DEFAULT_ENGINE_ID
    return Settings(
        environment=os.getenv("VOICECITY_ENV", "development").strip() or "development",
        host=os.getenv("VOICECITY_HOST", "127.0.0.1").strip() or "127.0.0.1",
        port=int(os.getenv("VOICECITY_PORT", "8765")),
        data_dir=Path(os.getenv("VOICECITY_DATA_DIR", "./data")).expanduser().resolve(),
        model_dir=Path(os.getenv("VOICECITY_MODEL_DIR", "./models")).expanduser().resolve(),
        tts_provider=provider,
        allow_remote_inference=(
            os.getenv("VOICECITY_ALLOW_REMOTE_INFERENCE", "false").strip().lower() == "true"
        ),
        max_upload_mb=max(1, int(os.getenv("VOICECITY_MAX_UPLOAD_MB", "100"))),
        max_text_chars=max(50, int(os.getenv("VOICECITY_MAX_TEXT_CHARS", "4000"))),
    )


settings = load_settings()
