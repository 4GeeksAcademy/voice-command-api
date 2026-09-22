from fastapi import APIRouter, HTTPException, status

from src.app.schemas.voice import Task, TaskCreate, TaskReplace, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])

tasks: list[Task] = []
_next_task_id = 1


@router.get("", response_model=list[Task])
def get_tasks() -> list[Task]:
    return tasks


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate) -> Task:
    global _next_task_id
    task = Task(id=_next_task_id, title=payload.title, done=payload.done)
    _next_task_id += 1
    tasks.append(task)
    return task


@router.put("/{task_id}", response_model=Task)
def replace_task(
    task_id: int,
    payload: TaskReplace,
) -> Task:
    task = find_task(task_id)
    task.title = payload.title
    task.done = payload.done
    return task


@router.patch("/{task_id}", response_model=Task)
def update_task(
    task_id: int,
    payload: TaskUpdate,
) -> Task:
    task = find_task(task_id)
    if payload.title is not None:
        task.title = payload.title
    if payload.done is not None:
        task.done = payload.done
    return task


@router.delete("/{task_id}")
def delete_task(task_id: int) -> dict[str, str]:
    task = find_task(task_id)
    tasks.remove(task)
    return {"message": "Task deleted successfully"}


def find_task(task_id: int) -> Task:
    for task in tasks:
        if task.id == task_id:
            return task
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task with id {task_id} not found.",
    )
