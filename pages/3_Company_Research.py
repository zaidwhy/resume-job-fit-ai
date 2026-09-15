"""Company Research - powered by Google Gemini.

Enter a company name and optional role to get a culture profile, interview format,
what they value, honest red flags, and prep tips.
"""

import html as _html

import streamlit as st

from secrets_bridge import load_secrets_into_env

load_secrets_into_env(("GEMINI_API_KEY", "GOOGLE_API_KEY"))

from analyzer import AnalyzerError, CompanyProfile, research_company

st.set_page_config(
    page_title="Company Research - Resume Job-Fit AI",
    page_icon="🔍",
    layout="wide",
)

st.title("Company Research")
st.caption(
    "Enter a company name (and optional role) to get a culture profile, interview format, "
    "what they value, honest red flags, and specific prep tips - powered by Google Gemini."
)

col_a, col_b = st.columns([2, 1])
with col_a:
    company_name = st.text_input(
        "Company name",
        placeholder="e.g. Google, Stripe, Shopify, Anthropic…",
    )
with col_b:
    role = st.text_input(
        "Role (optional)",
        placeholder="e.g. Senior Software Engineer",
    )

research_clicked = st.button("Research company", type="primary")

if research_clicked:
    if not company_name.strip():
        st.warning("Enter a company name to research.")
    else:
        with st.spinner(f"Researching {company_name} with Gemini…"):
            try:
                profile = research_company(company_name, role)
                st.session_state["company_profile"] = profile
                st.session_state["company_profile_name"] = company_name
            except AnalyzerError as err:
                st.error(str(err))

profile: CompanyProfile | None = st.session_state.get("company_profile")
if profile:
    researched_name = st.session_state.get("company_profile_name", "Company")
    st.divider()

    # Culture overview
    st.subheader(f"Culture - {_html.escape(researched_name)}")
    st.write(profile.culture_summary)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Work Style")
        st.info(profile.work_style)
    with col2:
        st.subheader("Typical Interview Format")
        st.write(profile.typical_interview_format)

    st.divider()
    col3, col4 = st.columns(2)
    with col3:
        st.subheader("What They Value")
        for item in profile.what_they_value:
            st.markdown(f"- {_html.escape(item)}")
    with col4:
        st.subheader("Honest Red Flags")
        if profile.red_flags:
            for flag in profile.red_flags:
                st.markdown(f"- {_html.escape(flag)}")
        else:
            st.caption("No significant red flags identified.")

    st.divider()
    st.subheader("Prep Tips")
    for tip in profile.prep_tips:
        st.markdown(f"- {_html.escape(tip)}")

    with st.expander("Copy all prep tips"):
        st.code("\n".join(f"- {tip}" for tip in profile.prep_tips), language=None)

st.divider()
st.caption(
    "Built in public by Zaid Ali Syed "
    "· [Live demo](https://resume-job-fit-ai.streamlit.app) "
    "· [GitHub](https://github.com/zaidwhy/resume-job-fit-ai) "
    "· AI-generated - verify key facts before your interview."
)
