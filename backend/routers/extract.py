from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from database import get_db, Task
from services.claude import extract_tasks

router = APIRouter(prefix="/api/extract", tags=["extract"])


class ExtractRequest(BaseModel):
    text: str


@router.post("")
def extract_and_save(body: ExtractRequest, db: Session = Depends(get_db)):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Input text is empty")

    try:
        extracted = extract_tasks(body.text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Task extraction failed: {e}")

    saved = []
    for item in extracted:
        deadline = None
        if item.get("deadline"):
            try:
                deadline = datetime.fromisoformat(item["deadline"])
            except ValueError:
                deadline = None

        task = Task(
            title=item.get("title", "Untitled"),
            description=item.get("description"),
            deadline=deadline,
            priority=item.get("priority", "medium"),
            estimated_hours=item.get("estimated_hours"),
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        saved.append({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "deadline": task.deadline.isoformat() if task.deadline else None,
            "priority": task.priority,
            "estimated_hours": task.estimated_hours,
        })

    return {"extracted": len(saved), "tasks": saved}
