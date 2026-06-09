"""Lightweight styling helpers for the TrainFlow UI.

CSS is injected once; the HTML builders are pure functions (no Streamlit
imports) so they can be unit-tested. All dynamic text is HTML-escaped.
"""

import html as _html

ACCENT = "#00e5a0"

_CSS = f"""
<style>
:root {{ --tf-accent: {ACCENT}; }}

.stApp {{
  background:
    radial-gradient(1200px 600px at 10% -10%, rgba(0,229,160,0.07), transparent 60%),
    radial-gradient(900px 500px at 100% 0%, rgba(124,108,255,0.08), transparent 55%),
    #0c0f14;
}}

/* Headings + general type */
h1, h2, h3 {{ letter-spacing: -0.02em; }}

/* Hero banner */
.tf-hero {{
  border-radius: 18px;
  padding: 26px 30px;
  margin-bottom: 8px;
  background: linear-gradient(135deg, rgba(0,229,160,0.14), rgba(124,108,255,0.12)), #11161e;
  border: 1px solid rgba(255,255,255,0.06);
  box-shadow: 0 10px 30px rgba(0,0,0,0.35);
}}
.tf-hero h1 {{ margin: 0 0 6px 0; font-size: 1.9rem; }}
.tf-hero .tf-tagline {{ color: #aeb7c2; font-size: 1.02rem; margin-bottom: 14px; }}
.tf-hero .tf-meta {{ display: flex; gap: 10px; flex-wrap: wrap; }}
.tf-hero-center {{ text-align: center; }}
.tf-hero-center .tf-tagline {{ margin-left: auto; margin-right: auto; max-width: 520px; }}
.tf-hero-center .tf-meta {{ justify-content: center; }}

/* Generic card */
.tf-card {{
  background: #141a22;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  padding: 18px 20px;
}}

/* Metric cards — fixed min-height so all cards line up regardless of content */
.tf-metric {{
  background: #141a22;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  padding: 18px 18px 16px;
  height: 100%;
  min-height: 140px;
  display: flex;
  flex-direction: column;
}}
.tf-metric .tf-metric-label {{
  color: #8b97a5; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em;
}}
.tf-metric .tf-metric-value {{ font-size: 2.1rem; font-weight: 700; line-height: 1.1; margin-top: 6px; }}
.tf-metric .tf-metric-sub {{ color: #7f8b99; font-size: 0.82rem; margin-top: auto; padding-top: 8px; }}
.tf-metric .tf-metric-value.accent {{ color: var(--tf-accent); }}
.tf-metric .tf-metric-chips {{ margin-top: 10px; line-height: 1.9; }}

/* Pills / badges */
.tf-badge {{
  display: inline-block; padding: 3px 10px; border-radius: 999px;
  font-size: 0.74rem; font-weight: 600; margin: 2px 4px 2px 0;
  border: 1px solid rgba(255,255,255,0.10); color: #cdd6e0; background: #1b222c;
}}
.tf-badge.muscle {{ color: var(--tf-accent); border-color: rgba(0,229,160,0.35); background: rgba(0,229,160,0.08); }}
.tf-badge.equipment {{ color: #9db4ff; border-color: rgba(124,140,255,0.35); background: rgba(124,140,255,0.08); }}
.tf-badge.difficulty {{ color: #ffd58a; border-color: rgba(255,196,92,0.30); background: rgba(255,196,92,0.08); }}
.tf-badge.status-ok {{ color: var(--tf-accent); border-color: rgba(0,229,160,0.35); }}
.tf-badge.status-muted {{ color: #aeb7c2; }}

/* Plan day + exercise item cards */
.tf-day {{
  background: #141a22; border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px; padding: 16px 18px; margin-bottom: 14px;
}}
.tf-day .tf-day-head {{ display: flex; align-items: baseline; gap: 10px; margin-bottom: 10px; }}
.tf-day .tf-day-num {{ color: var(--tf-accent); font-weight: 700; font-size: 0.8rem; letter-spacing: 0.08em; }}
.tf-day .tf-day-focus {{ font-weight: 600; font-size: 1.05rem; }}
.tf-item {{
  background: #0f141b; border: 1px solid rgba(255,255,255,0.05);
  border-radius: 12px; padding: 12px 14px; margin-bottom: 10px;
}}
.tf-item .tf-item-name {{ font-weight: 600; font-size: 1.0rem; }}
.tf-item .tf-item-meta {{ color: #aeb7c2; font-size: 0.86rem; margin-top: 3px; }}
.tf-item .tf-item-why {{ color: #8b97a5; font-size: 0.84rem; font-style: italic; margin-top: 6px; }}

/* Highlighted coach panel */
.tf-panel {{
  border-radius: 14px; padding: 14px 16px; margin-bottom: 10px;
  background: rgba(0,229,160,0.07); border: 1px solid rgba(0,229,160,0.25); color: #d7f5ea;
}}

/* History timeline cards */
.tf-session {{
  background: #141a22; border: 1px solid rgba(255,255,255,0.06);
  border-left: 3px solid var(--tf-accent);
  border-radius: 12px; padding: 14px 16px; margin-bottom: 12px;
}}
.tf-session .tf-session-head {{ display: flex; justify-content: space-between; gap: 12px; }}
.tf-session .tf-session-date {{ font-weight: 600; }}
.tf-session .tf-session-goal {{ color: var(--tf-accent); font-size: 0.85rem; }}
.tf-session .tf-session-notes {{ color: #8b97a5; font-size: 0.86rem; margin-top: 4px; }}

.tf-empty {{
  text-align: center; padding: 36px 20px; color: #8b97a5;
  border: 1px dashed rgba(255,255,255,0.12); border-radius: 16px; background: #11161e;
}}
.tf-empty .tf-empty-title {{ color: #cdd6e0; font-weight: 600; font-size: 1.05rem; margin-bottom: 6px; }}

/* Sidebar navigation — keep st.radio (reliable) but hide the radio dots and
   render options as clean, full-width menu rows. */
section[data-testid="stSidebar"] div[role="radiogroup"] {{ gap: 4px; }}
section[data-testid="stSidebar"] div[role="radiogroup"] > label {{
  width: 100%; margin: 0; padding: 9px 12px;
  border-radius: 10px; border: 1px solid transparent; cursor: pointer;
}}
section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {{
  display: none;  /* hide the radio circle */
}}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {{
  background: rgba(255,255,255,0.05);
}}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {{
  background: rgba(0,229,160,0.12); border-color: rgba(0,229,160,0.30);
}}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p {{
  color: var(--tf-accent); font-weight: 600;
}}

/* Buttons — global, readable on dark. Base = dark neutral with light text. */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
  border-radius: 10px; font-weight: 600;
  background-color: #1b222c; color: #e6edf3;
  border: 1px solid rgba(255,255,255,0.14);
}}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {{
  background-color: #232c39; color: #ffffff; border-color: rgba(255,255,255,0.26);
}}
.stButton > button:focus, .stDownloadButton > button:focus, .stFormSubmitButton > button:focus {{
  box-shadow: 0 0 0 2px rgba(0,229,160,0.35) !important;
}}

/* Primary / CTA: dark text on bright green for strong contrast. */
button[kind="primary"], button[kind="primaryFormSubmit"],
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {{
  background-color: var(--tf-accent) !important;
  color: #06231b !important;
  border: 1px solid var(--tf-accent) !important;
  font-weight: 700 !important;
}}
button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover,
[data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover {{
  background-color: #00c98c !important;
  color: #06231b !important;
  border-color: #00c98c !important;
}}
</style>
"""


def styles() -> str:
    """Return the CSS block (also used by inject)."""
    return _CSS


def _esc(value) -> str:
    return _html.escape(str(value)) if value is not None else ""


def badge(text, kind: str = "") -> str:
    cls = f"tf-badge {kind}".strip()
    return f'<span class="{cls}">{_esc(text)}</span>'


def badges(items, kind: str = "") -> str:
    return "".join(badge(item, kind) for item in (items or []))


def hero(title: str, tagline: str, meta_html: str = "", center: bool = False) -> str:
    cls = "tf-hero tf-hero-center" if center else "tf-hero"
    meta = f'<div class="tf-meta">{meta_html}</div>' if meta_html else ""
    return (
        f'<div class="{cls}"><h1>{_esc(title)}</h1>'
        f'<div class="tf-tagline">{_esc(tagline)}</div>{meta}</div>'
    )


def metric_card(label: str, value, sub: str = "", accent: bool = False) -> str:
    value_cls = "tf-metric-value accent" if accent else "tf-metric-value"
    sub_html = f'<div class="tf-metric-sub">{_esc(sub)}</div>' if sub else ""
    return (
        f'<div class="tf-metric"><div class="tf-metric-label">{_esc(label)}</div>'
        f'<div class="{value_cls}">{_esc(value)}</div>{sub_html}</div>'
    )


def metric_chip_card(label: str, chips: list[str], more: int = 0, sub: str = "") -> str:
    """A metric card whose value is a compact row of badges (e.g. recent focus
    muscles), keeping the same height as value-based cards."""
    if chips:
        chip_html = badges(chips, "muscle")
        if more > 0:
            chip_html += badge(f"+{more} more", "status-muted")
    else:
        chip_html = '<span class="tf-metric-sub">—</span>'
    sub_html = f'<div class="tf-metric-sub">{_esc(sub)}</div>' if sub else ""
    return (
        f'<div class="tf-metric"><div class="tf-metric-label">{_esc(label)}</div>'
        f'<div class="tf-metric-chips">{chip_html}</div>{sub_html}</div>'
    )


PROVIDER_LABELS = {
    "gemini": "Gemini",
    "anthropic": "Anthropic",
    "fallback": "Built-in planner",
    "llm": "AI",
}


def provider_label(provider) -> str:
    return PROVIDER_LABELS.get(str(provider or "").lower(), "Unknown")


def provider_badge(provider) -> str:
    label = provider_label(provider)
    kind = "status-ok" if str(provider or "").lower() in ("gemini", "anthropic", "llm") else "status-muted"
    return badge(f"Coach: {label}", kind)


def exercise_card(exercise: dict) -> str:
    name = _esc(exercise.get("name", "Unnamed"))
    muscle_html = badges(exercise.get("primary_muscles", []), "muscle")
    equip_html = badge(exercise.get("equipment", ""), "equipment") if exercise.get("equipment") else ""
    diff_html = badge(exercise.get("difficulty", ""), "difficulty") if exercise.get("difficulty") else ""
    return (
        f'<div class="tf-card" style="margin-bottom:12px">'
        f'<div class="tf-item-name">{name}</div>'
        f'<div style="margin-top:8px">{muscle_html}{equip_html}{diff_html}</div></div>'
    )


def plan_item_card(item: dict, catalog_by_id: dict | None = None) -> str:
    catalog_by_id = catalog_by_id or {}
    name = _esc(item.get("exercise_name") or f"#{item.get('exercise_id')}")
    sets = _esc(item.get("sets"))
    reps = _esc(item.get("reps"))
    rest = _esc(item.get("rest_seconds"))
    meta = f"{sets} sets × {reps} reps · {rest}s rest"
    why = item.get("rationale")
    why_html = f'<div class="tf-item-why">{_esc(why)}</div>' if why else ""

    badge_html = ""
    catalog = catalog_by_id.get(item.get("exercise_id"))
    if catalog:
        badge_html = (
            '<div style="margin-top:8px">'
            + badges(catalog.get("primary_muscles", []), "muscle")
            + (badge(catalog.get("equipment", ""), "equipment") if catalog.get("equipment") else "")
            + "</div>"
        )
    return (
        f'<div class="tf-item"><div class="tf-item-name">{name}</div>'
        f'<div class="tf-item-meta">{meta}</div>{why_html}{badge_html}</div>'
    )


def plan_day_card(index: int, focus: str, items: list[dict], catalog_by_id: dict | None = None) -> str:
    items_html = "".join(plan_item_card(i, catalog_by_id) for i in items)
    return (
        f'<div class="tf-day"><div class="tf-day-head">'
        f'<span class="tf-day-num">DAY {int(index)}</span>'
        f'<span class="tf-day-focus">{_esc(focus or "Workout")}</span></div>'
        f"{items_html}</div>"
    )


def insight_panel(text: str) -> str:
    return f'<div class="tf-panel">{_esc(text)}</div>'


def session_card(session: dict, item_lines: list[str], show_owner: bool = False) -> str:
    owner = session.get("owner")
    owner_html = (
        f'<span class="tf-session-goal">· {_esc(owner)}</span>' if show_owner and owner else ""
    )
    notes = session.get("notes")
    notes_html = f'<div class="tf-session-notes">{_esc(notes)}</div>' if notes else ""
    lines = "".join(f'<div class="tf-item-meta">{_esc(line)}</div>' for line in item_lines)
    return (
        f'<div class="tf-session"><div class="tf-session-head">'
        f'<span class="tf-session-date">{_esc(session.get("date", ""))}</span>'
        f'<span class="tf-session-goal">{_esc(session.get("goal", ""))} {owner_html}</span></div>'
        f"{notes_html}<div style=\"margin-top:8px\">{lines}</div></div>"
    )


def empty_state(title: str, message: str) -> str:
    return (
        f'<div class="tf-empty"><div class="tf-empty-title">{_esc(title)}</div>'
        f"<div>{_esc(message)}</div></div>"
    )
