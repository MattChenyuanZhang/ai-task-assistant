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
Classify the input as "task", "update", or "chat".

- "task": adding a NEW thing to do. Has a clear deliverable. e.g. "finish report by friday", "call dentist tomorrow"
- "update": changing an EXISTING task. e.g. "mark report done", "i finished half", "working on it now", "push deadline back"
- "chat": everything else — questions, advice requests, greetings, schedule questions. e.g. "what should i do now?", "work until which clock", "how am i doing", "what's due today", "hi"

Examples:
"finish the essay by monday" → task
"i'm done with the report" → update
"what should i work on first?" → chat
"work until which clock" → chat
"can you help me plan today?" → chat
"add gym session tomorrow" → task
"push report deadline to friday" → update
"how long do i have left?" → chat

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


_ACTION_VERBS = {
    "finish", "complete", "do", "submit", "write", "read", "call", "send",
    "fix", "review", "prepare", "make", "buy", "get", "check", "update",
    "clean", "organize", "schedule", "book", "file", "pay", "study", "practice"
}

def _clean_title(title: str) -> str:
    words = title.strip().split()
    if words and words[0].lower() in _ACTION_VERBS:
        words = words[1:]
    result = " ".join(words).strip()
    return result.title() if result else title.title()


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
    tasks = _parse_json_array(raw)
    for t in tasks:
        if t.get("title"):
            t["title"] = _clean_title(t["title"])
    return tasks


def get_advice(tasks: list[dict], history: list[dict]) -> str:
    now_dt = datetime.now()
    now = now_dt.strftime("%A, %B %d %Y %H:%M")
    hour = now_dt.hour

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
                "Always give specific time slots (e.g. 'start at 9am, work for 3h'). "
                "Be concise and direct."
            )},
            {"role": "user", "content": f"""The current time is {now}.
{"It is late at night — do NOT suggest starting work now. Suggest sleep and a specific start time tomorrow morning." if hour >= 22 or hour < 5 else ""}

Pending tasks (use ONLY these numbers):
{task_block}

Recent conversation:
{history_block}

Produce an action plan. For each section, give SPECIFIC time slots and reference the exact hours from the data above:

**Now:**
<what to do immediately — or if late night, say to sleep and give a specific wake-up time>

**Tomorrow:**
<specific time block, e.g. "9am–2pm: work on X (5h)">

**Schedule tip:**
<one concrete tip based on the deadlines and probabilities above>"""}
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def proactive_check(
    tasks: list[dict],
    minutes_inactive: float,
    working_task_title: str | None,
    working_minutes: float | None,
    history: list[dict] | None = None,
) -> str | None:
    """Ask the LLM whether to say something proactively. Returns a message or None."""
    now = datetime.now()
    now_str = now.strftime("%A, %B %d %Y %H:%M")
    hour = now.hour

    probs = calculate_probabilities(tasks)
    task_lines = []
    for t in tasks:
        p = probs.get(t["id"])
        prob_str = f", {round(p * 100)}% finish prob" if p is not None else ""
        hours_left = t.get("estimated_hours") or 0
        done = t.get("finished_hours") or 0
        deadline = t.get("deadline") or "no deadline"
        working_flag = " [CURRENTLY WORKING]" if t.get("working") else ""
        task_lines.append(
            f"- {t['title']}: {done:.1f}h done / {hours_left:.1f}h left, deadline: {deadline}{prob_str}{working_flag}"
        )
    task_block = "\n".join(task_lines) if task_lines else "No pending tasks."

    working_ctx = ""
    if working_task_title and working_minutes is not None:
        working_ctx = f"\nThe user has been working on \"{working_task_title}\" for {working_minutes:.0f} minutes without stopping."

    late_night_ctx = ""
    if hour >= 23 or hour < 5:
        late_night_ctx = "\nNote: it is late at night."
    elif hour >= 22:
        late_night_ctx = "\nNote: it is getting late in the evening."

    history_lines = [f"{h['role'].capitalize()}: {h['content']}" for h in (history or [])[-6:]]
    history_block = "\n".join(history_lines) if history_lines else "No prior conversation."

    prompt = f"""You are HAL, a calm and intelligent productivity assistant.

Current time: {now_str}{late_night_ctx}
User has been inactive for: {minutes_inactive:.0f} minutes{working_ctx}

Pending tasks:
{task_block}

Recent conversation (do NOT repeat anything already said):
{history_block}

Decide: should you say something to the user right now?

Consider things like:
- It's very late — maybe they should rest
- They've been working for a long time without a break
- A task deadline is dangerously close
- They've been idle a long time and have urgent tasks
- All tasks are done — acknowledge it
- Nothing noteworthy is happening — stay silent

If you should say something: reply with a short, natural message (1-2 sentences max). Be warm, not robotic.
If you should stay silent: reply with exactly the word: null"""

    response = client.chat.completions.create(
        model=MODEL_SMALL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=80,
    )
    result = response.choices[0].message.content.strip()
    if not result or "null" in result.lower()[:10]:
        return None
    return result
