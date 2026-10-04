"""Streamlit UI for the AI Resume / Job-Fit Tool.

Run: streamlit run app.py
"""

import io
import logging
from pathlib import Path

import streamlit as st

from secrets_bridge import load_secrets_into_env

# One stdout handler (Streamlit Cloud collects stdout). basicConfig is a no-op on reruns.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# Streamlit Community Cloud stores secrets in st.secrets, not env vars.
# Inject them into os.environ so analyzer.py's os.environ.get() calls work on Cloud.
load_secrets_into_env(("GEMINI_API_KEY", "GOOGLE_API_KEY"))

from analyzer import (
    Analysis, AnalyzerError, CompanyProfile, CoverLetter, EmailTemplates, InterviewPrep,
    LinkedInProfile, ResumeHealth, SkillsRoadmap, analyze, analyze_resume_health,
    generate_cover_letter, generate_email_templates, generate_interview_prep,
    generate_linkedin_profile, generate_skills_roadmap, research_company,
)
from db import save_application
from exports import analysis_as_text, export_docx, export_tailored_resume_docx
from session_owner import current_owner
from ui_sections import (
    render_analysis, render_cover_letter, render_email_templates, render_interview_prep,
    render_linkedin_profile, render_resume_health, render_skills_roadmap,
)

SAMPLE_DIR = Path(__file__).parent / "sample"

st.set_page_config(page_title="Resume Job-Fit AI", page_icon="🎯", layout="wide")


# --- Helpers -----------------------------------------------------------------

def load_sample(name: str) -> str:
    try:
        return (SAMPLE_DIR / name).read_text(encoding="utf-8")
    except OSError:
        return ""


def extract_pdf_text(uploaded_file) -> str:
    import pdfplumber
    with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages).strip()


# --- Session state init ------------------------------------------------------

def _init() -> None:
    defaults = {
        "resume": "",
        "job": "",
        "pdf_name": None,
        "result": None,
        "cover_letter": None,
        "cover_letter_tone": "Professional",
        "interview_prep": None,
        "skills_roadmap": None,
        "linkedin_profile": None,
        "email_templates": None,
        "resume_health": None,
        "tracker_saved": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()

# --- Layout ------------------------------------------------------------------

st.title("Resume Job-Fit AI")
st.caption(
    "Paste or upload your resume + a job description - get a fit score, keyword gaps, "
    "tailored rewrites, cover letter, interview prep, and a skills roadmap. "
    "Powered by Google Gemini (free tier)."
)

col_a, col_b = st.columns(2)
with col_a:
    st.session_state.job = st.text_area(
        "Job description", value=st.session_state.job,
        height=300, placeholder="Paste the job posting here...",
    )
with col_b:
    uploaded_pdf = st.file_uploader(
        "Upload resume PDF (or paste below)", type="pdf", label_visibility="visible",
    )
    if uploaded_pdf is not None and uploaded_pdf.name != st.session_state.pdf_name:
        try:
            st.session_state.resume = extract_pdf_text(uploaded_pdf)
            st.session_state.pdf_name = uploaded_pdf.name
            st.session_state.result = None
            st.session_state.cover_letter = None
            st.session_state.interview_prep = None
            st.session_state.skills_roadmap = None
            st.session_state.linkedin_profile = None
            st.session_state.email_templates = None
            st.session_state.resume_health = None
            st.rerun()
        except Exception:
            st.error("Could not read the PDF. Try a text-based PDF or paste your resume below.")

    st.session_state.resume = st.text_area(
        "Your resume", value=st.session_state.resume,
        height=220, placeholder="Paste your resume text here...",
        label_visibility="collapsed",
    )

btn_analyze, btn_sample, btn_clear, _ = st.columns([1, 1, 1, 3])
with btn_analyze:
    analyze_clicked = st.button("Analyze fit", type="primary", use_container_width=True)
with btn_sample:
    if st.button("Load sample", use_container_width=True):
        st.session_state.resume = load_sample("sample_resume.txt")
        st.session_state.job = load_sample("sample_job.txt")
        st.session_state.pdf_name = None
        st.session_state.result = None
        st.session_state.cover_letter = None
        st.session_state.interview_prep = None
        st.session_state.skills_roadmap = None
        st.session_state.linkedin_profile = None
        st.session_state.email_templates = None
        st.session_state.resume_health = None
        st.rerun()
with btn_clear:
    if st.button("Clear", use_container_width=True):
        st.session_state.resume = ""
        st.session_state.job = ""
        st.session_state.pdf_name = None
        st.session_state.result = None
        st.session_state.cover_letter = None
        st.session_state.interview_prep = None
        st.session_state.skills_roadmap = None
        st.session_state.linkedin_profile = None
        st.session_state.email_templates = None
        st.session_state.resume_health = None
        st.rerun()

if analyze_clicked:
    with st.spinner("Analyzing with Gemini..."):
        try:
            st.session_state.result = analyze(st.session_state.resume, st.session_state.job)
            st.session_state.cover_letter = None
            st.session_state.interview_prep = None
            st.session_state.skills_roadmap = None
            st.session_state.linkedin_profile = None
            st.session_state.email_templates = None
            st.session_state.tracker_saved = False
        except AnalyzerError as err:
            st.error(str(err))

# --- Results (persist across reruns) -----------------------------------------

if st.session_state.result:
    result: Analysis = st.session_state.result

    # "Generate all sections" - runs all 4 AI generators in one click
    _todo = [k for k in ("cover_letter", "interview_prep", "skills_roadmap", "linkedin_profile", "email_templates")
             if st.session_state[k] is None]
    if _todo:
        _gen_all_col, _ = st.columns([2, 5])
        with _gen_all_col:
            if st.button("Generate all sections ✨", type="primary", use_container_width=True):
                _generators = [
                    (generate_interview_prep,   "interview_prep",   "Interview Prep"),
                    (generate_skills_roadmap,   "skills_roadmap",   "Skills Roadmap"),
                    (generate_linkedin_profile, "linkedin_profile", "LinkedIn Profile"),
                    (generate_email_templates,  "email_templates",  "Email Templates"),
                ]
                _progress = st.progress(0, text="Starting…")
                if st.session_state.cover_letter is None:
                    _progress.progress(0, text="Generating Cover Letter…")
                    try:
                        st.session_state.cover_letter = generate_cover_letter(
                            st.session_state.resume,
                            st.session_state.job,
                            st.session_state.cover_letter_tone,
                        )
                    except AnalyzerError as _err:
                        st.warning(f"Cover Letter: {_err}")
                for _i, (_fn, _key, _label) in enumerate(_generators):
                    if st.session_state[_key] is None:
                        _progress.progress((_i + 1) / (len(_generators) + 1), text=f"Generating {_label}…")
                        try:
                            st.session_state[_key] = _fn(
                                st.session_state.resume, st.session_state.job
                            )
                        except AnalyzerError as _err:
                            st.warning(f"{_label}: {_err}")
                _progress.progress(1.0, text="All sections ready!")
                st.rerun()

    tab_analysis, tab_cover, tab_interview, tab_roadmap, tab_linkedin, tab_emails, tab_health = st.tabs(
        ["Analysis", "Cover Letter", "Interview Prep", "Skills Roadmap", "LinkedIn Profile", "Emails", "Resume Health"]
    )

    with tab_analysis:
        render_analysis(result)

    with tab_cover:
        cover: CoverLetter | None = st.session_state.cover_letter
        _tone = st.radio(
            "Tone",
            ["Professional", "Warm & Enthusiastic", "Bold & Direct"],
            index=["Professional", "Warm & Enthusiastic", "Bold & Direct"].index(
                st.session_state.cover_letter_tone
            ),
            horizontal=True,
            key="_tone_radio",
        )
        if _tone != st.session_state.cover_letter_tone:
            st.session_state.cover_letter_tone = _tone
        _btn_label = "Generate cover letter" if cover is None else "Regenerate with this tone"
        if st.button(_btn_label, type="primary"):
            with st.spinner("Writing your cover letter with Gemini..."):
                try:
                    cover = generate_cover_letter(
                        st.session_state.resume, st.session_state.job, _tone
                    )
                    st.session_state.cover_letter = cover
                    st.rerun()
                except AnalyzerError as err:
                    st.error(str(err))
        if cover:
            render_cover_letter(cover)

    with tab_interview:
        st.caption(
            "Want to research the company first? Use the **Company Research** page in the sidebar."
        )
        prep: InterviewPrep | None = st.session_state.interview_prep
        if prep is None:
            if st.button("Generate interview prep", type="primary"):
                with st.spinner("Generating interview questions with Gemini..."):
                    try:
                        prep = generate_interview_prep(
                            st.session_state.resume, st.session_state.job
                        )
                        st.session_state.interview_prep = prep
                        st.rerun()
                    except AnalyzerError as err:
                        st.error(str(err))
        if prep:
            render_interview_prep(prep)

    with tab_roadmap:
        roadmap: SkillsRoadmap | None = st.session_state.skills_roadmap
        if roadmap is None:
            if st.button("Generate skills roadmap", type="primary"):
                with st.spinner("Building your skills roadmap with Gemini..."):
                    try:
                        roadmap = generate_skills_roadmap(
                            st.session_state.resume, st.session_state.job
                        )
                        st.session_state.skills_roadmap = roadmap
                        st.rerun()
                    except AnalyzerError as err:
                        st.error(str(err))
        if roadmap:
            render_skills_roadmap(roadmap)

    with tab_linkedin:
        li_profile: LinkedInProfile | None = st.session_state.linkedin_profile
        if li_profile is None:
            st.caption(
                "Get an optimized LinkedIn headline, a ready-to-paste About section, "
                "skills to add, and profile tips - all tailored to this role."
            )
            if st.button("Optimize LinkedIn profile", type="primary"):
                with st.spinner("Optimizing your LinkedIn profile with Gemini..."):
                    try:
                        li_profile = generate_linkedin_profile(
                            st.session_state.resume, st.session_state.job
                        )
                        st.session_state.linkedin_profile = li_profile
                        st.rerun()
                    except AnalyzerError as err:
                        st.error(str(err))
        if li_profile:
            render_linkedin_profile(li_profile)

    with tab_emails:
        emails: EmailTemplates | None = st.session_state.email_templates
        if emails is None:
            st.caption(
                "Three ready-to-send email templates grounded in your resume and this role: "
                "a follow-up after applying, a thank-you note after your interview, "
                "and a graceful reply to a rejection."
            )
            if st.button("Generate email templates", type="primary"):
                with st.spinner("Drafting email templates with Gemini..."):
                    try:
                        emails = generate_email_templates(
                            st.session_state.resume, st.session_state.job
                        )
                        st.session_state.email_templates = emails
                        st.rerun()
                    except AnalyzerError as err:
                        st.error(str(err))
        if emails:
            render_email_templates(emails)

    with tab_health:
        rh: ResumeHealth | None = st.session_state.resume_health
        if rh is None:
            st.caption(
                "Evaluates your resume on its own - writing quality, quantification, "
                "verb strength, and length - independent of any specific job."
            )
            if st.button("Check resume health", type="primary"):
                with st.spinner("Analyzing your resume with Gemini..."):
                    try:
                        rh = analyze_resume_health(st.session_state.resume)
                        st.session_state.resume_health = rh
                        st.rerun()
                    except AnalyzerError as err:
                        st.error(str(err))
        if rh:
            render_resume_health(rh)

    st.divider()
    _dl_txt, _dl_docx, _dl_resume, _ = st.columns([1, 1, 1, 3])
    with _dl_txt:
        st.download_button(
            label="Download (.txt)",
            data=analysis_as_text(
                result,
                st.session_state.cover_letter,
                st.session_state.interview_prep,
                st.session_state.skills_roadmap,
                st.session_state.linkedin_profile,
                st.session_state.email_templates,
            ),
            file_name="resume_analysis.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with _dl_docx:
        st.download_button(
            label="Download (.docx)",
            data=export_docx(
                result,
                st.session_state.cover_letter,
                st.session_state.interview_prep,
                st.session_state.skills_roadmap,
                st.session_state.linkedin_profile,
                st.session_state.email_templates,
            ),
            file_name="resume_analysis.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
    with _dl_resume:
        st.download_button(
            label="Tailored Resume (.docx)",
            data=export_tailored_resume_docx(result),
            file_name="tailored_resume.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            help="A ready-to-edit resume with AI-improved bullets and ATS notes pre-filled.",
        )

    # Save to tracker
    st.divider()
    if st.session_state.tracker_saved:
        st.success("Saved to Job Tracker! View it in the **Job Tracker** page (sidebar).")
    else:
        with st.form("save_to_tracker"):
            _tc1, _tc2, _tc3 = st.columns([2, 2, 1])
            with _tc1:
                _job_title = st.text_input(
                    "Job title",
                    placeholder="e.g. Senior Python Engineer",
                )
            with _tc2:
                _company = st.text_input(
                    "Company (optional)",
                    placeholder="e.g. Acme Corp",
                )
            with _tc3:
                st.markdown("<br>", unsafe_allow_html=True)
                _save_clicked = st.form_submit_button(
                    "Save to tracker 📋", use_container_width=True
                )
            if _save_clicked:
                if not _job_title.strip():
                    st.warning("Enter a job title to save.")
                else:
                    save_application(
                        owner=current_owner(),
                        job_title=_job_title,
                        score=result.score,
                        company=_company,
                    )
                    st.session_state.tracker_saved = True
                    st.rerun()

st.divider()
st.caption(
    "Built in public by Zaid Ali Syed "
    "· [Live demo](https://resume-job-fit-ai.streamlit.app) "
    "· [GitHub](https://github.com/zaidwhy/resume-job-fit-ai) "
    "· Rewrites stay truthful to your resume - review before using."
)
