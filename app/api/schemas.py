"""Pydantic request and response schemas for the VoiceCity local REST API."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class VoiceProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    notes: Optional[str] = Field(default=None, max_length=1000)
    reference_transcript: Optional[str] = Field(default=None, max_length=2000)


class PrepareVoiceRequest(BaseModel):
    target_duration_seconds: float = Field(default=8.0, ge=3.0, le=15.0)
    reference_transcript: Optional[str] = Field(default=None, max_length=2000)


class TextAnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    language: Literal["ur", "en", "mixed"] = "mixed"


class GenerationCreateRequest(BaseModel):
    voice_profile_id: str = Field(..., min_length=4, max_length=64)
    text: str = Field(..., min_length=1, max_length=4000)
    language: Literal["ur", "en", "mixed"] = "ur"
    speed: float = Field(default=1.0, ge=0.6, le=1.5)
    expression: Literal["neutral", "clear", "warm", "calm"] = "neutral"
    engine_id: Optional[str] = Field(default=None, max_length=64)


class SettingsUpdateRequest(BaseModel):
    active_engine: Optional[str] = Field(default=None, max_length=64)
    compute_device: Optional[Literal["auto", "cpu", "cuda"]] = None
    default_language: Optional[Literal["ur", "en", "mixed"]] = None
    default_speed: Optional[float] = Field(default=None, ge=0.6, le=1.5)
    default_expression: Optional[Literal["neutral", "clear", "warm", "calm"]] = None
    default_export_format: Optional[Literal["wav", "mp3"]] = None
    prefer_offline_only: Optional[bool] = None
