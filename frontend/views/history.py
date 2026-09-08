from datetime import datetime
from typing import Any, Dict, List

import plotly.graph_objects as go
import requests
import streamlit as st

from frontend.components._helpers import (
    CHART_TEXT_COLOR,
    format_ts,
    get_score_icon,
    icon,
    score_hex,
)
from frontend.services import api_client


def _show_backend_error(exc: Exception) -> None:
    if isinstance(exc, requests.ConnectionError):
        st.error("Could not reach the backend. Is it running on port 8000?")
    elif isinstance(exc, requests.HTTPError) and exc.response is not None:
        st.error(f"Backend returned {exc.response.status_code}: {exc.response.text}")
    else:
        st.error(f"Unexpected error: {exc}")


def _sorted_entries(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Oldest → newest, so the trend line reads left-to-right."""
    def key(entry):
        try:
            return datetime.fromisoformat(
                str(entry.get("created_at", "")).replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            return datetime.min

    return sorted(history, key=key)


def _render_stat_strip(history: List[Dict[str, Any]]) -> None:
    scores = [float(e.get("ats_score", 0) or 0) for e in history]
    items = [
        (len(history), "Total analyses"),
        (f"{max(scores):.0f}", "Best score"),
        (f"{sum(scores) / len(scores):.0f}", "Average"),
        (format_ts(history[0].get("created_at"), "%b %d"), "Most recent"),
    ]
    cells = "".join(
        f'<div class="stat-strip-item"><span class="stat-strip-value">{v}</span>'
        f'<span class="stat-strip-label">{label}</span></div>'
        for v, label in items
    )
    st.markdown(f'<div class="stat-strip">{cells}</div>', unsafe_allow_html=True)


def _render_trend(entries: List[Dict[str, Any]]) -> None:
    """Score-over-time line. Only meaningful with 2+ points."""
    if len(entries) < 2:
        return

    x = [e.get("created_at", "") for e in entries]
    y = [float(e.get("ats_score", 0) or 0) for e in entries]
    labels = [
        f"{format_ts(e.get('created_at'))}<br>{e.get('filename', 'resume')} — {s:.0f}/100"
        for e, s in zip(entries, y)
    ]
    text_color = CHART_TEXT_COLOR

    fig = go.Figure(
        go.Scatter(
            x=x,
            y=y,
            mode="lines+markers",
            text=labels,
            hoverinfo="text",
            line=dict(color="#2563EB", width=3, shape="spline", smoothing=0.6),
            marker=dict(
                size=9,
                color=[score_hex(s) for s in y],
                line=dict(width=2, color="#FFFFFF"),
            ),
        )
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=220,
        yaxis=dict(range=[0, 105], gridcolor=_grid_color(text_color)),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=text_color),
    )
    fig.update_xaxes(showgrid=False)
    st.plotly_chart(fig, use_container_width=True, key="history_trend")


def _grid_color(text_color: str) -> str:
    """Faint gridline color from the theme text color."""
    r, g, b = (int(text_color[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},0.15)"


def _render_card(idx: int, entry: Dict[str, Any]) -> None:
    filename = entry.get("filename", "resume")
    ats_score = float(entry.get("ats_score", 0) or 0)
    created_at = entry.get("created_at", "")
    analysis = entry.get("analysis_result", {}) or {}

    component_scores = analysis.get("component_scores", {}) or {}
    jd_comparison = analysis.get("jd_comparison") or analysis.get("jd_match_analysis")

    st.markdown(
        f"""
        <div class="history-card">
            <div class="history-card-header">
                <div>
                    <span class="history-card-title">
                        {icon("description", 20)}{filename}
                    </span><br>
                    <span class="history-meta">
                        {icon("schedule", 14)}{format_ts(created_at)}
                        &nbsp;·&nbsp;
                        {icon("track_changes", 14)}{"JD match" if jd_comparison else "General analysis"}
                    </span>
                </div>
                <span class="score-badge" style="color:{score_hex(ats_score)}; background:{_grid_color(score_hex(ats_score))};">
                    {icon(get_score_icon(ats_score), 18)}{ats_score:.0f}/100
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Details", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Formatting", f"{component_scores.get('formatting', 0):.0f}/20")
            st.metric("Keywords", f"{component_scores.get('keywords', 0):.0f}/25")
        with c2:
            st.metric("Content", f"{component_scores.get('content', 0):.0f}/25")
            st.metric("Skill Validation", f"{component_scores.get('skill_validation', 0):.0f}/15")
        with c3:
            st.metric("ATS Compatibility", f"{component_scores.get('ats_compatibility', 0):.0f}/15")
            if jd_comparison:
                st.metric("JD Match", f"{jd_comparison.get('match_percentage', 0):.0f}%")

        entry_id = entry.get("id")
        if entry_id:
            if st.button("Delete this entry", key=f"delete_{idx}", icon=":material/delete:"):
                try:
                    api_client.delete_history_entry(str(entry_id), access_token=st.session_state["access_token"])
                    st.toast("Analysis deleted", icon=":material/delete:")
                    st.rerun()
                except requests.RequestException as exc:
                    _show_backend_error(exc)


def render() -> None:
    st.title("Analysis History")
    st.markdown("Past analyses saved against your account.")

    access_token = st.session_state.get("access_token")
    if not access_token:
        st.warning("Sign in from the sidebar to view your history.")
        return

    try:
        history = api_client.get_history(access_token)
    except requests.RequestException as exc:
        _show_backend_error(exc)
        return

    if not history:
        st.info("No analyses yet for this account. Run a scoring on the ATS Scorer page first.")
        if st.button("Go to ATS Scorer", icon=":material/rocket_launch:"):
            st.session_state.current_view = "scorer"
            st.rerun()
        return

    # history comes newest-first from the API; the trend wants oldest-first.
    chronological = _sorted_entries(history)

    _render_stat_strip(history)

    st.markdown(
        f'<div class="section-header">{icon("query_stats", 22)}Score Trend</div>',
        unsafe_allow_html=True,
    )
    _render_trend(chronological)

    st.markdown(
        f'<div class="section-header">{icon("history", 22)}'
        f"All Analyses ({len(history)})</div>",
        unsafe_allow_html=True,
    )
    for idx, entry in enumerate(history):
        _render_card(idx, entry)
