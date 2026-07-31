"""Multi-job comparison page - paste 2-3 job descriptions to see which fits your resume best."""

import html as _html
import io
from pathlib import Path

import streamlit as st

from secrets_bridge import load_secrets_into_env

load_secrets_into_env(("GEMINI_API_KEY", "GOOGLE_API_KEY"))

from analyzer import AnalyzerError, JobComparison, compare_jobs
from ui_colors import score_color

st.set_page_config(page_title="Compare Jobs - Resume Job-Fit AI", page_icon="⚖️", layout="wide")

st.title("⚖️ Compare Jobs")
st.caption(
    "Paste your resume once, then paste 2–3 job descriptions. "
    "Get a ranked comparison - which role fits you best, and why."
)

# --- Session state -----------------------------------------------------------

def _init() -> None:
    defaults = {
        "cmp_resume": "",
        "cmp_pdf_name": None,
        "cmp_job1": "",
        "cmp_job2": "",
        "cmp_job3": "",
        "cmp_result": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()


# --- PDF helper (same as main app) -------------------------------------------

def extract_pdf_text(uploaded_file) -> str:
    import pdfplumber
    with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages).strip()


# --- Inputs ------------------------------------------------------------------

st.subheader("Your resume")
uploaded_pdf = st.file_uploader("Upload resume PDF (or paste below)", type="pdf")
if uploaded_pdf and uploaded_pdf.name != st.session_state.cmp_pdf_name:
    try:
        st.session_state.cmp_resume = extract_pdf_text(uploaded_pdf)
        st.session_state.cmp_pdf_name = uploaded_pdf.name
        st.session_state.cmp_result = None
        st.rerun()
    except Exception:
        st.error("Could not read the PDF. Try a text-based PDF or paste below.")

st.session_state.cmp_resume = st.text_area(
    "Resume text",
    value=st.session_state.cmp_resume,
    height=200,
    placeholder="Paste your resume here…",
    label_visibility="collapsed",
)

st.divider()
st.subheader("Job descriptions (paste 2 or 3)")

col1, col2, col3 = st.columns(3)
with col1:
    st.session_state.cmp_job1 = st.text_area(
        "Job 1", value=st.session_state.cmp_job1, height=280,
        placeholder="Paste job description #1…",
    )
with col2:
    st.session_state.cmp_job2 = st.text_area(
        "Job 2", value=st.session_state.cmp_job2, height=280,
        placeholder="Paste job description #2…",
    )
with col3:
    st.session_state.cmp_job3 = st.text_area(
        "Job 3 (optional)", value=st.session_state.cmp_job3, height=280,
        placeholder="Paste job description #3 (optional)…",
    )

btn_col, _ = st.columns([2, 5])
with btn_col:
    compare_clicked = st.button("Compare jobs ⚖️", type="primary", use_container_width=True)

if compare_clicked:
    jobs = [
        st.session_state.cmp_job1,
        st.session_state.cmp_job2,
        st.session_state.cmp_job3,
    ]
    with st.spinner("Comparing jobs with Gemini…"):
        try:
            st.session_state.cmp_result = compare_jobs(st.session_state.cmp_resume, jobs)
        except AnalyzerError as err:
            st.error(str(err))

# --- Results -----------------------------------------------------------------

if st.session_state.cmp_result:
    result: JobComparison = st.session_state.cmp_result

    st.divider()
    st.subheader("Results - ranked best fit first")

    # Recommendation banner
    rec_match = next(
        (m for m in result.matches if m.job_number == result.recommended_job), None
    )
    rec_title = rec_match.job_title if rec_match else f"Job {result.recommended_job}"
    st.success(
        f"**Best fit: {_html.escape(rec_title)}** (Job {result.recommended_job})  \n"
        f"{_html.escape(result.recommendation_reason)}"
    )

    # Apply order
    order_str = " → ".join(f"Job {n}" for n in result.apply_order)
    st.info(f"**Suggested apply order:** {order_str}")

    st.divider()

    # Per-job cards
    for match in result.matches:
        color = score_color(match.score)
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(result.apply_order.index(match.job_number) + 1
                                                   if match.job_number in result.apply_order else 0, "")

        with st.container(border=True):
            head_col, score_col = st.columns([5, 1])
            with head_col:
                st.markdown(
                    f"### {medal} Job {match.job_number} - {_html.escape(match.job_title)}"
                )
                st.caption(_html.escape(match.verdict))
            with score_col:
                st.markdown(
                    f"<div style='text-align:center;padding-top:0.5rem;'>"
                    f"<span style='font-size:2.2rem;font-weight:800;color:{color};'>{match.score}</span>"
                    f"<span style='font-size:0.9rem;color:#888;'>/100</span></div>",
                    unsafe_allow_html=True,
                )

            left, right = st.columns(2)
            with left:
                st.markdown("**Strengths matched**")
                for s in match.top_strengths:
                    st.markdown(f"- {_html.escape(s)}")
            with right:
                st.markdown("**Key gaps**")
                for g in match.top_gaps:
                    st.markdown(f"- {_html.escape(g)}")

    st.divider()
    st.caption(
        "Back to the main analyzer → use the sidebar · "
        "Built in public by Zaid Ali Syed "
        "· [Live demo](https://resume-job-fit-ai.streamlit.app) "
        "· [GitHub](https://github.com/syzayd/resume-job-fit-ai)"
    )
