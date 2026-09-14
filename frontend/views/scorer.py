from typing import Optional
import threading

import requests
import streamlit as st

from frontend.services import api_client
from frontend.components.dashboard import display_results_dashboard


def _read_jd(jd_file, jd_text: str) -> str:
    """
    Turn whatever the user provided into a plain JD string for the backend.

    For .txt files we decode in-process — that's a trivial operation, no need
    for a backend round-trip. For PDF/DOCX, we'd need the backend's parser;
    we don't have a public endpoint for that, so we ask the user to paste text
    instead for non-txt JDs.
    """
    if jd_text:
        return jd_text.strip()
    if jd_file is None:
        return ""
    if jd_file.name.lower().endswith(".txt"):
        return jd_file.getvalue().decode("utf-8", errors="ignore")
    st.warning(
        "Job description files must be `.txt` for now — paste the JD text instead "
        "if you have a PDF or DOCX."
    )
    return ""


def _analyze_with_progress(resume_file, access_token: str, job_description: str) -> dict:
    """
    Run the analyze request while showing staged status + an eased progress bar.

    The HTTP call runs in a worker thread; the main thread animates a progress
    bar that decelerates toward 90% (so it never looks stuck, and never
    finishes early). Only the worker touches the network, only the main
    thread touches Streamlit elements.
    """
    import time

    STAGES = [
        (0,  "Uploading resume to backend…"),
        (6,  "Extracting text and structure from your file…"),
        (14, "Parsing skills, projects and experience (Groq LLM)…"),
        (26, "Scoring against ATS criteria…"),
        (40, "Validating skills against project evidence…"),
    ]

    result: dict = {}
    error: Optional[requests.RequestException] = None

    def _worker():
        nonlocal result, error
        try:
            result = api_client.analyze_resume(
                resume_file=resume_file,
                access_token=access_token,
                job_description=job_description,
            )
        except requests.RequestException as exc:
            error = exc

    status = st.status("Analyzing your resume…", expanded=True)
    stage_text = st.empty()
    progress = st.progress(0, text="")

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

    start = time.time()
    while thread.is_alive():
        elapsed = time.time() - start
        # Ease-out curve: fast start, decelerates, asymptotes at 90%.
        pct = min(90.0, 90.0 * (1 - (1 / (1 + elapsed / 8.0))))
        progress.progress(int(pct), text=f"{elapsed:.0f}s elapsed")
        for at, label in STAGES:
            if elapsed >= at:
                stage_text.markdown(f":gray[{label}]")
        time.sleep(0.25)

    thread.join()

    if error is not None:
        status.update(label="Analysis failed", state="error", expanded=True)
        raise error

    progress.progress(100, text="Done")
    status.update(
        label=f"Analysis complete in {time.time() - start:.0f}s",
        state="complete",
        expanded=False,
    )
    return result


def _show_backend_error(exc: Exception) -> None:
    """Translate a `requests` exception into a friendly Streamlit error."""
    if isinstance(exc, requests.ConnectionError):
        st.error("Could not reach the backend. Is `uvicorn backend.main:app` running on port 8000?")
    elif isinstance(exc, requests.Timeout):
        st.error("The backend took too long to respond. Try a smaller resume or check the server logs.")
    elif isinstance(exc, requests.HTTPError) and exc.response is not None:
        try:
            detail = exc.response.json().get("detail", exc.response.text)
        except ValueError:
            detail = exc.response.text
        st.error(f"Backend returned {exc.response.status_code}: {detail}")
    else:
        st.error(f"Unexpected error: {exc}")


def _summary_text(analysis: dict) -> str:
    """Tiny client-side text summary for the Download button."""
    score = analysis.get("ATS_score", analysis.get("ats_score", 0))
    lines = [f"ATS Score: {score:.0f}/100", ""]

    cs = analysis.get("component_scores") or {}
    if cs:
        lines.append("COMPONENT BREAKDOWN:")
        for label, key in [
            ("Formatting", "formatting"),
            ("Keywords", "keywords"),
            ("Content", "content"),
            ("Skill Validation", "skill_validation"),
            ("ATS Compatibility", "ats_compatibility"),
        ]:
            if key in cs:
                lines.append(f"  - {label}: {cs[key]}")
        lines.append("")

    if analysis.get("interpretation"):
        lines.append(analysis["interpretation"])
        lines.append("")

    if analysis.get("strengths"):
        lines.append("STRENGTHS:")
        lines.extend(f"  - {s}" for s in analysis["strengths"])
        lines.append("")

    if analysis.get("critical_issues"):
        lines.append("CRITICAL ISSUES:")
        lines.extend(f"  - {s}" for s in analysis["critical_issues"])
        lines.append("")

    if analysis.get("suggestions"):
        lines.append("SUGGESTIONS:")
        lines.extend(f"  - {s}" for s in analysis["suggestions"])
        lines.append("")

    missing = analysis.get("missing_keywords") or []
    if missing:
        lines.append("MISSING KEYWORDS:")
        lines.extend(f"  - {k}" for k in missing[:15])
        lines.append("")

    return "\n".join(lines)


class MockUploadedFile:
    def __init__(self, name: str, data: bytes, content_type: str = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
        self.name = name
        self._data = data
        self.type = content_type
        self.size = len(data)

    def getvalue(self) -> bytes:
        return self._data


def _render_upload_area(analysis_mode: str):
    """Two-column upload widgets. Returns (resume_file, jd_file, jd_text)."""
    from pathlib import Path
    left, right = st.columns(2)

    with left:
        st.markdown("### 📄 Upload Resume")
        resume_file = st.file_uploader(
            "Choose your resume file",
            type=["pdf", "doc", "docx"],
            help="Supported: PDF, DOC, DOCX (max 5 MB)",
            key="resume_upload",
        )
        if resume_file:
            st.session_state.pop("sample_resume", None)
            st.success(f"✅ {resume_file.name} ({resume_file.size / 1024:.1f} KB)")
        elif st.session_state.get("sample_resume"):
            resume_file = st.session_state["sample_resume"]
            st.success(f"✅ Active Sample: {resume_file.name} ({resume_file.size / 1024:.1f} KB)")
            if st.button("✕ Clear Sample Resume", key="clear_sample"):
                st.session_state.pop("sample_resume", None)
                st.rerun()
        else:
            st.caption("Don't have a resume handy? Try a pre-loaded profile:")
            if st.button("✨ Load Sample Resume: Senior SWE", key="load_sample_swe", use_container_width=True):
                sample_path = Path(__file__).resolve().parents[1] / "assets" / "samples" / "sample_swe_resume.docx"
                if sample_path.exists():
                    with open(sample_path, "rb") as f:
                        st.session_state["sample_resume"] = MockUploadedFile("sample_swe_resume.docx", f.read())
                    st.rerun()

    jd_file: Optional[object] = None
    jd_text = ""

    with right:
        if analysis_mode == "Job Description Comparison":
            st.markdown("### 📋 Job Description")
            jd_method = st.radio(
                "Input method:",
                ["📝 Paste Text", "🌐 Import from URL", "📁 Upload .txt File"],
                horizontal=True,
                key="jd_input_method",
            )
            if jd_method == "📁 Upload .txt File":
                jd_file = st.file_uploader(
                    "Choose JD file (.txt only)",
                    type=["txt"],
                    key="jd_upload",
                )
                if jd_file:
                    st.success(f"✅ {jd_file.name}")
            elif jd_method == "🌐 Import from URL":
                st.caption("Paste a link from LinkedIn, Indeed, Greenhouse, Lever, or any company career page:")
                url_col, btn_col = st.columns([3, 1])
                with url_col:
                    jd_url = st.text_input(
                        "Job Posting URL:",
                        placeholder="https://company.com/careers/... or job board link",
                        label_visibility="collapsed",
                        key="jd_url_input",
                    )
                with btn_col:
                    fetch_btn = st.button("📥 Fetch JD", use_container_width=True)

                if fetch_btn and jd_url.strip():
                    try:
                        with st.spinner("Fetching and extracting job requirements with AI..."):
                            data = api_client.extract_jd_from_url(
                                jd_url.strip(),
                                access_token=st.session_state.get("access_token"),
                            )
                            st.session_state["extracted_jd_content"] = data.get("job_description", "")
                            st.session_state["extracted_jd_title"] = data.get("title", "Job Posting")
                            st.success(f"✅ Extracted: {st.session_state['extracted_jd_title']}")
                    except Exception as exc:
                        _show_backend_error(exc)

                current_extracted = st.session_state.get("extracted_jd_content", "")
                jd_text = st.text_area(
                    "Job Description (editable):",
                    value=current_extracted,
                    height=200,
                    placeholder="Job description will appear here after fetching...",
                    key="jd_text_from_url",
                )
                if jd_text:
                    st.success(f"✅ {len(jd_text)} characters loaded")
            else:
                jd_text = st.text_area(
                    "Paste job description text:",
                    height=200,
                    placeholder="Paste the JD here...",
                    key="jd_text",
                )
                if jd_text:
                    st.success(f"✅ {len(jd_text)} characters")
        else:
            st.markdown("### 📋 Job Description")
            st.info("Switch to 'Job Description Comparison' mode to enable JD matching.")

    return resume_file, jd_file, jd_text


def _render_export_buttons(analysis: dict) -> None:
    st.markdown("### 📥 Export Results")
    c1, c2 = st.columns(2)

    with c1:
        # Lazy: only call the backend the first time the user clicks expand.
        if st.button("📑 Generate PDF Report", use_container_width=True, type="primary"):
            try:
                with st.spinner("Generating PDF on backend..."):
                    pdf_bytes = api_client.generate_pdf(
                        analysis,
                        access_token=st.session_state.get("access_token") or "guest",
                    )
                st.session_state["scorer_pdf_bytes"] = pdf_bytes
            except requests.RequestException as exc:
                _show_backend_error(exc)

        if "scorer_pdf_bytes" in st.session_state:
            st.download_button(
                "⬇️ Download PDF",
                data=st.session_state["scorer_pdf_bytes"],
                file_name="ats_resume_report.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_pdf_report",
            )

    with c2:
        st.download_button(
            "📄 Download Summary (.txt)",
            data=_summary_text(analysis),
            file_name="ats_summary.txt",
            mime="text/plain",
            use_container_width=True,
            key="download_summary",
        )


def render() -> None:
    st.title("🎯 ATS Resume Scorer")
    st.markdown("Upload your resume — and optionally a job description — for a comprehensive analysis.")

    with st.sidebar:
        st.markdown("---")
        st.markdown("## 📊 Analysis Options")
        st.info(
            "**General ATS Score**: resume only — overall compatibility.\n\n"
            "**JD Comparison**: resume + job description — targeted match analysis."
        )

    st.markdown("---")

    analysis_mode = st.radio(
        "Select Analysis Mode:",
        ["General ATS Score", "Job Description Comparison"],
        horizontal=True,
    )

    st.markdown("---")

    resume_file, jd_file, jd_text = _render_upload_area(analysis_mode)

    st.markdown("---")

    if not resume_file:
        st.info("👆 Upload your resume or load a sample resume above to begin.")
        # If we have a prior result in session, render it again.
        if st.session_state.get("scorer_analysis"):
            display_results_dashboard(st.session_state["scorer_analysis"])
        return

    access_token = st.session_state.get("access_token")
    if not access_token:
        st.info("👤 **Guest Mode Active**: Running full ATS analysis as guest. (Sign in from sidebar if you wish to persist your score history across sessions).")
        access_token = "guest"

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        analyze = st.button("🚀 Analyze Resume", use_container_width=True, type="primary")

    if not analyze:
        # Re-show previous result on rerun (e.g. after PDF generation).
        if st.session_state.get("scorer_analysis"):
            display_results_dashboard(st.session_state["scorer_analysis"])
            _render_export_buttons(st.session_state["scorer_analysis"])
        return

    # Fresh analysis — drop any cached PDF/result.
    st.session_state.pop("scorer_pdf_bytes", None)
    st.session_state.pop("scorer_analysis", None)

    job_description = _read_jd(jd_file, jd_text) if analysis_mode == "Job Description Comparison" else ""

    try:
        analysis = _analyze_with_progress(
            resume_file=resume_file,
            access_token=access_token,
            job_description=job_description,
        )
    except requests.RequestException as exc:
        _show_backend_error(exc)
        return

    st.session_state["scorer_analysis"] = analysis
    st.success("✅ Analysis complete!")
    display_results_dashboard(analysis)
    _render_export_buttons(analysis)
