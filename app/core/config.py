"""Environment-backed configuration with safe local defaults."""

from pathlib import Path
import os


class Settings:
    def __init__(self) -> None:
        self.environment = os.getenv("VOICECITY_ENV", "development")
        self.host = os.getenv("VOICECITY_HOST", "127.0.0.1")
        self.port = int(os.getenv("VOICECITY_PORT", "8765"))
        self.data_dir = Path(os.getenv("VOICECITY_DATA_DIR", "./data")).resolve()
        self.model_dir = Path(os.getenv("VOICECITY_MODEL_DIR", "./models")).resolve()
        self.allow_remote_inference = (
            os.getenv("VOICECITY_ALLOW_REMOTE_INFERENCE", "false").lower() == "true"
        )


settings = Settings()
