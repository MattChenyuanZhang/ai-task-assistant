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

- "task": anything that sounds like work to be done — even terse notes like "report friday" or "call dentist". When in doubt, prefer "task".
- "update": the user wants to modify, reschedule, mark done, delete, or change an existing task
- "chat": ONLY clear general questions, greetings, or things completely unrelated to tasks

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

Return a JSON array of update objects only (no markdown, no explanation).
Each object: {{"id": int, "fields": {{only changed fields with their NEW absolute values}}}}

Possible fields: title, description, deadline (ISO 8601), priority (high/medium/low), estimated_hours (number), finished_hours (number), status (pending/done)

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
    prompt = f"""You are a task extraction assistant.
Extract all tasks from the following input and return a JSON array only (no markdown, no explanation).
Each task must have these fields:
- "title": short task name (string)
- "description": details (string or null)
- "deadline": ISO 8601 datetime string (e.g. "2026-04-10T17:00:00") or null if not mentioned
- "priority": "high", "medium", or "low"
- "estimated_hours": number or null

If no deadline year is mentioned, assume the current year is {datetime.utcnow().year}.
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
                "You will be given task data including exact estimated hours remaining and finish probabilities. "
                "CRITICAL RULES: "
                "1. Never invent or suggest time allocations — only reference the exact hours provided in the data. "
                "2. Never contradict the provided numbers. If a task has 1h remaining, say 1 hour, not 10. "
                "3. Base every suggestion strictly on the data given. "
                "4. Keep suggestions concise and actionable."
            )},
            {"role": "user", "content": f"""The current time is {now}.

Here are the user's pending tasks. Use ONLY these numbers — do not invent any:
{task_block}

Recent conversation:
{history_block}

Reason about which tasks are most at risk using their finish probabilities and hours remaining.
Give 3-5 specific suggestions. Every time estimate you mention must come directly from the data above.

Format:
**Reasoning:**
<reasoning using exact numbers from the data>

**Suggestions:**
<numbered list of 3-5 suggestions using only the provided hours and probabilities>"""}
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()
