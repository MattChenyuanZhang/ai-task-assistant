from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db, Task, Conversation
from services.claude import get_advice

router = APIRouter(prefix="/api/advice", tags=["advice"])


@router.post("")
def generate_advice(db: Session = Depends(get_db)):
    # Fetch pending tasks
    tasks = db.query(Task).filter(Task.status == "pending").order_by(Task.deadline.asc().nullslast()).all()
    task_dicts = [
        {
            "title": t.title,
            "description": t.description,
            "deadline": t.deadline.isoformat() if t.deadline else None,
            "priority": t.priority,
            "estimated_hours": t.estimated_hours,
        }
        for t in tasks
    ]

    # Fetch last 10 conversation turns
    history = db.query(Conversation).order_by(Conversation.timestamp.desc()).limit(10).all()
    history_dicts = [{"role": h.role, "content": h.content} for h in reversed(history)]

    advice = get_advice(task_dicts, history_dicts)

    # Save assistant response to conversation history
    db.add(Conversation(role="assistant", content=advice))
    db.commit()

    return {"advice": advice}
