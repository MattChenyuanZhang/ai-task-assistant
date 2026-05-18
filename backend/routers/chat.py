import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from database import get_db, Task, TaskLog, Conversation
from services.claude import get_advice, classify_intent, extract_tasks, extract_updates, chat_reply, get_proactive_reminder
from services.probability import calculate_probabilities

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/reminder")
def get_reminder(db: Session = Depends(get_db)):
    tasks = db.query(Task).filter(Task.status == "pending").order_by(Task.deadline.asc().nullslast()).all()
    task_dicts = [
        {"id": t.id, "title": t.title, "deadline": t.deadline.isoformat() if t.deadline else None,
         "estimated_hours": t.estimated_hours, "status": t.status}
        for t in tasks
    ]
    if not task_dicts:
        return {"reminder": None}
    probs = calculate_probabilities(task_dicts)
    reminder = get_proactive_reminder(task_dicts, probs)
    return {"reminder": reminder}


@router.post("/advice")
def generate_advice(db: Session = Depends(get_db)):
    tasks = db.query(Task).filter(Task.status == "pending").order_by(Task.deadline.asc().nullslast()).all()
    task_dicts = [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "deadline": t.deadline.isoformat() if t.deadline else None,
            "priority": t.priority,
            "estimated_hours": t.estimated_hours,
            "finished_hours": t.finished_hours or 0.0,
            "status": t.status,
        }
        for t in tasks
    ]
    history = db.query(Conversation).order_by(Conversation.timestamp.desc()).limit(10).all()
    history_dicts = [{"role": h.role, "content": h.content} for h in reversed(history)]
    advice = get_advice(task_dicts, history_dicts)
    db.add(Conversation(role="assistant", content=advice))
    db.commit()
    return {"advice": advice}


class ChatRequest(BaseModel):
    text: str


@router.post("/chat")
def chat(body: ChatRequest, db: Session = Depends(get_db)):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Input is empty")
    try:
        return _chat_handler(body, db)
    except Exception as e:
        # fallback — never show a raw error to the user
        try:
            all_tasks = db.query(Task).order_by(Task.deadline.asc().nullslast()).all()
            task_dicts = [{"id": t.id, "title": t.title, "estimated_hours": t.estimated_hours, "status": t.status} for t in all_tasks]
            reply = chat_reply(body.text, task_dicts)
        except Exception:
            reply = "Sorry, I had trouble processing that. Could you rephrase?"
        db.add(Conversation(role="assistant", content=reply))
        db.commit()
        return {"intent": "chat", "reply": reply}


def _chat_handler(body: ChatRequest, db):

    all_tasks = db.query(Task).order_by(Task.deadline.asc().nullslast()).all()
    task_dicts = [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "deadline": t.deadline.isoformat() if t.deadline else None,
            "priority": t.priority,
            "estimated_hours": t.estimated_hours,
            "status": t.status,
        }
        for t in all_tasks
    ]

    intent = classify_intent(body.text, has_tasks=len(task_dicts) > 0)
    db.add(Conversation(role="user", content=body.text))
    db.commit()

    # --- ADD TASKS ---
    if intent == "task":
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
                    pass
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
            saved.append({"id": task.id, "title": task.title})

        if not saved:
            reply = chat_reply(body.text, task_dicts)
            db.add(Conversation(role="assistant", content=reply))
            db.commit()
            return {"intent": "chat", "reply": reply}

        return {"intent": "task", "tasks": saved}

    # --- UPDATE TASKS ---
    elif intent == "update":
        if not task_dicts:
            reply = "You don't have any tasks yet. Tell me what you need to do and I'll add them!"
            db.add(Conversation(role="assistant", content=reply))
            db.commit()
            return {"intent": "chat", "reply": reply}

        try:
            updates = extract_updates(body.text, task_dicts)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Update extraction failed: {e}")

        applied = []
        for u in updates:
            task = db.query(Task).filter(Task.id == u["id"]).first()
            if not task:
                continue
            fields = u.get("fields", {})
            if "title" in fields:
                task.title = fields["title"]
            if "description" in fields:
                task.description = fields["description"]
            if "priority" in fields:
                task.priority = fields["priority"]
            if "estimated_hours" in fields:
                task.estimated_hours = fields["estimated_hours"]
            if "status" in fields:
                task.status = fields["status"]
            if "finished_hours" in fields:
                task.finished_hours = max(0, float(fields["finished_hours"]))
            if "working" in fields:
                starting = fields["working"] in (True, "true", 1)
                if starting:
                    # stop any other currently working task first
                    others = db.query(Task).filter(Task.id != task.id, Task.working == True).all()
                    for other in others:
                        if other.working_start:
                            elapsed = (datetime.now() - other.working_start).total_seconds() / 3600
                            other.finished_hours = (other.finished_hours or 0) + elapsed
                            other.estimated_hours = max(0, (other.estimated_hours or 0) - elapsed)
                        other.working = False
                        other.working_start = None
                    task.working = True
                    task.working_start = datetime.now()
                else:
                    # commit elapsed time
                    if task.working and task.working_start:
                        elapsed = (datetime.now() - task.working_start).total_seconds() / 3600
                        task.finished_hours = (task.finished_hours or 0) + elapsed
                        task.estimated_hours = max(0, (task.estimated_hours or 0) - elapsed)
                    task.working = False
                    task.working_start = None
            if "deadline" in fields:
                try:
                    task.deadline = datetime.fromisoformat(fields["deadline"]) if fields["deadline"] else None
                except ValueError:
                    pass
            db.commit()
            db.add(TaskLog(task_id=task.id, prompt=body.text, changes=json.dumps(fields)))
            db.commit()
            applied.append({"id": task.id, "title": task.title, "fields": fields})

        if not applied:
            reply = chat_reply(body.text, task_dicts)
            db.add(Conversation(role="assistant", content=reply))
            db.commit()
            return {"intent": "chat", "reply": reply}

        return {"intent": "update", "updated": applied}

    # --- CHAT ---
    else:
        reply = chat_reply(body.text, task_dicts)
        db.add(Conversation(role="assistant", content=reply))
        db.commit()
        return {"intent": "chat", "reply": reply}
