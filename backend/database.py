from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./assistant.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    deadline = Column(DateTime, nullable=True)
    priority = Column(String, default="medium")  # high / medium / low
    status = Column(String, default="pending")   # pending / done
    estimated_hours = Column(Float, nullable=True)
    finished_hours = Column(Float, default=0.0, nullable=True)
    working = Column(Boolean, default=False)
    working_start = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TaskLog(Base):
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, nullable=False, index=True)
    prompt = Column(Text, nullable=False)       # user's original message
    changes = Column(Text, nullable=False)      # JSON string of changed fields
    created_at = Column(DateTime, default=datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String, nullable=False)   # user / assistant
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class ScheduleBlock(Base):
    __tablename__ = "schedule_blocks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    start_time = Column(String, nullable=False)   # "HH:MM"
    end_time = Column(String, nullable=False)     # "HH:MM"
    recurrence = Column(String, default="daily")  # "none" | "daily" | "weekly"
    day_of_week = Column(Integer, nullable=True)  # 0=Mon..6=Sun, only for weekly
    date = Column(String, nullable=True)          # "YYYY-MM-DD", only for one-time


class UserPreference(Base):
    __tablename__ = "user_preferences"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    # Add finished_hours column if it doesn't exist (for existing DBs)
    with engine.connect() as conn:
        for col_sql in [
            "ALTER TABLE tasks ADD COLUMN finished_hours REAL DEFAULT 0.0",
            "ALTER TABLE tasks ADD COLUMN working INTEGER DEFAULT 0",
            "ALTER TABLE tasks ADD COLUMN working_start DATETIME",
        ]:
            try:
                conn.execute(__import__('sqlalchemy').text(col_sql))
                conn.commit()
            except Exception:
                pass
    # Seed default preferences
    db = SessionLocal()
    existing = db.query(UserPreference).filter_by(key="notification_threshold_hours").first()
    if not existing:
        db.add(UserPreference(key="notification_threshold_hours", value="24"))
        db.commit()
    db.close()
