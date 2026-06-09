import ui_styles as ui


def test_badge_contains_text_and_class():
    out = ui.badge("chest", "muscle")
    assert "chest" in out
    assert "tf-badge" in out and "muscle" in out


def test_badge_escapes_html():
    out = ui.badge("<script>alert(1)</script>")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_badges_joins_multiple():
    out = ui.badges(["chest", "back"], "muscle")
    assert out.count("tf-badge") == 2


def test_metric_card_renders_label_value_sub():
    out = ui.metric_card("Exercises", 16, "in catalog", accent=True)
    assert "Exercises" in out and "16" in out and "in catalog" in out
    assert "accent" in out


def test_metric_chip_card_shows_chips_and_more():
    out = ui.metric_chip_card("Recent focus", ["chest", "back"], more=2, sub="from history")
    assert "chest" in out and "back" in out
    assert "+2 more" in out
    assert "tf-metric" in out  # same card shell -> consistent height


def test_metric_chip_card_empty_shows_dash():
    out = ui.metric_chip_card("Recent focus", [], more=0)
    assert "—" in out


def test_hero_center_adds_class():
    assert "tf-hero-center" in ui.hero("T", "tag", center=True)
    assert "tf-hero-center" not in ui.hero("T", "tag")


def test_styles_hide_sidebar_radio_dots():
    css = ui.styles()
    # The radio circle (first child of each option label) is hidden.
    assert 'div[role="radiogroup"] > label > div:first-child' in css
    assert "display: none" in css


def test_styles_have_global_button_rules_and_readable_primary():
    css = ui.styles()
    # Global button selectors (not just one button).
    assert ".stButton > button" in css
    assert ".stDownloadButton > button" in css
    assert ".stFormSubmitButton > button" in css
    # Primary CTA uses dark text on green — no white-on-light-green.
    assert "#06231b" in css  # dark text for primary buttons
    assert "color: #ffffff !important" not in css  # never force white on the green CTA


def test_provider_label_mapping():
    assert ui.provider_label("gemini") == "Gemini"
    assert ui.provider_label("anthropic") == "Anthropic"
    assert ui.provider_label("fallback") == "Built-in planner"
    assert ui.provider_label("something-odd") == "Unknown"


def test_provider_badge_contains_label():
    assert "Gemini" in ui.provider_badge("gemini")


def test_exercise_card_has_name_and_badges():
    ex = {"name": "Bench Press", "primary_muscles": ["chest"],
          "equipment": "barbell", "difficulty": "intermediate"}
    out = ui.exercise_card(ex)
    assert "Bench Press" in out
    assert "chest" in out and "barbell" in out and "intermediate" in out


def test_plan_item_card_shows_meta_and_reason():
    item = {"exercise_id": 1, "exercise_name": "Squat", "sets": 4,
            "reps": "8-12", "rest_seconds": 90, "rationale": "main lift"}
    out = ui.plan_item_card(item)
    assert "Squat" in out
    assert "4 sets" in out and "8-12 reps" in out and "90s" in out
    assert "main lift" in out


def test_plan_item_card_enriches_from_catalog():
    item = {"exercise_id": 1, "exercise_name": "Squat", "sets": 4, "reps": "5", "rest_seconds": 120}
    catalog = {1: {"primary_muscles": ["quadriceps"], "equipment": "barbell"}}
    out = ui.plan_item_card(item, catalog)
    assert "quadriceps" in out and "barbell" in out


def test_plan_day_card_lists_items():
    out = ui.plan_day_card(2, "Push", [
        {"exercise_id": 1, "exercise_name": "Bench", "sets": 4, "reps": "8", "rest_seconds": 90},
    ])
    assert "DAY 2" in out and "Push" in out and "Bench" in out


def test_session_card_and_empty_state():
    s = {"date": "2026-06-07", "goal": "hypertrophy", "owner": "alice", "notes": "good"}
    card = ui.session_card(s, ["Bench — 4×8"], show_owner=True)
    assert "2026-06-07" in card and "hypertrophy" in card and "Bench" in card and "alice" in card

    empty = ui.empty_state("Nothing here", "Add something")
    assert "Nothing here" in empty and "Add something" in empty
