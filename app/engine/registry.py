"""Speech engine registry managing replaceable local model adapters."""

from __future__ import annotations

from app.core.config import Settings
from app.engine.adapters.unconfigured import UnconfiguredEngine
from app.engine.base import EngineCapability, SpeechEngine


class EngineRegistry:
    def __init__(self, engines: list[SpeechEngine] | None = None) -> None:
        self._engines: dict[str, SpeechEngine] = {}
        for eng in engines or []:
            self.register(eng)
        if "unconfigured" not in self._engines:
            self.register(UnconfiguredEngine())

    def register(self, engine: SpeechEngine) -> None:
        self._engines[engine.engine_id] = engine

    def get(self, engine_id: str) -> SpeechEngine:
        return self._engines.get(engine_id, self._engines["unconfigured"])

    def list_ids(self) -> list[str]:
        return [eid for eid in self._engines if eid != "unconfigured"]

    def list_capabilities(self) -> list[EngineCapability]:
        caps = [
            eng.capabilities()
            for eid, eng in self._engines.items()
            if eid != "unconfigured"
        ]
        if not caps:
            caps.append(self._engines["unconfigured"].capabilities())
        return caps

    def resolve(self, preferred_engine_id: str | None) -> SpeechEngine:
        if preferred_engine_id and preferred_engine_id in self._engines:
            return self._engines[preferred_engine_id]
        for eid, eng in self._engines.items():
            if eid != "unconfigured" and eng.capabilities().distributable_default:
                return eng
        return self._engines["unconfigured"]


def build_default_registry(settings: Settings) -> EngineRegistry:
    """Build the default local engine registry from available adapters."""
    engines: list[SpeechEngine] = []
    # Adapters implemented in Milestone 4 are dynamically loaded here when present
    try:
        from app.engine.adapters.indic_openvoice import IndicParlerOpenVoiceEngine

        engines.append(IndicParlerOpenVoiceEngine(model_dir=settings.model_dir))
    except ImportError:
        pass
    try:
        from app.engine.adapters.f5_tts_urdu import F5TTSUrduEngine

        engines.append(F5TTSUrduEngine(model_dir=settings.model_dir))
    except ImportError:
        pass
    return EngineRegistry(engines)
