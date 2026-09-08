"""Shared helpers for all result components: icons, colors, dates."""
from datetime import datetime
from typing import Optional, Tuple


# ──────────────────────────────────────────────────────────────────────────────
# Icons — Material Symbols (font loaded once in streamlit_app.py).
# One consistent set everywhere instead of a mix of emoji.
# ──────────────────────────────────────────────────────────────────────────────

def icon(name: str, size: int = 20, color: str = "inherit") -> str:
    """Inline Material Symbols span. Use inside st.markdown(unsafe_allow_html=True)."""
    return (
        f'<span class="ms-icon" style="font-size:{size}px; color:{color};">{name}</span>'
    )


def icon_text(name: str, text: str, size: int = 20, color: str = "inherit") -> str:
    """Icon + label on one line, vertically aligned."""
    return (
        f'<span class="ms-icon-text" style="color:{color};">'
        f'{icon(name, size, "currentColor")}{text}</span>'
    )


# ──────────────────────────────────────────────────────────────────────────────
# Score colors — semantic values, shared by charts, cards and badges.
# ──────────────────────────────────────────────────────────────────────────────

SCORE_GREEN = "#10B981"
SCORE_AMBER = "#F59E0B"
SCORE_RED = "#EF4444"

def score_hex(score: float) -> str:
    """Hex color for a 0–100 score. Used by Plotly charts and inline HTML."""
    if score >= 80:
        return SCORE_GREEN
    if score >= 60:
        return SCORE_AMBER
    return SCORE_RED


def get_score_color(score: float) -> Tuple[str, str]:
    """(text_color, background_color) for a 0–100 score — used by cards."""
    if score >= 80:
        return "var(--success-text)", "var(--success-soft)"
    if score >= 60:
        return "var(--warning-text)", "var(--warning-soft)"
    return "var(--danger-text)", "var(--danger-soft)"


def get_score_icon(score: float) -> str:
    """Material Symbols icon name for the score band."""
    if score >= 90:
        return "workspace_premium"
    if score >= 80:
        return "check_circle"
    if score >= 70:
        return "thumb_up"
    if score >= 60:
        return "warning"
    return "error"


def get_severity_style(severity: str) -> Tuple[str, str, str]:
    """
    (material_symbol_name, text_color, background_color) for an IssueDetail
    severity. Matches the values the backend emits in
    `detailed_feedback[].severity_level`.
    """
    level = (severity or "").lower()
    if level in ("critical", "high"):
        return "error", "var(--danger-text)", "var(--danger-soft)"
    if level in ("medium", "moderate"):
        return "warning", "var(--warning-text)", "var(--warning-soft)"
    return "check_circle", "var(--success-text)", "var(--success-soft)"


# ──────────────────────────────────────────────────────────────────────────────
# Dates — human formatting instead of raw ISO strings.
# ──────────────────────────────────────────────────────────────────────────────

def format_ts(iso: Optional[str], fmt: str = "%b %d, %I:%M %p") -> str:
    """'2026-09-08T12:00:00+00:00' → 'Sep 08, 12:00 PM'. Falls back to input."""
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return dt.strftime(fmt)
    except (ValueError, TypeError):
        return str(iso)


# Axis/label color for Plotly charts on the light background.
CHART_TEXT_COLOR = "#374151"
