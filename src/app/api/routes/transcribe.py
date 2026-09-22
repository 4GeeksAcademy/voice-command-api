from fastapi import APIRouter, HTTPException, Request, status
from starlette.datastructures import UploadFile
from groq import Groq
from pydantic import ValidationError

from src.app.api.routes.instruction import request_instruction
from src.app.api.routes.tasks import create_task, delete_task, replace_task, update_task
from src.app.core.config import get_settings
from src.app.schemas.voice import (
    InstructionRequest,
    TaskCreate,
    TaskReplace,
    TaskUpdate,
    TranscribeFlowResponse,
)

router = APIRouter(tags=["transcribe"])


@router.get("/")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/transcribe", response_model=TranscribeFlowResponse)
async def transcribe_and_run_flow(request: Request) -> TranscribeFlowResponse:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        body = await request.json()
        transcription = InstructionRequest.model_validate(body).transcription
    elif content_type.startswith("multipart/form-data"):
        form = await request.form()
        uploaded = form.get("file")
        if not isinstance(uploaded, UploadFile):
            raise HTTPException(status_code=400, detail="A multipart audio file is required.")
        transcription = transcribe_audio(uploaded, form.get("language"))
    else:
        raise HTTPException(status_code=415, detail="Use JSON transcription or multipart audio.")

    instruction = request_instruction(transcription)
    result = execute_instruction(instruction)
    return TranscribeFlowResponse(
        transcription=transcription,
        instruction=instruction,
        result=result,
    )


def transcribe_audio(uploaded: UploadFile, language: object) -> str:
    settings = get_settings()
    if not settings.groq_api_key:
        raise HTTPException(status_code=503, detail="Groq API configuration is missing. Set GROQ_API_KEY.")
    try:
        kwargs: dict[str, object] = {
            "file": (uploaded.filename or "command.webm", uploaded.file.read()),
            "model": settings.groq_transcription_model,
        }
        if isinstance(language, str) and language.strip():
            kwargs["language"] = language.strip().lower()
        response = Groq(api_key=settings.groq_api_key).audio.transcriptions.create(**kwargs)
        text = getattr(response, "text", "")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Groq returned an empty transcription.")
        return text.strip()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to transcribe audio with Groq.") from exc


def execute_instruction(instruction: object) -> object:
    endpoint = instruction.endpoint
    method = instruction.method
    params = instruction.params
    try:
        if endpoint == "/tasks" and method == "GET":
            from src.app.api.routes.tasks import get_tasks
            return get_tasks()
        if endpoint == "/tasks" and method == "POST":
            return create_task(TaskCreate.model_validate(params))
        task_id = int(endpoint.rsplit("/", 1)[1])
        if method == "PUT":
            return replace_task(task_id, TaskReplace.model_validate(params))
        if method == "PATCH":
            return update_task(task_id, TaskUpdate.model_validate(params))
        if method == "DELETE":
            return delete_task(task_id)
    except (IndexError, ValueError, ValidationError) as exc:
        raise HTTPException(status_code=502, detail="Groq returned an invalid task instruction.") from exc
    raise HTTPException(status_code=502, detail="Groq returned an unsupported task instruction.")
