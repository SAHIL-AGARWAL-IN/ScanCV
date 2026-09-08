from typing import Any, Dict

import streamlit as st

from frontend.components.score_display import display_overall_score, display_score_breakdown
from frontend.components.strengths_issues import display_strengths, display_critical_issues
from frontend.components.skill_validation import display_skill_validation
from frontend.components.jd_comparison import display_jd_comparison
from frontend.components.detailed_feedback import display_detailed_feedback
from frontend.components.action_items import display_action_items
from frontend.components.recommendations import display_recommendations


def display_results_dashboard(analysis: Dict[str, Any]) -> None:
    """
    Render the full results page from one backend response dict.

    Layout: score hero + breakdown on top, then tabs for the detail sections
    so the most important information (score, then action items) is visible
    without scrolling through everything.
    """
    display_overall_score(analysis)
    display_score_breakdown(analysis)

    jd_comparison = analysis.get("jd_comparison") or analysis.get("jd_match_analysis")

    tab_actions, tab_feedback, tab_skills, tab_jd = st.tabs([
        "Action Items",
        "Issues & Feedback",
        "Skill Validation",
        "JD Match" if jd_comparison else "JD Match — none submitted",
    ])

    with tab_actions:
        # Most actionable content first: strengths, then prioritized steps.
        display_strengths(analysis.get("strengths") or [])
        display_action_items(analysis)
        display_recommendations(analysis)

    with tab_feedback:
        display_critical_issues(analysis)
        display_detailed_feedback(analysis)

    with tab_skills:
        display_skill_validation(analysis)

    with tab_jd:
        if jd_comparison:
            display_jd_comparison(jd_comparison)
        else:
            st.info(
                "No job description was submitted for this analysis. "
                "Switch to 'Job Description Comparison' mode and paste a JD "
                "to see keyword matching here."
            )
