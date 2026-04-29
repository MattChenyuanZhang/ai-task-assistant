# From command line:
# Step1: Input the task name from the command line
# Step2: Input the deadline from the command line
# Step3: Input the time estimated for the task from the command line
# Step4: Input any updates on the task from the command line


# Calculate the time remaining until the deadline

# Calculate the possibility of completing the task on time based on the time remaining and the estimated time for the task

from __future__ import annotations

from datetime import datetime # For parsing and handling date and time

# Define the supported date formats for parsing the deadline input
DATE_FORMATS = (
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y",
)

# Parses a deadline string into a datetime object. Supports multiple formats.
def parse_deadline(deadline_text: str):
    for fmt in DATE_FORMATS:  # Try each format until one works
        try:
            # Parse the deadline text using the current format
            parsed = datetime.strptime(deadline_text.strip(), fmt)
            # If the format only includes a date (no time), set the time to 23:59 to represent the end of that day
            if fmt in ("%Y-%m-%d", "%m/%d/%Y"):
                return parsed.replace(hour=23, minute=59, second=59)
            return parsed
        except ValueError:
            continue
    raise ValueError(
        "Invalid deadline format. Use one of: "
        "YYYY-MM-DD HH:MM, YYYY-MM-DD, MM/DD/YYYY HH:MM, MM/DD/YYYY"
    )

# Note: Need to modify a lot
def completion_probability(
    hours_remaining_until_deadline: float, estimated_hours_left: float
) -> float:
    if estimated_hours_left <= 0:
        return 100.0
    if hours_remaining_until_deadline <= 0:
        return 0.0

    ratio = hours_remaining_until_deadline / estimated_hours_left
    if ratio >= 1.5:
        return 95.0
    if ratio >= 1.2:
        return 80.0
    if ratio >= 1.0:
        return 65.0
    if ratio >= 0.8:
        return 40.0
    return 15.0

# Asks the user for a floating-point number, with an optional prompt and minimum.
def ask_float(prompt: str = "Estimated hours needed: ", minimum: float = 0.0):
    while True:
        raw = input(prompt).strip()
        try:
            value = float(raw) # Try to convert the input to a float
            if value < minimum:
                print(f"Please enter a value >= {minimum}.")
                continue
            return value
        except ValueError:
            print("Please enter a valid number.")


def main() -> None:
    # Step1: Input the task name from the command line
    print("Task Completion Predictor\n")
    task_name = input("Task name: ").strip()
    # If the user doesn't provide a task name, use a default one
    if not task_name:
        task_name = "Untitled task"

    deadline = None
    while deadline is None:
        deadline_input = input(
            "Deadline: "
        )
        try:  # Try to parse the deadline, if it fails, ask again
            deadline = parse_deadline(deadline_input)
        except ValueError as exc:
            print(exc)

    estimate_hours = ask_float(minimum=0.0)
    hours_done = ask_float(
        "Optional - Hours already completed (0 if none): ", minimum=0.0
    )

    now = datetime.now()
    time_remaining_hours = (deadline - now).total_seconds() / 3600
    estimated_hours_left = max(estimate_hours - hours_done, 0.0)
    chance = completion_probability(time_remaining_hours, estimated_hours_left)

    print("\n--- Result ---")
    print(f"Task: {task_name}")
    print(f"Now: {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"Deadline: {deadline.strftime('%Y-%m-%d %H:%M')}")

    if time_remaining_hours >= 0:
        print(f"Time remaining: {time_remaining_hours:.2f} hours")
    else:
        print(f"Deadline passed by: {abs(time_remaining_hours):.2f} hours")

    print(f"Estimated hours left: {estimated_hours_left:.2f}")
    print(f"Predicted chance of finishing on time: {chance:.1f}%")


if __name__ == "__main__":
    main()
