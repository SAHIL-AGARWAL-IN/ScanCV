from typing import Any, Dict, Optional

import streamlit as st

from frontend.components._helpers import icon


def _chips(keywords: list, variant: str, sym: str, empty_text: str) -> None:
    if not keywords:
        st.markdown(f"<span class='chip chip-plain'>{empty_text}</span>", unsafe_allow_html=True)
        return
    chips = "".join(
        f'<span class="chip chip-{variant}">{icon(sym, 15)}{kw}</span>' for kw in keywords
    )
    st.markdown(f'<div class="chip-row">{chips}</div>', unsafe_allow_html=True)


def display_jd_comparison(jd_comparison: Optional[Dict[str, Any]]) -> None:
    if not jd_comparison:
        return  # caller decides whether to render the section at all

    st.markdown(
        f'<div class="section-header">{icon("track_changes", 22)}Job Description Match</div>',
        unsafe_allow_html=True,
    )

    match_pct = float(jd_comparison.get("match_percentage", 0))
    semantic = float(jd_comparison.get("semantic_similarity", 0))
    matched = jd_comparison.get("matched_keywords", []) or []
    missing = jd_comparison.get("missing_keywords", []) or []
    gap = jd_comparison.get("skills_gap", []) or []

    top_l, top_r = st.columns(2)
    with top_l:
        st.metric("Match Percentage", f"{match_pct:.0f}%")
        st.progress(min(max(match_pct / 100.0, 0.0), 1.0))
    with top_r:
        st.metric("Semantic Similarity", f"{semantic * 100:.0f}%")
        st.progress(min(max(semantic, 0.0), 1.0))

    st.markdown(
        f'<div class="section-header" style="font-size:1.05rem;">{icon("join_inner", 20)}Matched keywords</div>',
        unsafe_allow_html=True,
    )
    _chips(matched[:15], "good", "check", "None matched yet")

    col_missing, col_gap = st.columns(2)
    with col_missing:
        st.markdown(
            f'<div class="section-header" style="font-size:1.05rem;">{icon("search_off", 20)}Missing keywords</div>',
            unsafe_allow_html=True,
        )
        _chips(missing[:10], "bad", "close", "All key terms are present!")

    with col_gap:
        st.markdown(
            f'<div class="section-header" style="font-size:1.05rem;">{icon("query_stats", 20)}Skills gap</div>',
            unsafe_allow_html=True,
        )
        _chips(gap[:10], "info", "arrow_outward", "No significant skills gap detected")
