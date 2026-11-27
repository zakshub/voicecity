"""Speech engine registry managing strictly separated capability adapters."""

from __future__ import annotations

from app.core.config import Settings
from app.engine.adapters.dual_cloning_router import DualCloningRouterEngine
from app.engine.adapters.experimental_parler_openvoice import ExperimentalParlerOpenVoiceEngine
from app.engine.adapters.f5_tts_urdu import F5TTSUrduEngine
from app.engine.adapters.indic_parler_tts import IndicParlerTTSEngine
from app.engine.adapters.openvoice_v2 import OpenVoiceV2ConverterEngine
from app.engine.adapters.qwen3_tts_en import Qwen3TTSEnglishCloningEngine
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
        if "dual_cloning_router" in self._engines:
            return self._engines["dual_cloning_router"]
        for eid, eng in self._engines.items():
            if eid != "unconfigured" and eng.capabilities().distributable_default:
                return eng
        return self._engines["unconfigured"]

    def capability_summary(self) -> dict[str, dict[str, str]]:
        """Compute honest separated capability readiness across all 4 capability classes."""
        caps = self.list_capabilities()

        def _check(cap_class: str, lang: str, allow_experimental: bool = False) -> str:
            matching = [
                c
                for c in caps
                if c.capability_class == cap_class
                and (
                    lang in c.verified_native_languages
                    or (allow_experimental and lang in c.experimental_languages)
                )
            ]
            if not matching:
                return "unsupported"
            ready_matches = [c for c in matching if c.ready]
            if ready_matches:
                if any(c.maturity_level == "empirically_verified" for c in ready_matches):
                    return "empirically_verified"
                if any(c.maturity_level == "technically_integrated" for c in ready_matches):
                    return "ready_unverified_listening"
                return "ready_experimental"
            if any(c.maturity_level == "experimental" for c in matching):
                return "experimental_not_installed"
            return "not_installed"

        return {
            "standard_tts": {
                "urdu": _check("standard_tts", "ur"),
                "english": _check("standard_tts", "en"),
            },
            "reference_voice_cloning": {
                "urdu": _check("reference_voice_cloning", "ur"),
                "english": _check("reference_voice_cloning", "en"),
                "mixed": _check("reference_voice_cloning", "mixed", allow_experimental=True),
            },
            "voice_conversion": {
                "english": _check("voice_conversion", "en"),
                "urdu_experimental": _check("voice_conversion", "ur", allow_experimental=True),
            },
            "cross_linguistic_voice_conversion": {
                "urdu_experimental": _check(
                    "cross_linguistic_voice_conversion", "ur", allow_experimental=True
                ),
                "english": _check("cross_linguistic_voice_conversion", "en"),
            },
        }


def build_default_registry(settings: Settings) -> EngineRegistry:
    """Register all distinct capability adapters without conflating TTS and voice cloning."""
    f5_ur = F5TTSUrduEngine(model_dir=settings.model_dir)
    qwen_en = Qwen3TTSEnglishCloningEngine(model_dir=settings.model_dir)
    dual_router = DualCloningRouterEngine(urdu_engine=f5_ur, english_engine=qwen_en)
    parler_tts = IndicParlerTTSEngine(model_dir=settings.model_dir)
    openvoice_vc = OpenVoiceV2ConverterEngine(model_dir=settings.model_dir)
    exp_parler_ov = ExperimentalParlerOpenVoiceEngine(
        parler_engine=parler_tts, openvoice_engine=openvoice_vc
    )
    return EngineRegistry(
        [
            dual_router,
            f5_ur,
            qwen_en,
            parler_tts,
            openvoice_vc,
            exp_parler_ov,
        ]
    )
