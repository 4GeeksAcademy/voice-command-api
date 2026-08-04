"""In-memory task store and CRUD helpers."""

from __future__ import annotations

from fastapi import HTTPException, status

from src.app.schemas.voice import Task, TaskCreate, TaskReplace, TaskUpdate

tasks: list[dict] = []
_next_id = 1


def list_tasks() -> list[Task]:
    return [Task.model_validate(task) for task in tasks]


def create_task(payload: TaskCreate) -> Task:
    global _next_id
    task = {
        "id": _next_id,
        "title": payload.title,
        "done": payload.done,
    }
    _next_id += 1
    tasks.append(task)
    return Task.model_validate(task)


def replace_task(task_id: int, payload: TaskReplace) -> Task:
    task = _get_task_or_404(task_id)
    task["title"] = payload.title
    task["done"] = payload.done
    return Task.model_validate(task)


def update_task(task_id: int, payload: TaskUpdate) -> Task:
    task = _get_task_or_404(task_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one of: title, done.",
        )
    if "title" in data and data["title"] is not None:
        task["title"] = data["title"]
    if "done" in data and data["done"] is not None:
        task["done"] = data["done"]
    return Task.model_validate(task)


def delete_task(task_id: int) -> dict[str, str]:
    index = _find_index(task_id)
    if index is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found.",
        )
    tasks.pop(index)
    return {"message": f"Task {task_id} deleted."}


def execute_instruction(endpoint: str, method: str, params: dict) -> object:
    """Apply a routed instruction against the in-memory task store."""
    method_upper = method.upper()
    path = endpoint.rstrip("/") or "/tasks"

    if path == "/tasks" and method_upper == "GET":
        return [task.model_dump() for task in list_tasks()]

    if path == "/tasks" and method_upper == "POST":
        payload = TaskCreate.model_validate(params)
        return create_task(payload).model_dump()

    task_id = _extract_task_id(path)
    if task_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported instruction endpoint: {method_upper} {endpoint}",
        )

    if method_upper == "PUT":
        payload = TaskReplace.model_validate(params)
        return replace_task(task_id, payload).model_dump()

    if method_upper == "PATCH":
        payload = TaskUpdate.model_validate(params)
        return update_task(task_id, payload).model_dump()

    if method_upper == "DELETE":
        return delete_task(task_id)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported instruction method: {method_upper} {endpoint}",
    )


def _get_task_or_404(task_id: int) -> dict:
    index = _find_index(task_id)
    if index is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found.",
        )
    return tasks[index]


def _find_index(task_id: int) -> int | None:
    for index, task in enumerate(tasks):
        if task["id"] == task_id:
            return index
    return None


def _extract_task_id(path: str) -> int | None:
    # Accept "/tasks/1" or "tasks/1"
    parts = [part for part in path.strip("/").split("/") if part]
    if len(parts) == 2 and parts[0] == "tasks":
        try:
            return int(parts[1])
        except ValueError:
            return None
    return None
