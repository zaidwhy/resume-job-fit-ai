"""Download builders in exports.py: plain text and the two Word documents."""

from __future__ import annotations

import io

from docx import Document

from analyzer import (
    Analysis, BulletRewrite, CoverLetter, EmailTemplates, InterviewPrep, InterviewQuestion,
    LinkedInProfile, Resource, SkillGap, SkillsRoadmap,
)
from exports import analysis_as_text, export_docx, export_tailored_resume_docx


def _analysis() -> Analysis:
    return Analysis(
        score=82,
        verdict="Strong fit",
        salary_range="$90k-$120k",
        matched_keywords=["python", "sql"],
        missing_keywords=["go"],
        bullet_rewrites=[BulletRewrite(original="did stuff", improved="Shipped X, cutting latency 30%")],
        summary="Add Go projects.",
        ats_tips=["Use the exact phrase 'Kubernetes'"],
    )


def _docx_text(data: bytes) -> str:
    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs)


def test_text_export_has_core_sections_and_values():
    text = analysis_as_text(_analysis())
    assert "Score: 82/100" in text
    assert "Verdict: Strong fit" in text
    assert "Estimated Salary Range: $90k-$120k" in text
    assert "python, sql" in text and "go" in text
    assert "Before: did stuff" in text and "After:  Shipped X, cutting latency 30%" in text
    assert "COVER LETTER" not in text  # optional sections are absent until generated


def test_text_export_appends_every_optional_section():
    text = analysis_as_text(
        _analysis(),
        cover=CoverLetter(opening="Dear team", body="I built things", closing="Thanks"),
        prep=InterviewPrep(
            questions=[InterviewQuestion(question="Why us?", why_asked="fit", tip="be concrete")],
            opening_tip="Stay calm",
        ),
        roadmap=SkillsRoadmap(
            gaps=[SkillGap(skill="Go", importance="High", how_to_learn="Tour of Go",
                           resources=[Resource(name="Go course", provider="Coursera", type="Course")])],
            timeline="6 weeks",
            quick_wins=["Read the docs"],
        ),
        linkedin=LinkedInProfile(headline="Engineer", about="About me", skills_to_add=["Go"], profile_tips=["Add a photo"]),
        emails=EmailTemplates(follow_up="hi", thank_you="thanks", rejection_response="understood"),
    )
    for expected in ("COVER LETTER", "Dear team", "Q1: Why us?", "Timeline: 6 weeks", "[High] Go",
                     "Go course (Coursera, Course)", "Headline: Engineer", "APPLICATION FOLLOW-UP"):
        assert expected in text


def test_analysis_docx_is_a_valid_document_containing_the_score_and_rewrite():
    data = export_docx(_analysis())
    assert data[:2] == b"PK"  # a .docx is a zip
    text = _docx_text(data)
    assert "Resume Job-Fit Analysis" in text
    assert "Fit Score: 82/100" in text
    assert "Shipped X, cutting latency 30%" in text


def test_tailored_resume_docx_uses_the_improved_bullet_not_the_original():
    text = _docx_text(export_tailored_resume_docx(_analysis()))
    assert "Shipped X, cutting latency 30%" in text
    assert "did stuff" not in text
