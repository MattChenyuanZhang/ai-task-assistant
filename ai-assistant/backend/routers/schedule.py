from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date as date_type
from typing import Optional

from database import get_db, ScheduleBlock

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


class BlockCreate(BaseModel):
    title: str
    start_time: str          # "HH:MM"
    end_time: str            # "HH:MM"
    recurrence: str = "daily"  # "none" | "daily" | "weekly"
    day_of_week: Optional[int] = None
    date: Optional[str] = None  # "YYYY-MM-DD"


def block_to_dict(b: ScheduleBlock) -> dict:
    return {
        "id": b.id,
        "title": b.title,
        "start_time": b.start_time,
        "end_time": b.end_time,
        "recurrence": b.recurrence,
        "day_of_week": b.day_of_week,
        "date": b.date,
    }


@router.get("/today")
def get_today_blocks(db: Session = Depends(get_db)):
    today = date_type.today()
    today_str = today.isoformat()
    today_dow = today.weekday()  # 0=Mon, 6=Sun

    result = []
    for b in db.query(ScheduleBlock).all():
        if b.recurrence == "daily":
            result.append(block_to_dict(b))
        elif b.recurrence == "weekly" and b.day_of_week == today_dow:
            result.append(block_to_dict(b))
        elif b.recurrence == "none" and b.date == today_str:
            result.append(block_to_dict(b))

    return sorted(result, key=lambda x: x["start_time"])


@router.get("")
def list_blocks(db: Session = Depends(get_db)):
    return [block_to_dict(b) for b in db.query(ScheduleBlock).order_by(ScheduleBlock.start_time).all()]


@router.post("", status_code=201)
def create_block(body: BlockCreate, db: Session = Depends(get_db)):
    block = ScheduleBlock(**body.model_dump())
    db.add(block)
    db.commit()
    db.refresh(block)
    return block_to_dict(block)


@router.delete("/{block_id}", status_code=204)
def delete_block(block_id: int, db: Session = Depends(get_db)):
    block = db.query(ScheduleBlock).filter(ScheduleBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    db.delete(block)
    db.commit()
