from typing import Any, Dict, List

import streamlit as st

from frontend.components._helpers import icon


def display_strengths(strengths: List[str]) -> None:
    st.markdown(
        f'<div class="section-header">{icon("workspace_premium", 22)}Strengths</div>',
        unsafe_allow_html=True,
    )
    if not strengths:
        st.info("Keep improving your resume to unlock strengths!")
        return
    for item in strengths:
        st.markdown(
            f'<div class="action-item">{icon("check_circle", 18, "var(--success-text)")}<span>{item}</span></div>',
            unsafe_allow_html=True,
        )


def display_critical_issues(analysis: Dict[str, Any]) -> None:
    critical = analysis.get("critical_issues") or []
    summary = analysis.get("issues_summary") or []

    st.markdown(
        f'<div class="section-header">{icon("report", 22)}Critical Issues</div>',
        unsafe_allow_html=True,
    )

    if not critical and not summary:
        st.success("No critical issues found — your resume has no urgent problems. Nice work.")
        return

    if critical:
        st.error("These issues should be addressed first for better ATS performance.")
        for item in critical:
            st.markdown(
                f'<div class="action-item">{icon("error", 18, "var(--danger-text)")}<span>{item}</span></div>',
                unsafe_allow_html=True,
            )

    extra = [s for s in summary if s not in critical]
    if extra:
        with st.expander("Additional flagged items", expanded=False):
            for item in extra:
                st.markdown(
                    f'<div class="action-item">{icon("flag", 18, "var(--warning-text)")}<span>{item}</span></div>',
                    unsafe_allow_html=True,
                )
