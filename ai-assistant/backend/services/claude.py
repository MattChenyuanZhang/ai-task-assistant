import os
import json
import anthropic
from datetime import datetime

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-opus-4-6"


def extract_tasks(user_input: str) -> list[dict]:
    """Extract structured tasks from free-form text/voice input."""
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

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.splitlines()
        inner = lines[1:]
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        raw = "\n".join(inner).strip()
    return json.loads(raw)


def get_advice(tasks: list[dict], history: list[dict]) -> str:
    """Generate time-aware, chain-of-thought advice based on tasks and history."""
    now = datetime.now().strftime("%A, %B %d %Y %H:%M")

    task_lines = []
    for t in tasks:
        deadline_str = f"deadline: {t['deadline']}" if t.get("deadline") else "no deadline"
        hours_str = f", ~{t['estimated_hours']}h" if t.get("estimated_hours") else ""
        task_lines.append(
            f"- [{t['priority'].upper()}] {t['title']} ({deadline_str}{hours_str}) — {t.get('description') or 'no description'}"
        )
    task_block = "\n".join(task_lines) if task_lines else "No pending tasks."

    history_lines = [f"{h['role'].capitalize()}: {h['content']}" for h in history[-10:]]
    history_block = "\n".join(history_lines) if history_lines else "No prior conversation."

    system_prompt = "You are a personal productivity assistant."

    user_prompt = f"""The current time is {now}.

Here are the user's pending tasks:
{task_block}

Recent conversation context:
{history_block}

First, reason step by step about urgency, workload, and priorities.
Then give 3-5 specific, actionable suggestions tailored to the current time and deadlines.

Format your response exactly like this:
**Reasoning:**
<your step-by-step reasoning here>

**Suggestions:**
<numbered list of 3-5 actionable suggestions>"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text.strip()
