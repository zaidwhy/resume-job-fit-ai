"""Streamlit panels for each result section of the main page."""

import html as _html

import streamlit as st

from analyzer import (
    Analysis, CoverLetter, EmailTemplates, InterviewPrep, LinkedInProfile, ResumeHealth,
    SkillsRoadmap,
)
from ui_colors import score_color


def chips(items: list[str], bg: str, fg: str) -> None:
    if not items:
        st.caption("None found.")
        return
    html = " ".join(
        f"<span style='background:{bg};color:{fg};padding:4px 10px;border-radius:14px;"
        f"font-size:0.85rem;margin:2px;display:inline-block;'>{_html.escape(item)}</span>"
        for item in items
    )
    st.markdown(html, unsafe_allow_html=True)



def render_analysis(result: Analysis) -> None:
    color = score_color(result.score)
    st.markdown(
        f"<div style='text-align:center;margin:0.5rem 0;'>"
        f"<span style='font-size:3.5rem;font-weight:800;color:{color};'>{result.score}</span>"
        f"<span style='font-size:1.2rem;color:#888;'>/100</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='text-align:center;font-size:1.1rem;'>{_html.escape(result.verdict)}</p>",
        unsafe_allow_html=True,
    )
    if result.salary_range:
        st.markdown(
            f"<div style='text-align:center;margin:0.25rem 0 0.75rem;'>"
            f"<span style='background:#fefce8;color:#854d0e;border:1px solid #fde68a;"
            f"padding:5px 14px;border-radius:20px;font-size:0.9rem;font-weight:600;'>"
            f"💰 Estimated salary: {_html.escape(result.salary_range)}</span></div>",
            unsafe_allow_html=True,
        )
    st.divider()

    left, right = st.columns(2)
    with left:
        st.subheader("Matched keywords")
        chips(result.matched_keywords, "#dcfce7", "#166534")
    with right:
        st.subheader("Missing keywords")
        chips(result.missing_keywords, "#fee2e2", "#991b1b")

    st.divider()
    st.subheader("Tailored bullet rewrites")
    st.caption("Original on the left · AI rewrite on the right · Copy individual rewrites or all at once.")
    for i, rw in enumerate(result.bullet_rewrites):
        left_col, right_col = st.columns(2)
        with left_col:
            st.markdown(
                f"<div style='background:#f3f4f6;border-left:3px solid #9ca3af;"
                f"padding:12px 14px;border-radius:6px;font-size:0.88rem;'>"
                f"<div style='color:#6b7280;font-size:0.72rem;font-weight:700;"
                f"text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;'>Original</div>"
                f"{_html.escape(rw.original)}</div>",
                unsafe_allow_html=True,
            )
        with right_col:
            st.markdown(
                f"<div style='background:#f0fdf4;border-left:3px solid #16a34a;"
                f"padding:12px 14px;border-radius:6px;font-size:0.88rem;'>"
                f"<div style='color:#16a34a;font-size:0.72rem;font-weight:700;"
                f"text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;'>Rewritten ✓</div>"
                f"{_html.escape(rw.improved)}</div>",
                unsafe_allow_html=True,
            )
            with st.expander(f"Copy rewrite #{i + 1}"):
                st.code(rw.improved, language=None)
        st.write("")
    if result.bullet_rewrites:
        with st.expander("Copy all rewrites"):
            st.code(
                "\n\n".join(rw.improved for rw in result.bullet_rewrites),
                language=None,
            )

    st.divider()
    st.subheader("How to improve this application")
    st.write(result.summary)
    if result.ats_tips:
        st.markdown("**ATS tips:**")
        for tip in result.ats_tips:
            st.markdown(f"- {tip}")


def render_cover_letter(cover: CoverLetter) -> None:
    st.write(cover.opening)
    st.write(cover.body)
    st.write(cover.closing)
    st.divider()
    with st.expander("Copy full letter"):
        st.code(f"{cover.opening}\n\n{cover.body}\n\n{cover.closing}", language=None)


def render_interview_prep(prep: InterviewPrep) -> None:
    st.info(f"**Key advice:** {prep.opening_tip}")
    st.divider()
    for i, q in enumerate(prep.questions, 1):
        with st.container(border=True):
            st.markdown(f"**Q{i}: {q.question}**")
            st.caption(f"Why asked: {q.why_asked}")
            st.markdown(f"Tip: {q.tip}")
            with st.expander("Copy question + tip"):
                st.code(f"Q: {q.question}\n\nTip: {q.tip}", language=None)


def render_skills_roadmap(roadmap: SkillsRoadmap) -> None:
    st.markdown(f"**Estimated timeline to close key gaps:** {roadmap.timeline}")
    if roadmap.quick_wins:
        st.subheader("Quick wins this week")
        for win in roadmap.quick_wins:
            st.markdown(f"- {win}")
    st.divider()
    st.subheader("Skill gaps - priority order")
    importance_color = {"High": "#fee2e2", "Medium": "#fef9c3", "Low": "#f0fdf4"}
    importance_fg = {"High": "#991b1b", "Medium": "#854d0e", "Low": "#166534"}
    for gap in roadmap.gaps:
        bg = importance_color.get(gap.importance, "#f3f4f6")
        fg = importance_fg.get(gap.importance, "#374151")
        with st.container(border=True):
            st.markdown(
                f"<span style='background:{bg};color:{fg};padding:2px 8px;"
                f"border-radius:10px;font-size:0.8rem;font-weight:600;'>{_html.escape(gap.importance)}</span>"
                f" &nbsp; **{_html.escape(gap.skill)}**",
                unsafe_allow_html=True,
            )
            st.write(gap.how_to_learn)
            if gap.resources:
                for r in gap.resources:
                    st.markdown(f"- **{r.name}** - {r.provider} _{r.type}_")


def render_resume_health(health: ResumeHealth) -> None:
    color = score_color(health.overall_score)
    st.markdown(
        f"<div style='text-align:center;margin:0.5rem 0;'>"
        f"<span style='font-size:3.5rem;font-weight:800;color:{color};'>{health.overall_score}</span>"
        f"<span style='font-size:1.2rem;color:#888;'>/100</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='text-align:center;color:#6b7280;'>{_html.escape(health.length_assessment)}</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    st.subheader("Score breakdown")
    c1, c2, c3 = st.columns(3)
    for col, label, val in [
        (c1, "Writing clarity", health.writing_score),
        (c2, "Quantification", health.quantification_score),
        (c3, "Verb strength", health.verb_strength_score),
    ]:
        with col:
            sub_color = score_color(val)
            st.markdown(
                f"<div style='text-align:center;'>"
                f"<div style='font-size:0.8rem;color:#6b7280;margin-bottom:4px;'>{label}</div>"
                f"<div style='font-size:2rem;font-weight:700;color:{sub_color};'>{val}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.progress(val / 100)

    st.divider()
    col_issues, col_fixes = st.columns(2)
    with col_issues:
        st.subheader("Top issues")
        for issue in health.top_issues:
            st.markdown(f"- {_html.escape(issue)}", unsafe_allow_html=False)
    with col_fixes:
        st.subheader("Quick fixes")
        for fix in health.quick_fixes:
            st.markdown(f"- {_html.escape(fix)}", unsafe_allow_html=False)


def render_email_templates(emails: EmailTemplates) -> None:
    for label, body in [
        ("📩 Application Follow-up", emails.follow_up),
        ("🤝 Post-Interview Thank You", emails.thank_you),
        ("🚪 Graceful Rejection Response", emails.rejection_response),
    ]:
        st.subheader(label)
        st.write(body)
        with st.expander("Copy"):
            st.code(body, language=None)
        st.write("")


def render_linkedin_profile(profile: LinkedInProfile) -> None:
    st.subheader("Headline")
    st.markdown(f"> {_html.escape(profile.headline)}", unsafe_allow_html=False)
    with st.expander("Copy headline"):
        st.code(profile.headline, language=None)

    st.divider()
    st.subheader("About section")
    st.write(profile.about)
    with st.expander("Copy About section"):
        st.code(profile.about, language=None)

    st.divider()
    st.subheader("Skills to add on LinkedIn")
    chips(profile.skills_to_add, "#dbeafe", "#1e40af")

    st.divider()
    st.subheader("Profile tips")
    for tip in profile.profile_tips:
        st.markdown(f"- {tip}")
