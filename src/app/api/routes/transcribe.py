from fastapi import APIRouter, HTTPException, Request, UploadFile, status

from src.app.schemas.voice import InstructionRequest, TranscribeFlowResponse
from src.app.services.groq_client import route_transcription, transcribe_audio
from src.app.services.tasks import execute_instruction
from src.app.utils.language import normalize_transcription_language

router = APIRouter(tags=["transcribe"])


@router.get("/")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/transcribe", response_model=TranscribeFlowResponse)
async def transcribe_and_run_flow(request: Request) -> TranscribeFlowResponse:
    content_type = (request.headers.get("content-type") or "").lower()

    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON body.",
            ) from exc
        try:
            manual = InstructionRequest.model_validate(body)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="JSON body must include a non-empty 'transcription' field.",
            ) from exc
        transcription = manual.transcription.strip()
    elif "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("file")
        if not _is_upload(upload):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="multipart/form-data must include an audio 'file' field.",
            )
        language = normalize_transcription_language(form.get("language"))
        transcription = await transcribe_audio(upload, language=language)
    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Send multipart/form-data with 'file' or application/json with 'transcription'.",
        )

    instruction = route_transcription(transcription)
    result = execute_instruction(
        instruction.endpoint,
        instruction.method,
        instruction.params,
    )
    return TranscribeFlowResponse(
        transcription=transcription,
        instruction=instruction,
        result=result,
    )


def _is_upload(value: object) -> bool:
    """True for Starlette/FastAPI uploads (avoid brittle isinstance under --reload)."""
    if value is None or isinstance(value, (str, bytes, bytearray)):
        return False
    return hasattr(value, "filename") and hasattr(value, "read")
