from typing import Any, Dict

import streamlit as st

from frontend.components._helpers import icon


def display_skill_validation(analysis: Dict[str, Any]) -> None:
    details = analysis.get("skill_validation_details") or {}
    validated = details.get("validated", [])
    unvalidated = details.get("unvalidated", [])
    total = details.get("total", len(validated) + len(unvalidated))
    pct = details.get("validation_pct", 0.0)

    st.markdown(
        f'<div class="section-header">{icon("verified", 22)}Skill Validation</div>',
        unsafe_allow_html=True,
    )
    st.caption("Skills listed on the resume that are actually backed by a project or experience bullet.")

    if total == 0:
        st.info("No skills detected on the resume.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Skills", total)
    c2.metric("Validated", len(validated))
    c3.metric("Validation %", f"{pct:.0f}%")

    st.progress(min(max(pct / 100.0, 0.0), 1.0))

    if validated:
        with st.expander(f"Validated skills ({len(validated)})", expanded=True):
            for entry in validated:
                skill = entry.get("skill", "?")
                projects = entry.get("projects", []) or []
                similarity = entry.get("similarity")

                project_text = ", ".join(projects[:3]) if projects else "experience section"
                sim_text = f" ({similarity * 100:.0f}% match)" if isinstance(similarity, (int, float)) else ""
                st.markdown(
                    f"""
                    <div class="skill-row">
                        {icon("check_circle", 18, "var(--success-text)")}
                        <span><strong>{skill}</strong></span>
                        <span class="skill-row-sim">{sim_text} — demonstrated in: {project_text}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    if unvalidated:
        with st.expander(f"Unvalidated skills ({len(unvalidated)})", expanded=False):
            st.caption("These skills are listed but not tied to a project or experience bullet.")
            for skill in unvalidated:
                st.markdown(
                    f"""
                    <div class="skill-row">
                        {icon("cancel", 18, "var(--danger-text)")}
                        <span>{skill}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
