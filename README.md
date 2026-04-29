# AI Task Assistant

An AI-powered productivity tool that helps you manage tasks, predict deadlines, and get personalized scheduling advice — built with FastAPI, React, and the Claude API.

## Features

- **Natural language task input** — type or speak tasks in plain English and let Claude extract titles, deadlines, priorities, and time estimates automatically
- **Deadline prediction** — calculates the probability of finishing a task on time based on hours remaining vs. estimated effort
- **AI advice** — generates step-by-step reasoning and actionable suggestions based on your current workload and deadlines
- **Task management** — create, update, and delete tasks with priority and status tracking
- **Urgent task detection** — surfaces tasks that need immediate attention
- **CLI tool** — lightweight command-line version for quick deadline checks without the web app

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, Axios |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | SQLite |
| AI | Claude API (claude-opus-4-6) |

## Project Structure

```
├── predictor.py              # Standalone CLI deadline predictor
└── ai-assistant/
    ├── backend/
    │   ├── main.py           # FastAPI app entry point
    │   ├── database.py       # SQLAlchemy models and DB setup
    │   ├── routers/          # API route handlers (tasks, chat, extract, schedule)
    │   └── services/         # Claude API integration and deadline logic
    └── frontend/
        └── src/
            ├── App.jsx
            ├── components/   # TaskList, AdvicePanel, SchedulePanel, VoiceInput
            └── api/          # Axios API client
```

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com/)

### Backend

```bash
cd ai-assistant
cp .env.example .env          # Add your ANTHROPIC_API_KEY
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

The API will be available at `http://localhost:8000`.

### Frontend

```bash
cd ai-assistant/frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

### CLI Tool

```bash
python predictor.py
```

Follow the prompts to enter a task name, deadline, and estimated hours. The tool outputs the predicted probability of finishing on time.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tasks` | List all tasks |
| POST | `/api/tasks` | Create a task |
| PATCH | `/api/tasks/{id}` | Update a task |
| DELETE | `/api/tasks/{id}` | Delete a task |
| GET | `/api/tasks/urgent` | Get urgent tasks |
| POST | `/api/extract` | Extract tasks from free-form text |
| POST | `/api/chat` | Get AI advice on current workload |
| GET | `/api/schedule` | Get schedule suggestions |
