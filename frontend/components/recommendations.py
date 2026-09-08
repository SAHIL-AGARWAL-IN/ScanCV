from typing import Any, Dict

import streamlit as st

from frontend.components._helpers import icon


def display_recommendations(analysis: Dict[str, Any]) -> None:
    suggestions = analysis.get("suggestions") or []
    if not suggestions:
        return

    st.markdown(
        f'<div class="section-header">{icon("lightbulb", 22)}Recommendations</div>',
        unsafe_allow_html=True,
    )
    for suggestion in suggestions:
        st.markdown(
            f'<div class="action-item">{icon("tips_and_updates", 18, "var(--info-text)")}<span>{suggestion}</span></div>',
            unsafe_allow_html=True,
        )
