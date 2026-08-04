"""Groq client helpers for chat routing and audio transcription."""

from __future__ import annotations

import json
import re
import ssl
from typing import Any

import httpx
import truststore
from fastapi import HTTPException, UploadFile, status
from groq import Groq

from src.app.core.config import get_settings
from src.app.schemas.voice import InstructionPayload

SYSTEM_PROMPT = """You are a voice-command router for a to-do list API.
Given a user transcription, respond with ONLY a single JSON object (no markdown, no explanation) in this exact shape:
{"endpoint":"/tasks","method":"POST","params":{"title":"Buy groceries"}}

Rules:
- Never return free text. Never wrap the JSON in markdown fences.
- Use only these endpoints and methods:
  - GET /tasks with params {}
  - POST /tasks with params {"title":"<task title>"} and optional "done" (boolean)
  - PUT /tasks/<id> with params {"title":"<task title>","done":<true|false>}
  - PATCH /tasks/<id> with params that include only fields to change: "title" and/or "done"
  - DELETE /tasks/<id> with params {}
- For create/add/new task intents, use POST /tasks and extract a clean title.
- For list/show/get all tasks, use GET /tasks.
- For mark done/complete/finish, use PATCH /tasks/<id> with {"done": true}.
- For rename/change title, use PATCH /tasks/<id> with {"title":"..."}.
- For full replace, use PUT /tasks/<id>.
- For remove/delete, use DELETE /tasks/<id>.
- When an id is mentioned ("task 2", "number 3"), put it in the endpoint path.
- If the intent is unclear, prefer GET /tasks with params {}.
"""

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _client() -> Groq:
    """Build a Groq client using the OS certificate store (fixes corporate SSL proxies)."""
    settings = get_settings()
    ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    http_client = httpx.Client(
        verify=ssl_context,
        timeout=settings.request_timeout_seconds,
    )
    return Groq(api_key=settings.groq_api_key, http_client=http_client)


def route_transcription(transcription: str) -> InstructionPayload:
    """Call Groq chat to turn plain text into routing JSON. No hardcoded intents."""
    settings = get_settings()
    try:
        completion = _client().chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": transcription},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
    except Exception as exc:  # noqa: BLE001 — surface Groq/network errors cleanly
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq chat request failed: {exc}",
        ) from exc

    content = (completion.choices[0].message.content or "").strip()
    data = _parse_instruction_json(content)
    try:
        return InstructionPayload.model_validate(data)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq returned invalid instruction JSON: {content}",
        ) from exc


async def transcribe_audio(file: UploadFile, language: str | None = None) -> str:
    """Transcribe uploaded audio with Groq Whisper."""
    settings = get_settings()
    filename = getattr(file, "filename", None) or "audio.webm"
    try:
        audio_bytes = await file.read()
        if not audio_bytes and hasattr(file, "file"):
            file.file.seek(0)
            audio_bytes = file.file.read()
        if not audio_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded audio file is empty.",
            )
        kwargs: dict[str, Any] = {
            "model": settings.groq_transcription_model,
            "file": (filename, audio_bytes),
            "response_format": "text",
        }
        if language:
            kwargs["language"] = language
        result = _client().audio.transcriptions.create(**kwargs)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq transcription failed: {exc}",
        ) from exc

    text = result if isinstance(result, str) else getattr(result, "text", str(result))
    text = (text or "").strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcription was empty.",
        )
    return text


def _parse_instruction_json(content: str) -> dict[str, Any]:
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        match = _JSON_OBJECT_RE.search(content)
        if match:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Could not parse Groq JSON response: {content}",
    )
