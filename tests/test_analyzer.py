"""Unit tests for analyzer.py - all Gemini calls are mocked."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import analyzer
from analyzer import (
    Analysis,
    AnalyzerError,
    BulletRewrite,
    CompanyProfile,
    CoverLetter,
    InterviewPrep,
    InterviewQuestion,
    JobComparison,
    JobMatch,
    LinkedInProfile,
    Resource,
    SkillGap,
    SkillsRoadmap,
    _parse_from_text,
    _validate,
    analyze,
    compare_jobs,
    generate_cover_letter,
    generate_interview_prep,
    generate_linkedin_profile,
    generate_skills_roadmap,
    research_company,
)


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

RESUME = "Software engineer with 3 years Python experience, built REST APIs."
JOB = "Senior Python Engineer - FastAPI, PostgreSQL, AWS required."


def _make_response(parsed_obj):
    """Fake Gemini response with .parsed and .text."""
    resp = SimpleNamespace()
    resp.parsed = parsed_obj
    resp.text = None
    return resp


def _valid_analysis() -> Analysis:
    return Analysis(
        score=72,
        verdict="Good match, a few gaps.",
        matched_keywords=["Python", "REST APIs"],
        missing_keywords=["FastAPI", "PostgreSQL", "AWS"],
        bullet_rewrites=[
            BulletRewrite(original="Built APIs", improved="Built REST APIs using FastAPI")
        ],
        summary="Add FastAPI and AWS to your resume.",
        ats_tips=["Include 'FastAPI' in your skills section."],
    )


# ---------------------------------------------------------------------------
# _validate
# ---------------------------------------------------------------------------

class TestValidate:
    def test_empty_resume_raises(self):
        with pytest.raises(AnalyzerError, match="resume"):
            _validate("", JOB)

    def test_empty_job_raises(self):
        with pytest.raises(AnalyzerError, match="resume"):
            _validate(RESUME, "")

    def test_oversized_resume_raises(self):
        with pytest.raises(AnalyzerError, match="too long"):
            _validate("x" * (analyzer.MAX_INPUT_CHARS + 1), JOB)

    def test_oversized_job_raises(self):
        with pytest.raises(AnalyzerError, match="too long"):
            _validate(RESUME, "x" * (analyzer.MAX_INPUT_CHARS + 1))

    def test_valid_inputs_do_not_raise(self):
        _validate(RESUME, JOB)  # should not raise


# ---------------------------------------------------------------------------
# _parse_from_text
# ---------------------------------------------------------------------------

class TestParseFromText:
    def test_parses_valid_json(self):
        obj = _valid_analysis()
        raw = obj.model_dump_json()
        result = _parse_from_text(raw, Analysis)
        assert isinstance(result, Analysis)
        assert result.score == 72

    def test_raises_on_empty_text(self):
        with pytest.raises(AnalyzerError, match="empty"):
            _parse_from_text("", Analysis)

    def test_raises_on_no_json(self):
        with pytest.raises(AnalyzerError, match="Could not read"):
            _parse_from_text("no json here", Analysis)

    def test_raises_on_malformed_json(self):
        with pytest.raises(AnalyzerError, match="malformed"):
            _parse_from_text('{"score": "not-an-int"}', Analysis)

    def test_strips_surrounding_markdown(self):
        obj = _valid_analysis()
        wrapped = f"```json\n{obj.model_dump_json()}\n```"
        result = _parse_from_text(wrapped, Analysis)
        assert result.score == 72


# ---------------------------------------------------------------------------
# analyze()
# ---------------------------------------------------------------------------

class TestAnalyze:
    @patch("analyzer._client")
    @patch("analyzer._generate")
    def test_returns_analysis_when_parsed_is_set(self, mock_gen, mock_client):
        mock_gen.return_value = _make_response(_valid_analysis())
        result = analyze(RESUME, JOB)
        assert isinstance(result, Analysis)
        assert result.score == 72

    @patch("analyzer._client")
    @patch("analyzer._generate")
    def test_falls_back_to_parse_from_text_when_parsed_is_none(self, mock_gen, mock_client):
        obj = _valid_analysis()
        resp = _make_response(None)
        resp.text = obj.model_dump_json()
        mock_gen.return_value = resp
        result = analyze(RESUME, JOB)
        assert result.score == 72

    def test_raises_analyzer_error_on_empty_inputs(self):
        with pytest.raises(AnalyzerError):
            analyze("", JOB)


# ---------------------------------------------------------------------------
# generate_cover_letter()
# ---------------------------------------------------------------------------

class TestGenerateCoverLetter:
    @patch("analyzer._client")
    @patch("analyzer._generate")
    def test_returns_cover_letter(self, mock_gen, mock_client):
        cover = CoverLetter(
            opening="Dear Hiring Manager,",
            body="I have 3 years of Python experience.",
            closing="Sincerely, Zaid",
        )
        mock_gen.return_value = _make_response(cover)
        result = generate_cover_letter(RESUME, JOB)
        assert isinstance(result, CoverLetter)
        assert "Dear" in result.opening

    def test_raises_on_empty_resume(self):
        with pytest.raises(AnalyzerError):
            generate_cover_letter("", JOB)


# ---------------------------------------------------------------------------
# generate_interview_prep()
# ---------------------------------------------------------------------------

class TestGenerateInterviewPrep:
    @patch("analyzer._client")
    @patch("analyzer._generate")
    def test_returns_interview_prep(self, mock_gen, mock_client):
        prep = InterviewPrep(
            questions=[
                InterviewQuestion(
                    question="Describe a FastAPI project.",
                    why_asked="Tests direct experience with required tech.",
                    tip="Reference the REST APIs you built.",
                )
            ],
            opening_tip="Lead with your Python depth.",
        )
        mock_gen.return_value = _make_response(prep)
        result = generate_interview_prep(RESUME, JOB)
        assert isinstance(result, InterviewPrep)
        assert len(result.questions) == 1


# ---------------------------------------------------------------------------
# generate_skills_roadmap()
# ---------------------------------------------------------------------------

class TestGenerateSkillsRoadmap:
    @patch("analyzer._client")
    @patch("analyzer._generate")
    def test_returns_roadmap(self, mock_gen, mock_client):
        roadmap = SkillsRoadmap(
            gaps=[
                SkillGap(
                    skill="FastAPI",
                    importance="High",
                    how_to_learn="Build a project with FastAPI.",
                    resources=[Resource(name="FastAPI Docs", provider="fastapi.tiangolo.com", type="Tutorial")],
                )
            ],
            timeline="4-6 weeks",
            quick_wins=["Add FastAPI to your LinkedIn skills."],
        )
        mock_gen.return_value = _make_response(roadmap)
        result = generate_skills_roadmap(RESUME, JOB)
        assert isinstance(result, SkillsRoadmap)
        assert result.gaps[0].skill == "FastAPI"


# ---------------------------------------------------------------------------
# generate_linkedin_profile()
# ---------------------------------------------------------------------------

class TestGenerateLinkedInProfile:
    @patch("analyzer._client")
    @patch("analyzer._generate")
    def test_returns_linkedin_profile(self, mock_gen, mock_client):
        profile = LinkedInProfile(
            headline="Python Engineer | FastAPI | REST APIs",
            about="I build reliable backend systems.",
            skills_to_add=["FastAPI", "PostgreSQL", "AWS"],
            profile_tips=["Add a featured section with your best project."],
        )
        mock_gen.return_value = _make_response(profile)
        result = generate_linkedin_profile(RESUME, JOB)
        assert isinstance(result, LinkedInProfile)
        assert "FastAPI" in result.headline


# ---------------------------------------------------------------------------
# compare_jobs()
# ---------------------------------------------------------------------------

class TestCompareJobs:
    JOB2 = "Data Scientist - Python, pandas, ML required."

    @patch("analyzer._client")
    @patch("analyzer._generate")
    def test_returns_comparison(self, mock_gen, mock_client):
        comparison = JobComparison(
            matches=[
                JobMatch(job_number=1, job_title="Senior Python Engineer", score=72,
                         top_strengths=["Python", "REST APIs"], top_gaps=["FastAPI"],
                         verdict="Good match."),
                JobMatch(job_number=2, job_title="Data Scientist", score=45,
                         top_strengths=["Python"], top_gaps=["pandas", "ML"],
                         verdict="Partial match."),
            ],
            recommended_job=1,
            recommendation_reason="Better alignment with engineering background.",
            apply_order=[1, 2],
        )
        mock_gen.return_value = _make_response(comparison)
        result = compare_jobs(RESUME, [JOB, self.JOB2])
        assert isinstance(result, JobComparison)
        assert result.recommended_job == 1

    def test_raises_on_only_one_job(self):
        with pytest.raises(AnalyzerError, match="at least 2"):
            compare_jobs(RESUME, [JOB])

    def test_raises_on_empty_resume(self):
        with pytest.raises(AnalyzerError, match="resume"):
            compare_jobs("", [JOB, self.JOB2])

    def test_caps_at_three_jobs(self):
        """Extra jobs beyond 3 are silently dropped."""
        with patch("analyzer._client"), patch("analyzer._generate") as mock_gen:
            comparison = JobComparison(
                matches=[
                    JobMatch(job_number=1, job_title="Job A", score=80,
                             top_strengths=[], top_gaps=[], verdict="Great."),
                    JobMatch(job_number=2, job_title="Job B", score=60,
                             top_strengths=[], top_gaps=[], verdict="Ok."),
                    JobMatch(job_number=3, job_title="Job C", score=50,
                             top_strengths=[], top_gaps=[], verdict="Weak."),
                ],
                recommended_job=1,
                recommendation_reason="Best technical fit.",
                apply_order=[1, 2, 3],
            )
            mock_gen.return_value = _make_response(comparison)
            result = compare_jobs(RESUME, [JOB, self.JOB2, JOB, JOB])  # 4 jobs - should cap at 3
            assert isinstance(result, JobComparison)
            # Verify _generate was called (meaning it didn't raise before getting there)
            mock_gen.assert_called_once()


# ---------------------------------------------------------------------------
# research_company()
# ---------------------------------------------------------------------------

class TestResearchCompany:
    @patch("analyzer._client")
    @patch("analyzer._generate")
    def test_returns_company_profile(self, mock_gen, mock_client):
        profile = CompanyProfile(
            culture_summary="Strong engineering culture, data-driven, high ownership.",
            work_style="Hybrid - 3 days in office, 2 remote.",
            typical_interview_format="4 rounds: recruiter screen, technical coding, system design, behavioral.",
            what_they_value=["Ownership", "Technical depth", "Clear communication", "Bias for action"],
            red_flags=["High performance bar - demanding environment.", "Promotion can be slow."],
            prep_tips=[
                "Prepare STAR answers for behavioral questions.",
                "Review distributed systems design basics.",
                "Study the company's engineering blog before the interview.",
            ],
        )
        mock_gen.return_value = _make_response(profile)
        result = research_company("Google", "Senior Software Engineer")
        assert isinstance(result, CompanyProfile)
        assert result.work_style == "Hybrid - 3 days in office, 2 remote."
        assert len(result.what_they_value) == 4

    @patch("analyzer._client")
    @patch("analyzer._generate")
    def test_works_without_role(self, mock_gen, mock_client):
        profile = CompanyProfile(
            culture_summary="Fast-paced startup environment.",
            work_style="Remote-first.",
            typical_interview_format="3 rounds: intro call, technical, founder interview.",
            what_they_value=["Autonomy", "Speed"],
            red_flags=["Early-stage uncertainty."],
            prep_tips=["Research their product deeply."],
        )
        mock_gen.return_value = _make_response(profile)
        result = research_company("Acme Corp")
        assert isinstance(result, CompanyProfile)

    def test_raises_on_empty_company_name(self):
        with pytest.raises(AnalyzerError, match="company name"):
            research_company("")

    def test_raises_on_whitespace_company_name(self):
        with pytest.raises(AnalyzerError, match="company name"):
            research_company("   ")
