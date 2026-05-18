import os
import json
from groq import Groq
from datetime import datetime
from services.probability import calculate_probabilities, get_bucket

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL_LARGE = "llama-3.3-70b-versatile"   # task extraction + advice
MODEL_SMALL = "llama-3.1-8b-instant"       # classification + chat replies (500K TPD)


def _parse_json_array(raw: str) -> list:
    """Robustly extract a JSON array from LLM output."""
    raw = raw.strip()
    # Strip markdown code fences
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:]).strip()
    # Find the first [ and last ] to extract just the array
    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end != -1:
        raw = raw[start:end + 1]
    return json.loads(raw)


def classify_intent(user_input: str, has_tasks: bool = False) -> str:
    """Returns 'task', 'update', or 'chat'."""
    task_note = " The user currently has existing tasks." if has_tasks else ""
    prompt = f"""You are an intent classifier for a productivity assistant app.{task_note}
Classify the following user input as "task", "update", or "chat".

- "task": the user is describing something they need to DO or complete — has a clear action/deliverable (e.g. "finish report", "call dentist", "submit homework by friday")
- "update": the user wants to modify, reschedule, mark done, or change an existing task
- "chat": questions, requests for advice, greetings, or anything that doesn't describe a new thing to do (e.g. "what should I do today?", "how am I doing?", "what's my priority?")

Reply with only one word: task, update, or chat.

Input: {user_input}"""

    response = client.chat.completions.create(
        model=MODEL_SMALL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=10,
    )
    result = response.choices[0].message.content.strip().lower()
    if "update" in result:
        return "update"
    if "task" in result:
        return "task"
    return "chat"


def extract_updates(user_input: str, tasks: list[dict]) -> list[dict]:
    """Extract task update instructions from user input, including semantic/relative updates."""
    task_list = "\n".join([
        f"- id:{t['id']} title:\"{t['title']}\" priority:{t['priority']} "
        f"status:{t.get('status','pending')} estimated_hours:{t.get('estimated_hours','null')} "
        f"finished_hours:{t.get('finished_hours', 0)} deadline:{t.get('deadline','null')}"
        for t in tasks
    ])
    prompt = f"""You are a task update assistant. The user may describe changes directly OR indirectly.
You must infer the correct NEW absolute value from the current task state and the user's intent.

Examples of indirect updates you must handle:
- "I finished half of X" → estimated_hours = current_estimated_hours / 2
- "I spent 2 hours on X" → estimated_hours = max(0, current_estimated_hours - 2), finished_hours = current_finished_hours + 2
- "I'm 75% done with X" → estimated_hours = current_estimated_hours * 0.25
- "X is almost done, maybe 30 min left" → estimated_hours = 0.5
- "mark X as done" → status = "done"
- "push X deadline back a day" → deadline = current_deadline + 1 day (compute the ISO string)
- "I'm working on X now" / "starting X" → working = true, working_start = {datetime.now().isoformat()}
- "I stopped working" / "taking a break" / "switching to Y" → working = false, working_start = null

Return a JSON array of update objects only (no markdown, no explanation).
Each object: {{"id": int, "fields": {{only changed fields with their NEW absolute values}}}}

Possible fields: title, description, deadline (ISO 8601), priority (high/medium/low), estimated_hours (number), finished_hours (number), status (pending/done), working (boolean), working_start (ISO 8601 or null)

Current tasks:
{task_list}

User input: {user_input}

Return only the JSON array. If no clear match, return []."""

    response = client.chat.completions.create(
        model=MODEL_SMALL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    raw = response.choices[0].message.content.strip()
    return _parse_json_array(raw)


def chat_reply(user_input: str, tasks: list[dict]) -> str:
    """Generate a conversational reply for non-task inputs."""
    task_lines = [f"- {t['title']}" for t in tasks] if tasks else []
    task_block = "\n".join(task_lines) if task_lines else "No tasks yet."

    response = client.chat.completions.create(
        model=MODEL_SMALL,
        messages=[
            {"role": "system", "content": (
                "You are HAL, a friendly personal productivity assistant. "
                "You help users manage their tasks and daily plans. "
                "Keep replies concise (2-4 sentences). "
                "If the user asks something completely unrelated to productivity or tasks, "
                "gently steer the conversation back."
            )},
            {"role": "user", "content": (
                f"The user's current tasks:\n{task_block}\n\nUser: {user_input}"
            )},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def extract_tasks(user_input: str) -> list[dict]:
    now = datetime.now()
    prompt = f"""You are a task extraction assistant.
Extract all tasks from the following input and return a JSON array only (no markdown, no explanation).
Each task must have these fields:
- "title": short task name (string)
- "description": details (string or null)
- "deadline": ISO 8601 datetime string (e.g. "2026-04-10T17:00:00") or null if not mentioned
- "priority": "high", "medium", or "low"
- "estimated_hours": number or null

Today is {now.strftime("%A, %B %d %Y")}. Use this to resolve relative dates like "next Monday" or "tomorrow".
If no specific time is mentioned for a deadline date, assume end of day (23:59:00).

Input:
{user_input}

Return only the JSON array."""

    response = client.chat.completions.create(
        model=MODEL_LARGE,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    raw = response.choices[0].message.content.strip()
    return _parse_json_array(raw)


def get_advice(tasks: list[dict], history: list[dict]) -> str:
    now = datetime.now().strftime("%A, %B %d %Y %H:%M")

    probs = calculate_probabilities(tasks)

    task_lines = []
    for t in tasks:
        deadline_str = f"deadline: {t['deadline']}" if t.get("deadline") else "no deadline"
        hours_remaining = t.get("estimated_hours") or 0
        hours_done = t.get("finished_hours") or 0
        hours_str = f", {hours_done}h done / {hours_remaining}h remaining" if hours_remaining else ""
        prob = probs.get(t["id"])
        prob_str = f", finish probability: {round(prob * 100)}% [{get_bucket(prob)}]" if prob is not None else ""
        task_lines.append(
            f"- [{t['priority'].upper()}] {t['title']} ({deadline_str}{hours_str}{prob_str})"
            + (f" — {t['description']}" if t.get("description") else "")
        )
    task_block = "\n".join(task_lines) if task_lines else "No pending tasks."

    history_lines = [f"{h['role'].capitalize()}: {h['content']}" for h in history[-10:]]
    history_block = "\n".join(history_lines) if history_lines else "No prior conversation."

    response = client.chat.completions.create(
        model=MODEL_SMALL,
        messages=[
            {"role": "system", "content": (
                "You are a personal productivity assistant. "
                "Use ONLY the exact hours and probabilities provided — never invent numbers. "
                "Be concise and direct."
            )},
            {"role": "user", "content": f"""The current time is {now}.

Pending tasks (use ONLY these numbers):
{task_block}

Recent conversation:
{history_block}

Produce a short action plan in this exact format (skip a section if not applicable):

**Now:**
<1-2 things to do right now, based on urgency and probability>

**Tomorrow:**
<1-2 things to schedule for tomorrow, if any tasks are due soon>

**Schedule tip:**
<one concrete suggestion on how to arrange time across these tasks>"""}
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def get_proactive_reminder(tasks: list[dict], probs: dict) -> str:
    """Single-sentence reminder for proactive triggers."""
    now = datetime.now().strftime("%A, %B %d %Y %H:%M")
    at_risk = [
        t for t in tasks
        if probs.get(t["id"]) is not None and probs[t["id"]] < 0.6
    ]
    task_lines = []
    for t in (at_risk or tasks[:2]):
        p = probs.get(t["id"])
        prob_str = f", {round(p*100)}% finish probability" if p is not None else ""
        hours_str = f", {t.get('estimated_hours')}h remaining" if t.get("estimated_hours") else ""
        task_lines.append(f"- {t['title']}{hours_str}{prob_str}")
    task_block = "\n".join(task_lines) if task_lines else "No tasks."

    response = client.chat.completions.create(
        model=MODEL_SMALL,
        messages=[
            {"role": "system", "content": "You are a productivity assistant. Write one short reminder sentence (max 20 words). Be specific, mention the task name."},
            {"role": "user", "content": f"Current time: {now}\nTasks:\n{task_block}\n\nWrite one reminder sentence."}
        ],
        temperature=0.7,
        max_tokens=60,
    )
    return response.choices[0].message.content.strip()
