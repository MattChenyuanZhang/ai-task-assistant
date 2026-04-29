from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import Task, UserPreference


def get_urgent_tasks(db: Session) -> list[dict]:
    """Return pending tasks whose deadline is within the configured threshold."""
    pref = db.query(UserPreference).filter_by(key="notification_threshold_hours").first()
    threshold_hours = float(pref.value) if pref else 24.0

    now = datetime.utcnow()
    cutoff = now + timedelta(hours=threshold_hours)

    urgent = (
        db.query(Task)
        .filter(
            Task.status == "pending",
            Task.deadline != None,
            Task.deadline <= cutoff,
            Task.deadline >= now,
        )
        .order_by(Task.deadline)
        .all()
    )

    result = []
    for t in urgent:
        delta = t.deadline - now
        hours_left = round(delta.total_seconds() / 3600, 1)
        result.append({
            "id": t.id,
            "title": t.title,
            "deadline": t.deadline.isoformat(),
            "hours_left": hours_left,
            "priority": t.priority,
        })
    return result
