from typing import Any, Literal
import re

from pydantic import BaseModel, Field, model_validator


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1)
    done: bool = False


class TaskReplace(BaseModel):
    title: str = Field(..., min_length=1)
    done: bool


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    done: bool | None = None


class Task(BaseModel):
    id: int
    title: str
    done: bool


class InstructionRequest(BaseModel):
    transcription: str = Field(..., min_length=1)


class InstructionPayload(BaseModel):
    endpoint: str = Field(..., min_length=1)
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_route_params(self) -> "InstructionPayload":
        task_id_endpoint = re.fullmatch(r"/tasks/(\d+)", self.endpoint)
        if self.endpoint == "/tasks" and self.method == "GET":
            if self.params:
                raise ValueError("GET /tasks accepts no parameters.")
        elif self.endpoint == "/tasks" and self.method == "POST":
            if set(self.params) - {"title", "done"} or not isinstance(self.params.get("title"), str):
                raise ValueError("POST /tasks requires title and only permits done as an optional parameter.")
        elif task_id_endpoint and self.method == "PUT":
            if set(self.params) != {"title", "done"} or not isinstance(self.params["title"], str) or not isinstance(self.params["done"], bool):
                raise ValueError("PUT /tasks/{task_id} requires title and done.")
        elif task_id_endpoint and self.method == "PATCH":
            if not self.params or set(self.params) - {"title", "done"}:
                raise ValueError("PATCH /tasks/{task_id} accepts title and/or done only.")
            if "title" in self.params and not isinstance(self.params["title"], str):
                raise ValueError("PATCH title must be a string.")
            if "done" in self.params and not isinstance(self.params["done"], bool):
                raise ValueError("PATCH done must be a boolean.")
        elif task_id_endpoint and self.method == "DELETE":
            if self.params:
                raise ValueError("DELETE /tasks/{task_id} accepts no parameters.")
        else:
            raise ValueError("Unsupported task endpoint or method.")
        return self


class TranscribeFlowResponse(BaseModel):
    transcription: str = Field(..., min_length=1)
    instruction: InstructionPayload
    result: Any
