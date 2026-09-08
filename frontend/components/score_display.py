from typing import Any, Dict

import plotly.graph_objects as go
import streamlit as st

from frontend.components._helpers import (
    CHART_TEXT_COLOR,
    get_score_color,
    get_score_icon,
    icon,
    score_hex,
)


# Component max scores match backend/core/config.py SCORE_WEIGHTS.
# (Backend returns each component's score on its own scale, not 0–100.)
COMPONENTS = [
    ("Formatting",        "formatting",        20, "edit_note"),
    ("Keywords & Skills", "keywords",          25, "key"),
    ("Content Quality",   "content",           25, "description"),
    ("Skill Validation",  "skill_validation",  15, "verified"),
    ("ATS Compatibility", "ats_compatibility", 15, "smart_toy"),
]


def _gauge_figure(score: float) -> go.Figure:
    """Radial gauge for the overall ATS score."""
    color = score_hex(score)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"font": {"size": 64, "color": color}, "suffix": ""},
        gauge={
            "axis": {
                "range": [0, 100],
                "tickwidth": 1,
                "tickcolor": CHART_TEXT_COLOR,
                "tickfont": {"size": 12, "color": CHART_TEXT_COLOR},
            },
            "bar": {"color": color, "thickness": 0.28},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 60], "color": "rgba(239,68,68,0.10)"},
                {"range": [60, 80], "color": "rgba(245,158,11,0.10)"},
                {"range": [80, 100], "color": "rgba(16,185,129,0.10)"},
            ],
            "threshold": {
                "line": {"color": color, "width": 3},
                "thickness": 0.9,
                "value": score,
            },
        },
    ))
    fig.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _radar_figure(component_scores: Dict[str, Any]) -> go.Figure:
    """Radar chart of the five component scores, as % of their max."""
    labels = [c[0] for c in COMPONENTS]
    pcts = []
    for _label, key, max_score, _i in COMPONENTS:
        value = float(component_scores.get(key, 0) or 0)
        pcts.append(round(value / max_score * 100) if max_score else 0)

    fig = go.Figure(go.Scatterpolar(
        r=pcts + [pcts[0]],          # close the polygon
        theta=labels + [labels[0]],
        fill="toself",
        fillcolor="rgba(79,70,229,0.18)",
        line=dict(color="#4F46E5", width=2.5),
        marker=dict(size=5, color="#4F46E5"),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True, range=[0, 100],
                tickfont=dict(size=10, color=CHART_TEXT_COLOR),
                gridcolor="rgba(128,128,128,0.25)",
            ),
            angularaxis=dict(
                tickfont=dict(size=12, color=CHART_TEXT_COLOR),
                gridcolor="rgba(128,128,128,0.25)",
                linecolor="rgba(128,128,128,0.35)",
            ),
        ),
        height=340,
        margin=dict(l=70, r=70, t=30, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


def display_overall_score(analysis: Dict[str, Any]) -> None:
    """Gauge + interpretation side by side in one hero card."""
    score = float(analysis.get("ATS_score", analysis.get("ats_score", 0)))
    interpretation = analysis.get("interpretation", "")
    text_color, _bg = get_score_color(score)
    score_icon = get_score_icon(score)

    left, right = st.columns([1, 1.4])
    with left:
        st.plotly_chart(
            _gauge_figure(score),
            use_container_width=True,
            key="gauge_overall",
        )
    with right:
        st.markdown(
            f"""
            <div style="padding:0.5rem 0.25rem;">
                <div class="score-hero-kicker">Overall ATS Score</div>
                <div class="ms-icon-text" style="color:{text_color}; font-size:1.15rem;">
                    {icon(score_icon, 24, 'currentColor')}{interpretation or 'Analysis complete'}
                </div>
                <p class="score-hero-interpretation" style="margin-top:0.75rem;">
                    Scores above 80 clear most ATS filters. Below 60, focus on the
                    critical issues listed in the next tab first.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def display_score_breakdown(analysis: Dict[str, Any]) -> None:
    """Radar chart + labeled bars for the five scoring components."""
    component_scores = analysis.get("component_scores") or {}

    st.markdown(
        f'<div class="section-header">{icon("insights", 22)}Score Breakdown</div>',
        unsafe_allow_html=True,
    )

    chart, bars = st.columns([1, 1])
    with chart:
        st.plotly_chart(
            _radar_figure(component_scores),
            use_container_width=True,
            key="radar_components",
        )
    with bars:
        for label, key, max_score, sym in COMPONENTS:
            value = float(component_scores.get(key, 0) or 0)
            percentage = value / max_score if max_score else 0
            bar_color = score_hex(percentage * 100)

            st.markdown(
                f"""
                <div class="component-bar-row">
                    <div class="component-bar-top">
                        <span class="component-bar-label">{icon(sym, 18)}{label}</span>
                        <span class="component-bar-value">{value:.0f}/{max_score}</span>
                    </div>
                    <div class="component-bar-track">
                        <div class="component-bar-fill" style="width:{percentage * 100:.0f}%; background-color:{bar_color};"></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
