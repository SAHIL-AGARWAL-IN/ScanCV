from typing import Any, Dict, Optional

import streamlit as st

from frontend.components._helpers import icon


def _chips(keywords: list, variant: str, sym: str, empty_text: str, badge_prefix: str = "") -> None:
    if not keywords:
        st.markdown(f"<span class='chip chip-plain'>{empty_text}</span>", unsafe_allow_html=True)
        return
    chips = "".join(
        f'<span class="chip chip-{variant}">{icon(sym, 15)}{badge_prefix}{kw}</span>' for kw in keywords
    )
    st.markdown(f'<div class="chip-row">{chips}</div>', unsafe_allow_html=True)


def display_jd_comparison(jd_comparison: Optional[Dict[str, Any]]) -> None:
    if not jd_comparison:
        return

    st.markdown(
        f'<div class="section-header">{icon("track_changes", 24)}🎯 Job Description Alignment</div>',
        unsafe_allow_html=True,
    )

    match_pct = float(jd_comparison.get("match_percentage", 0))
    semantic = float(jd_comparison.get("semantic_similarity", 0))
    matched = jd_comparison.get("matched_keywords", []) or []
    missing = jd_comparison.get("missing_keywords", []) or []
    gap = jd_comparison.get("skills_gap", []) or []

    # Match rating status badge
    if match_pct >= 75:
        match_label = "🟢 Strong Match — Well aligned with job requirements"
        bar_color = "#10B981"
    elif match_pct >= 50:
        match_label = "🟡 Moderate Match — Consider adding critical missing keywords"
        bar_color = "#F59E0B"
    else:
        match_label = "🔴 Low Match — Resume is missing several core required skills"
        bar_color = "#EF4444"

    st.markdown(
        f"""
        <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:12px; padding:16px; margin-bottom:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-weight:600; font-size:1.05rem; color:#1E293B;">Keyword & Qualification Coverage</span>
                <span style="font-size:0.95rem; font-weight:700; color:{bar_color};">{match_pct:.0f}%</span>
            </div>
            <div style="background:#E2E8F0; border-radius:9999px; height:10px; overflow:hidden; margin-bottom:10px;">
                <div style="background:{bar_color}; width:{min(100.0, max(0.0, match_pct))}%; height:100%; border-radius:9999px; transition:width 0.4s ease;"></div>
            </div>
            <div style="font-size:0.88rem; color:#475569;">{match_label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    top_l, top_r = st.columns(2)
    with top_l:
        st.metric("Direct Keyword Match", f"{match_pct:.0f}%", help="Exact & fuzzy keyword matches against JD")
    with top_r:
        st.metric("Semantic Context Similarity", f"{semantic * 100:.0f}%", help="Deep semantic embedding similarity between your resume and the JD")

    st.markdown("---")

    st.markdown(
        f'<div class="section-header" style="font-size:1.05rem;">{icon("verified", 20)} Matched Keywords ({len(matched)})</div>',
        unsafe_allow_html=True,
    )
    _chips(matched[:20], "good", "check", "No keywords matched yet")

    col_missing, col_gap = st.columns(2)
    with col_missing:
        st.markdown(
            f'<div class="section-header" style="font-size:1.05rem;">{icon("add_circle", 20)} Missing Keywords to Add ({len(missing)})</div>',
            unsafe_allow_html=True,
        )
        st.caption("Consider adding these terms to your experience or skills section:")
        _chips(missing[:15], "bad", "priority_high", "All key JD terms are present in your resume!")

    with col_gap:
        st.markdown(
            f'<div class="section-header" style="font-size:1.05rem;">{icon("psychology", 20)} High-Priority Skills Gap ({len(gap)})</div>',
            unsafe_allow_html=True,
        )
        st.caption("Skills explicitly requested in the JD that were not found:")
        _chips(gap[:12], "info", "bolt", "No critical skills gap detected!")
