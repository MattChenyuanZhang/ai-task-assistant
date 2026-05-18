import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from database import get_db, Task, TaskLog
from services.deadline import get_urgent_tasks

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: str = "medium"
    estimated_hours: Optional[float] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    estimated_hours: Optional[float] = None
    finished_hours: Optional[float] = None
    working: Optional[bool] = None
    working_start: Optional[datetime] = None


def task_to_dict(t: Task) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "deadline": t.deadline.isoformat() if t.deadline else None,
        "priority": t.priority,
        "status": t.status,
        "estimated_hours": t.estimated_hours,
        "finished_hours": t.finished_hours or 0.0,
        "working": t.working or False,
        "working_start": (t.working_start.isoformat() + "Z") if t.working_start else None,
        "created_at": t.created_at.isoformat(),
    }


@router.get("")
def list_tasks(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    return [task_to_dict(t) for t in query.order_by(Task.deadline.asc().nullslast()).all()]


@router.get("/urgent")
def urgent_tasks(db: Session = Depends(get_db)):
    return get_urgent_tasks(db)


@router.post("", status_code=201)
def create_task(body: TaskCreate, db: Session = Depends(get_db)):
    task = Task(**body.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task_to_dict(task)


@router.patch("/{task_id}")
def update_task(task_id: int, body: TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    data = body.model_dump(exclude_unset=True)
    # if stopping work, commit elapsed hours
    if data.get("working") == False and task.working and task.working_start:
        elapsed = (datetime.utcnow() - task.working_start).total_seconds() / 3600
        task.finished_hours = (task.finished_hours or 0) + elapsed
        task.estimated_hours = max(0, (task.estimated_hours or 0) - elapsed)
        task.working_start = None
    # if starting work, stop any other working task
    if data.get("working") == True:
        others = db.query(Task).filter(Task.id != task_id, Task.working == True).all()
        for other in others:
            if other.working_start:
                elapsed = (datetime.utcnow() - other.working_start).total_seconds() / 3600
                other.finished_hours = (other.finished_hours or 0) + elapsed
                other.estimated_hours = max(0, (other.estimated_hours or 0) - elapsed)
            other.working = False
            other.working_start = None
    for field, value in data.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task_to_dict(task)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()


@router.get("/{task_id}/logs")
def get_task_logs(task_id: int, db: Session = Depends(get_db)):
    logs = db.query(TaskLog).filter(TaskLog.task_id == task_id).order_by(TaskLog.created_at.desc()).all()
    return [
        {
            "id": l.id,
            "prompt": l.prompt,
            "changes": json.loads(l.changes),
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]


@router.delete("", status_code=204)
def clear_all_tasks(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    query.delete()
    db.commit()
