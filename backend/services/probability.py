from datetime import datetime

SLEEP_HOURS_PER_DAY = 8
FREE_FRACTION = (24 - SLEEP_HOURS_PER_DAY) / 24  # 16/24


def free_hours(deadline_iso: str) -> float:
    deadline = datetime.fromisoformat(deadline_iso)
    hours_raw = (deadline - datetime.now()).total_seconds() / 3600
    return max(0.0, hours_raw * FREE_FRACTION)


def calculate_probabilities(tasks: list[dict]) -> dict:
    """
    P(i) = 1 - E_i / T_left_i
    T_left_i = F_i - sum(j!=i) [ P_j * E_j * (F_i - E_j/2) / F_i ]
    F_i = free hours before deadline (16/24 of raw time)
    """
    eligible = [
        t for t in tasks
        if t.get("status") == "pending"
        and t.get("deadline")
        and t.get("estimated_hours", 0) > 0
    ]

    if not eligible:
        return {}

    F = {t["id"]: free_hours(t["deadline"]) for t in eligible}

    # Initial naive estimate
    P = {
        t["id"]: min(1.0, max(0.0, 1 - t["estimated_hours"] / F[t["id"]]))
        if F[t["id"]] > 0 else 0.0
        for t in eligible
    }

    for _ in range(30):
        max_diff = 0.0
        new_P = {}
        for ti in eligible:
            Fi = F[ti["id"]]
            Ei = ti["estimated_hours"]
            if Fi <= 0:
                new_P[ti["id"]] = 0.0
                continue
            stolen = sum(
                P[tj["id"]] * tj["estimated_hours"] * (Fi - tj["estimated_hours"] / 2) / Fi
                for tj in eligible
                if tj["id"] != ti["id"]
                and max(0.0, P[tj["id"]] * tj["estimated_hours"] * (Fi - tj["estimated_hours"] / 2) / Fi) > 0
            )
            Tleft = max(0.0, Fi - stolen)
            new_p = min(1.0, max(0.0, 1 - Ei / Tleft)) if Tleft > 0 else 0.0
            max_diff = max(max_diff, abs(new_p - P[ti["id"]]))
            new_P[ti["id"]] = new_p
        P = new_P
        if max_diff < 0.001:
            break

    return P


def get_bucket(p: float) -> str:
    if p > 0.80: return "safe"
    if p > 0.60: return "watch"
    if p > 0.40: return "at-risk"
    if p > 0.20: return "danger"
    return "critical"
