import io
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_COLUMNS = ["Name", "Primary Muscles", "Equipment", "Difficulty"]


def generate_reference_sheet(exercises: list[dict]) -> bytes:
    rows = [
        [
            ex.get("name", "")[:35],
            ", ".join(ex.get("primary_muscles", []))[:40],
            ex.get("equipment", ""),
            ex.get("difficulty", ""),
        ]
        for ex in exercises
    ]

    n_rows = len(rows)
    fig_height = max(2.0, 0.45 * n_rows + 1.5)
    fig, ax = plt.subplots(figsize=(10, fig_height))
    ax.axis("off")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    ax.set_title(
        f"TrainFlow — Workout Reference Sheet\n{timestamp}",
        fontsize=13,
        pad=12,
    )

    if rows:
        table = ax.table(
            cellText=rows,
            colLabels=_COLUMNS,
            loc="center",
            cellLoc="left",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.auto_set_column_width(col=list(range(len(_COLUMNS))))

        for col in range(len(_COLUMNS)):
            table[(0, col)].set_facecolor("#2d2d2d")
            table[(0, col)].set_text_props(color="white", fontweight="bold")

        for row in range(1, n_rows + 1):
            bg = "#f5f5f5" if row % 2 == 0 else "white"
            for col in range(len(_COLUMNS)):
                table[(row, col)].set_facecolor(bg)
    else:
        ax.text(
            0.5, 0.5,
            "No exercises to display",
            ha="center", va="center",
            transform=ax.transAxes,
            fontsize=11, color="#888888",
        )

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


_PROVIDER_NAMES = {"gemini": "Gemini", "anthropic": "Anthropic", "llm": "AI", "fallback": "Built-in planner"}


def _plan_lines(plan: dict) -> list[tuple[str, str]]:
    """Return (style, text) lines describing the plan, for rendering."""
    lines: list[tuple[str, str]] = []
    goal = plan.get("goal", "")
    provider = _PROVIDER_NAMES.get(str(plan.get("generated_by", "")).lower(), "")
    subtitle = f"Goal: {goal}"
    if provider:
        subtitle += f"   ·   Coach: {provider}"
    lines.append(("subtitle", subtitle))

    for insight in plan.get("insights", []):
        lines.append(("insight", f"• {insight}"))

    for index, day in enumerate(plan.get("days", []), start=1):
        lines.append(("day", f"Day {index} — {day.get('focus', 'Workout')}"))
        for item in day.get("items", []):
            name = item.get("exercise_name") or f"#{item.get('exercise_id')}"
            meta = f"{item.get('sets')} sets x {item.get('reps')} reps · {item.get('rest_seconds')}s rest"
            lines.append(("item", f"{name} — {meta}"))
            if item.get("rationale"):
                lines.append(("why", f"    {item['rationale']}"))

    if plan.get("notes"):
        lines.append(("notes", f"Coach notes: {plan['notes']}"))
    return lines


def generate_plan_sheet(plan: dict) -> bytes:
    """Render a generated Coach plan as a clean, readable PNG (no raw JSON)."""
    lines = _plan_lines(plan or {})

    fig_height = max(3.0, 0.32 * (len(lines) + 4))
    fig, ax = plt.subplots(figsize=(9, fig_height))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    ax.text(0.0, 1.0, "TrainFlow — Workout Plan", fontsize=17, fontweight="bold",
            color="#0a6e54", va="top")

    styles = {
        "subtitle": dict(fontsize=11, color="#444444", fontweight="bold"),
        "insight": dict(fontsize=9.5, color="#0a6e54", style="italic"),
        "day": dict(fontsize=12, color="#111111", fontweight="bold"),
        "item": dict(fontsize=10, color="#222222"),
        "why": dict(fontsize=8.5, color="#777777", style="italic"),
        "notes": dict(fontsize=9.5, color="#444444", style="italic"),
    }

    y = 0.92
    step = 0.9 / max(1, len(lines) + 1)
    for kind, text in lines:
        if kind == "day":
            y -= step * 0.4
        ax.text(0.02, y, text[:110], va="top", **styles.get(kind, {}))
        y -= step

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=130, facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
