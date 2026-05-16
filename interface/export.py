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
