"""Headless render of the main page (Streamlit AppTest): the entrypoint and its modules wire up.

No network and no API key: nothing is generated, results are placed in session state.
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from analyzer import (
    Analysis, BulletRewrite, CoverLetter, EmailTemplates, InterviewPrep, InterviewQuestion,
    LinkedInProfile, Resource, ResumeHealth, SkillGap, SkillsRoadmap,
)

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def test_empty_page_renders_without_error():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert at.title[0].value == "Resume Job-Fit AI"
    assert [b.label for b in at.button][:3] == ["Analyze fit", "Load sample", "Clear"]
    assert len(at.tabs) == 0  # result tabs appear only after an analysis


def test_populated_page_renders_every_result_tab():
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["resume"] = "my resume"
    at.session_state["job"] = "my job"
    at.session_state["result"] = Analysis(
        score=82, verdict="Strong fit", salary_range="$90k-$120k",
        matched_keywords=["python"], missing_keywords=["go"],
        bullet_rewrites=[BulletRewrite(original="did stuff", improved="Shipped X")],
        summary="Add Go.", ats_tips=["Use 'Kubernetes'"],
    )
    at.session_state["cover_letter"] = CoverLetter(opening="Dear team", body="I built things", closing="Thanks")
    at.session_state["interview_prep"] = InterviewPrep(
        questions=[InterviewQuestion(question="Why us?", why_asked="fit", tip="be concrete")], opening_tip="Stay calm",
    )
    at.session_state["skills_roadmap"] = SkillsRoadmap(
        gaps=[SkillGap(skill="Go", importance="High", how_to_learn="Tour of Go",
                       resources=[Resource(name="Go course", provider="Coursera", type="Course")])],
        timeline="6 weeks", quick_wins=["Read the docs"],
    )
    at.session_state["linkedin_profile"] = LinkedInProfile(
        headline="Engineer", about="About me", skills_to_add=["Go"], profile_tips=["Add a photo"],
    )
    at.session_state["email_templates"] = EmailTemplates(follow_up="hi", thank_you="thanks", rejection_response="ok")
    at.session_state["resume_health"] = ResumeHealth(
        overall_score=70, writing_score=60, quantification_score=40, verb_strength_score=80,
        length_assessment="Ideal (1 page)", top_issues=["a"], quick_fixes=["b"],
    )

    at.run()

    assert not at.exception
    assert [t.label for t in at.tabs] == [
        "Analysis", "Cover Letter", "Interview Prep", "Skills Roadmap", "LinkedIn Profile", "Emails", "Resume Health",
    ]
    assert "Dear team" in " ".join(m.value for m in at.markdown)
