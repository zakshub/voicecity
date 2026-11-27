"""Minimal VoiceCity API scaffold. Speech generation is not configured yet."""

from fastapi import FastAPI

app = FastAPI(
    title="VoiceCity",
    description="Local-first personal voice studio for Urdu and English.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "voicecity"}


@app.get("/api/v1/capabilities")
def capabilities() -> dict[str, object]:
    return {
        "voice_profiles": False,
        "speech_generation": False,
        "urdu": "pending_model_evaluation",
        "english": "pending_model_evaluation",
        "mixed_language": "pending_model_evaluation",
        "remote_inference": False,
        "message": "Voice engine is not configured. See docs/MODEL_EVALUATION.md.",
    }
