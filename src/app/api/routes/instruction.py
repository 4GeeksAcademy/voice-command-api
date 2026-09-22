import json

from groq import Groq
from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from src.app.core.config import get_settings
from src.app.schemas.voice import InstructionPayload, InstructionRequest

router = APIRouter(tags=["instruction"])


@router.post("/instruction", response_model=InstructionPayload)
def route_instruction(
    payload: InstructionRequest,
) -> InstructionPayload:
    return request_instruction(payload.transcription)


def request_instruction(transcription: str) -> InstructionPayload:
    settings = get_settings()
    if not settings.groq_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Groq API configuration is missing. Set GROQ_API_KEY.",
        )

    try:
        response = Groq(api_key=settings.groq_api_key).chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the task API router. Convert the user's instruction into "
                        "one valid task API operation. Return ONLY strict JSON with exactly "
                        "these fields: endpoint, method, params. Never return markdown or "
                        "explanation. Use only these routes and parameter shapes:\n"
                        "GET /tasks => params {}\n"
                        "POST /tasks => params {title: required non-empty string, done: optional boolean}\n"
                        "PUT /tasks/{task_id} => params {title: required non-empty string, done: required boolean}\n"
                        "PATCH /tasks/{task_id} => params {title and/or done, and no other keys}\n"
                        "DELETE /tasks/{task_id} => params {}\n"
                        "The endpoint path contains the numeric task_id for PUT, PATCH, and DELETE. "
                        "Do not use keys named task, status, action, completed, or task_id. "
                        "Examples:\n"
                        "add buy groceries to my list -> {\"endpoint\":\"/tasks\",\"method\":\"POST\",\"params\":{\"title\":\"buy groceries\"}}\n"
                        "show my tasks -> {\"endpoint\":\"/tasks\",\"method\":\"GET\",\"params\":{}}\n"
                        "mark task 2 as done -> {\"endpoint\":\"/tasks/2\",\"method\":\"PATCH\",\"params\":{\"done\":true}}\n"
                        "delete task 1 -> {\"endpoint\":\"/tasks/1\",\"method\":\"DELETE\",\"params\":{}}"
                    ),
                },
                {"role": "user", "content": transcription},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Groq returned an empty response.")
        return InstructionPayload.model_validate(json.loads(content))
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Groq returned invalid instruction JSON. Expected endpoint, method, and params.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to get a valid instruction from Groq.",
        ) from exc
