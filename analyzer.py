"""Core analysis logic: compares a resume against a job description using Google Gemini.

Returns a validated `Analysis` object (Pydantic) describing fit score, keyword
gaps, tailored bullet rewrites, and ATS tips. Also generates cover letters.
Kept UI-agnostic so it can be reused from Streamlit, a CLI, or tests.
Uses Gemini's free tier (no credit card needed).
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import List, NoReturn

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, Field

# Server-side record of every model call: schema, attempt, latency, outcome. Never the resume or job text.
log = logging.getLogger("resume_job_fit_ai.analyzer")

load_dotenv()

# Free-tier friendly default. gemini-2.5-flash-lite is reliable on the free tier; the heavier
# gemini-2.5-flash can return 503s under load. Override with GEMINI_MODEL if you prefer.
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
MAX_INPUT_CHARS = 8000  # guard against runaway usage; we warn rather than truncate
_MAX_RETRIES = 3        # auto-retry on transient 5xx / 429s before surfacing an error


class AnalyzerError(Exception):
    """User-facing error the UI can display verbatim."""


# --- Output schemas ----------------------------------------------------------

class BulletRewrite(BaseModel):
    original: str = Field(description="A weak bullet taken from the resume.")
    improved: str = Field(description="A stronger, job-tailored rewrite, still truthful to the resume.")


class Analysis(BaseModel):
    score: int = Field(description="Overall fit score from 0 to 100.")
    verdict: str = Field(description="One-line honest summary of the fit.")
    salary_range: str = Field(default="", description="Estimated market salary range for this role (e.g. '$90k–$120k, US remote'). Base the estimate on the job title, required skills, and seniority level. If location is unspecified, assume US market.")
    matched_keywords: List[str] = Field(description="Important skills/terms the resume already covers.")
    missing_keywords: List[str] = Field(description="Important skills/terms from the job the resume is missing.")
    bullet_rewrites: List[BulletRewrite] = Field(description="2-4 tailored rewrites of real resume bullets.")
    summary: str = Field(description="2-4 sentences of concrete advice to improve this application.")
    ats_tips: List[str] = Field(description="Specific applicant-tracking-system tips (exact phrases to add, etc.).")


class CoverLetter(BaseModel):
    opening: str = Field(description="Opening paragraph: hook + specific role + why this company.")
    body: str = Field(description="Middle paragraph: 2-3 concrete skills/projects from the resume that directly match the job requirements.")
    closing: str = Field(description="Closing paragraph: enthusiasm, call to action, professional sign-off.")


class InterviewQuestion(BaseModel):
    question: str = Field(description="A high-probability interview question for this specific role and candidate.")
    why_asked: str = Field(description="The underlying concern or quality the interviewer is probing.")
    tip: str = Field(description="One concrete, actionable tip for answering well, grounded in the candidate's actual experience.")


class InterviewPrep(BaseModel):
    questions: List[InterviewQuestion] = Field(description="5-7 tailored interview questions for this role and resume.")
    opening_tip: str = Field(description="One key piece of advice for the overall interview approach given this candidate's background.")


class Resource(BaseModel):
    name: str = Field(description="Name of the specific course, certification, or project.")
    provider: str = Field(description="Who offers it - e.g. Coursera, Google, GitHub, LinkedIn Learning.")
    type: str = Field(description="One of: Course, Certification, Project, Book, Tutorial.")


class SkillGap(BaseModel):
    skill: str = Field(description="The missing skill or technology.")
    importance: str = Field(description="High, Medium, or Low - how critical this skill is for the target role.")
    how_to_learn: str = Field(description="Concrete 1-2 sentence advice on learning this skill, given the candidate's existing background.")
    resources: List[Resource] = Field(description="2-3 specific resources to acquire this skill.")


class SkillsRoadmap(BaseModel):
    gaps: List[SkillGap] = Field(description="Key skill gaps in priority order - most important first.")
    timeline: str = Field(description="Realistic estimate of how long to close the top gaps given this candidate's background.")
    quick_wins: List[str] = Field(description="2-3 things the candidate can do this week to immediately strengthen their profile.")


class LinkedInProfile(BaseModel):
    headline: str = Field(description="Optimized LinkedIn headline (max 220 characters) - keyword-rich, highlights the candidate's unique value for this type of role.")
    about: str = Field(description="3-4 paragraph LinkedIn About section in first person - achievement-focused, authentic to the resume, ends with a call to action.")
    skills_to_add: List[str] = Field(description="Top 8-10 LinkedIn skill keywords to add for the target role.")
    profile_tips: List[str] = Field(description="3-5 specific, actionable tips to improve this candidate's LinkedIn profile for the target role.")


class ResumeHealth(BaseModel):
    overall_score: int = Field(description="Overall resume quality score 0-100.")
    writing_score: int = Field(description="Clarity, active voice, and conciseness score 0-100.")
    quantification_score: int = Field(description="How well bullets are backed by numbers and outcomes, 0-100.")
    verb_strength_score: int = Field(description="Strength and variety of action verbs, 0-100.")
    length_assessment: str = Field(description="E.g. 'Ideal (1 page)', 'Too long (3 pages - aim for 1–2)', 'Too short (less than half a page)'.")
    top_issues: List[str] = Field(description="3-5 most important problems with the resume - specific and observable.")
    quick_fixes: List[str] = Field(description="3-5 concrete changes the candidate can make today to improve the resume.")


class EmailTemplates(BaseModel):
    follow_up: str = Field(description="Follow-up email to send 1 week after applying with no response. Professional, concise, re-expresses interest and asks for a status update. 3-4 sentences max.")
    thank_you: str = Field(description="Thank-you email to send within 24 hours after an interview. Warm, specific - references something concrete discussed in the interview. 3-4 sentences max.")
    rejection_response: str = Field(description="Professional, gracious reply to a rejection email. Keeps the door open for future opportunities and leaves a positive impression. 3-4 sentences max.")


class CompanyProfile(BaseModel):
    culture_summary: str = Field(description="2-3 sentence summary of the company's culture and work environment based on public knowledge. If the company is obscure, note that and give industry-level context.")
    work_style: str = Field(description="Work style - 'Remote', 'Hybrid', or 'Onsite', with any known details about the company's policy.")
    typical_interview_format: str = Field(description="Typical interview process for this company and role - number of rounds, question styles, known practices.")
    what_they_value: List[str] = Field(description="4-6 qualities, skills, or traits this company consistently looks for in candidates.")
    red_flags: List[str] = Field(description="2-4 honest caution points - known challenges, culture fit concerns, or role-specific pressures a candidate should be aware of.")
    prep_tips: List[str] = Field(description="4-6 specific, actionable prep tips tailored to this company and role.")


class JobMatch(BaseModel):
    job_number: int = Field(description="Which job this is (1, 2, or 3).")
    job_title: str = Field(description="The job title extracted from the job description.")
    score: int = Field(description="Fit score 0-100 for this specific job.")
    top_strengths: List[str] = Field(description="2-3 resume strengths that directly match this job's requirements.")
    top_gaps: List[str] = Field(description="2-3 most important skills missing for this job.")
    verdict: str = Field(description="One sentence honest summary of fit for this role.")


class JobComparison(BaseModel):
    matches: List[JobMatch] = Field(description="One entry per job, ranked best-fit first.")
    recommended_job: int = Field(description="Job number (1, 2, or 3) this resume is the best fit for overall.")
    recommendation_reason: str = Field(description="2-3 sentences explaining why this job is the best match given the resume's actual strengths.")
    apply_order: List[int] = Field(description="Suggested order to apply (job numbers, best fit first).")


# --- Prompts -----------------------------------------------------------------

_ANALYSIS_SYSTEM = (
    "You are a senior technical recruiter and ATS (applicant tracking system) screening expert. "
    "You assess how well a resume fits a specific job. You are specific, honest, and constructive. "
    "Critically: you NEVER invent experience, skills, or metrics the candidate does not have. "
    "Bullet rewrites must stay truthful to the original resume - improve clarity, impact, and keyword "
    "alignment, and where a real number is unknown, use a clear placeholder like [X] rather than inventing one. "
    "You also estimate realistic market salary ranges based on the role title, required skills, and seniority "
    "signals in the job description - assume US market if no location is specified."
)

_COVER_LETTER_TONE = {
    "Professional": "Use a formal, polished tone - confident but restrained. No exclamation marks.",
    "Warm & Enthusiastic": "Use a warm, genuine tone - show authentic excitement for the role without being over-the-top.",
    "Bold & Direct": "Use a punchy, confident tone - lead with value, cut all filler, make every sentence earn its place.",
}


def _cover_letter_system(tone: str) -> str:
    instruction = _COVER_LETTER_TONE.get(tone, _COVER_LETTER_TONE["Professional"])
    return (
        "You are a professional career coach writing tailored cover letters. "
        "You write in first-person from the candidate's perspective. "
        "You NEVER fabricate experience, skills, or projects not present in the resume. "
        "Keep each paragraph concise and specific - no filler phrases like 'I am excited to apply'. "
        f"Tone: {instruction}"
    )


def _build_analysis_prompt(resume: str, job: str) -> str:
    return (
        "Analyze how well the following resume fits the job description.\n\n"
        "=== JOB DESCRIPTION ===\n"
        f"{job}\n\n"
        "=== RESUME ===\n"
        f"{resume}\n\n"
        "Score the fit 0-100. List the most important matched and missing keywords/skills. "
        "Rewrite 2-4 of the candidate's actual resume bullets to better target this job (truthfully). "
        "Give a short, concrete summary of how to improve the application and specific ATS tips. "
        "Estimate the realistic market salary range for this role based on the job title, required skills, and seniority level."
    )


_INTERVIEW_SYSTEM = (
    "You are a senior hiring manager and interview coach who has conducted thousands of technical interviews. "
    "You generate highly specific, realistic interview questions based on a candidate's actual resume and the job they are applying for. "
    "Questions must reflect real gaps and strengths - never generic filler like 'tell me about yourself' unless it is genuinely the most important question. "
    "Tips must be grounded in the candidate's real experience, not generic advice."
)

_ROADMAP_SYSTEM = (
    "You are a technical career coach who builds specific, actionable learning roadmaps. "
    "You recommend real, named resources (actual courses, certifications, projects) - never vague advice like 'learn Python'. "
    "Prioritize the gaps that will most improve the candidate's chances for this specific role. "
    "Never invent skills the candidate already has. Stay honest about what is missing."
)

_LINKEDIN_SYSTEM = (
    "You are a LinkedIn profile optimization expert who has helped thousands of candidates attract recruiter attention. "
    "You write compelling, authentic LinkedIn content grounded only in the candidate's actual experience. "
    "You NEVER fabricate skills, projects, or achievements not present in the resume. "
    "You know exactly which keywords recruiters and LinkedIn's algorithm surface - and you apply that knowledge concretely."
)

_RESUME_HEALTH_SYSTEM = (
    "You are a professional resume coach with 20 years of experience reviewing resumes across industries. "
    "You evaluate resumes on their own merit - writing quality, impact, clarity, and ATS-readiness - "
    "without comparing to any specific job. You are specific and direct: no vague praise, no invented issues. "
    "All feedback is grounded entirely in what you can observe in the resume text itself."
)


def _build_resume_health_prompt(resume: str) -> str:
    return (
        "Evaluate the quality of this resume as a standalone document.\n\n"
        "=== RESUME ===\n"
        f"{resume}\n\n"
        "Score it 0-100 overall, then score these three dimensions independently:\n"
        "- writing_score: clarity, active voice, no jargon, concise bullets\n"
        "- quantification_score: percentage of bullets backed by real numbers or measurable outcomes\n"
        "- verb_strength_score: variety and impact of action verbs (avoid 'responsible for', 'helped', 'worked on')\n"
        "Assess the page length. Then identify the 3-5 most important specific issues "
        "and give 3-5 concrete quick fixes the candidate can implement today."
    )


_EMAIL_SYSTEM = (
    "You are a professional career coach who writes concise, high-impact job-search emails. "
    "Every email you write is grounded in the candidate's actual resume and the specific role - "
    "no generic filler. Emails should be 3-4 sentences: direct, warm, and professional. "
    "Never fabricate details not present in the resume."
)


def _build_email_prompt(resume: str, job: str) -> str:
    return (
        "Write three short, professional job-search emails for this candidate applying to this role.\n\n"
        "=== JOB DESCRIPTION ===\n"
        f"{job}\n\n"
        "=== CANDIDATE RESUME ===\n"
        f"{resume}\n\n"
        "Write:\n"
        "1. follow_up - sent 1 week after applying with no response; politely asks for a status update\n"
        "2. thank_you - sent within 24h of an interview; references at least one specific topic likely "
        "discussed given the role and resume\n"
        "3. rejection_response - a gracious, door-open reply to a rejection; professional and memorable\n"
        "Each email: 3-4 sentences, no subject line, no salutation boilerplate - body only."
    )


_COMPARISON_SYSTEM = (
    "You are a senior technical recruiter who has reviewed thousands of applications. "
    "You compare a single resume against multiple job descriptions and give a clear, honest ranking. "
    "You extract the actual job title from each job description. "
    "Scores are relative and calibrated - if a resume fits all jobs well, scores should still differentiate them. "
    "Never invent experience the candidate doesn't have. Be direct about gaps."
)

_COMPANY_SYSTEM = (
    "You are a career coach who has helped hundreds of candidates prepare for interviews at companies of all sizes. "
    "You provide honest, research-backed profiles - culture, interview format, and what a company values - "
    "drawn from publicly available knowledge. Be direct about both positives and concerns. "
    "If the company is not widely known or you have limited information, say so clearly in the culture_summary "
    "rather than fabricating details. Focus on what genuinely helps the candidate prepare."
)


def _build_cover_letter_prompt(resume: str, job: str) -> str:
    return (
        "Write a concise, tailored cover letter for this candidate applying to this specific job.\n\n"
        "=== JOB DESCRIPTION ===\n"
        f"{job}\n\n"
        "=== CANDIDATE RESUME ===\n"
        f"{resume}\n\n"
        "Rules:\n"
        "- Three paragraphs: opening, body (skills match), closing.\n"
        "- Only reference projects and skills that actually appear in the resume.\n"
        "- Be specific and concrete - reference the job title and at least two requirements.\n"
        "- No generic filler. No invented metrics. Placeholders like [Company Name] are fine."
    )


def _build_interview_prompt(resume: str, job: str) -> str:
    return (
        "Generate tailored interview preparation for this candidate applying to this specific job.\n\n"
        "=== JOB DESCRIPTION ===\n"
        f"{job}\n\n"
        "=== CANDIDATE RESUME ===\n"
        f"{resume}\n\n"
        "Produce 5-7 high-probability interview questions for this exact role and candidate. "
        "For each question explain why it will be asked and give one specific, actionable tip based on the candidate's real background. "
        "Include a mix of: technical/skills questions targeting gaps, behavioral questions targeting the role's key challenges, "
        "and questions about the candidate's strongest relevant projects."
    )


def _build_roadmap_prompt(resume: str, job: str) -> str:
    return (
        "Build a concrete skills gap roadmap for this candidate targeting this job.\n\n"
        "=== JOB DESCRIPTION ===\n"
        f"{job}\n\n"
        "=== CANDIDATE RESUME ===\n"
        f"{resume}\n\n"
        "Identify the most important missing skills. For each gap, rate its importance (High/Medium/Low) for this specific role, "
        "give concrete advice on how to learn it given the candidate's existing background, "
        "and recommend 2-3 real, named resources (specific course names and providers, real certifications, or concrete project ideas). "
        "Order gaps by priority. Include 2-3 quick wins the candidate can do this week."
    )


def _build_linkedin_prompt(resume: str, job: str) -> str:
    return (
        "Optimize this candidate's LinkedIn profile to appeal to recruiters for the type of role described.\n\n"
        "=== TARGET ROLE ===\n"
        f"{job}\n\n"
        "=== CANDIDATE RESUME ===\n"
        f"{resume}\n\n"
        "Produce:\n"
        "1. An optimized LinkedIn headline (max 220 chars) - specific, keyword-rich, value-focused\n"
        "2. A 3-4 paragraph LinkedIn About section in first-person - start with a hook, include concrete achievements, "
        "end with what opportunities the candidate is open to\n"
        "3. Top 8-10 skill keywords to add to their LinkedIn Skills section for this target role\n"
        "4. 3-5 specific, actionable tips to strengthen this candidate's LinkedIn profile for recruiters in this field"
    )


def _build_company_prompt(company_name: str, role: str) -> str:
    role_context = f"for the role of **{role}**" if role.strip() else "for a general role there"
    return (
        f"Research the company '{company_name}' and help a job candidate prepare {role_context}.\n\n"
        "Provide:\n"
        "1. A culture summary - what it's actually like to work there, based on public knowledge\n"
        "2. Work style (Remote / Hybrid / Onsite) with any known company policy details\n"
        "3. Typical interview process - how many rounds, what types of questions, any known quirks\n"
        "4. Qualities and traits this company consistently values in candidates (be specific)\n"
        "5. Honest red flags or caution points - pressure, culture challenges, known concerns\n"
        "6. Specific prep tips for a candidate interviewing at this company for this role\n\n"
        "If this is a smaller or less-known company, acknowledge limited public data in the culture_summary "
        "and give thoughtful advice based on company size, industry, and role type."
    )


def _build_comparison_prompt(resume: str, jobs: List[str]) -> str:
    jobs_block = "\n\n".join(
        f"=== JOB {i+1} ===\n{job}" for i, job in enumerate(jobs)
    )
    return (
        f"Compare this resume against {len(jobs)} job descriptions and rank the fit.\n\n"
        "=== RESUME ===\n"
        f"{resume}\n\n"
        f"{jobs_block}\n\n"
        "For each job:\n"
        "- Extract the actual job title from the description.\n"
        "- Score fit 0-100 (be calibrated - scores should differentiate even if all fit well).\n"
        "- List 2-3 resume strengths that directly match that job's requirements.\n"
        "- List 2-3 most important gaps for that job.\n"
        "- Write one honest verdict sentence.\n\n"
        "Then rank them best-fit first, name the single best match, explain why in 2-3 sentences, "
        "and give a suggested apply order (job numbers)."
    )


# --- Internal helpers --------------------------------------------------------

def _validate(resume: str, job: str) -> None:
    if not resume.strip() or not job.strip():
        raise AnalyzerError("Please paste both a resume and a job description before analyzing.")
    if len(resume) > MAX_INPUT_CHARS or len(job) > MAX_INPUT_CHARS:
        raise AnalyzerError(
            f"Inputs are too long (limit {MAX_INPUT_CHARS:,} characters each). "
            "Trim to the most relevant sections and try again."
        )


def _client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise AnalyzerError(
            "No GEMINI_API_KEY found. Create a FREE key (no credit card needed) at "
            "https://aistudio.google.com/apikey and add it to a .env file as GEMINI_API_KEY=your-key-here."
        )
    return genai.Client(api_key=api_key)


def _generate(client: genai.Client, prompt: str, system: str, schema) -> object:
    """Call Gemini with structured output and auto-retry on transient 5xx / 429s."""
    last_err: Exception | None = None
    name = getattr(schema, "__name__", str(schema))
    for attempt in range(_MAX_RETRIES):
        started = time.perf_counter()
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.3,
                ),
            )
            log.info("gemini ok schema=%s attempt=%d ms=%d", name, attempt + 1, (time.perf_counter() - started) * 1000)
            return response
        except genai_errors.ClientError as exc:
            if getattr(exc, "code", None) != 429:
                raise  # non-429 client errors are not transient
            log.warning("gemini 429 schema=%s attempt=%d, retrying", name, attempt + 1)
            last_err = exc
            if attempt < _MAX_RETRIES - 1:
                time.sleep(4 * (attempt + 1))  # 4s, 8s before final attempt
        except genai_errors.ServerError as exc:
            log.warning("gemini %s schema=%s attempt=%d, retrying", getattr(exc, "code", "5xx"), name, attempt + 1)
            last_err = exc
            if attempt < _MAX_RETRIES - 1:
                time.sleep(4 * (attempt + 1))
    raise last_err  # type: ignore[misc]


def _handle_api_error(exc: Exception) -> NoReturn:
    """Translate SDK exceptions into user-friendly AnalyzerErrors."""
    # the visitor sees a friendly message; the log keeps the real cause
    log.error("gemini failed: %s code=%s %s", type(exc).__name__, getattr(exc, "code", None), getattr(exc, "message", exc))
    if isinstance(exc, genai_errors.ClientError):
        msg = str(getattr(exc, "message", "") or exc).lower()
        code = getattr(exc, "code", None)
        if code in (401, 403) or any(t in msg for t in ("api key", "api_key", "unauthenticated", "permission")):
            raise AnalyzerError(
                "Your GEMINI_API_KEY looks invalid. Get a free key at "
                "https://aistudio.google.com/apikey and check your .env file."
            )
        if code == 429 or any(t in msg for t in ("quota", "rate", "resource_exhausted")):
            raise AnalyzerError("Hit the free-tier rate limit. Wait a minute and try again.")
        raise AnalyzerError(f"The Gemini API rejected the request: {getattr(exc, 'message', exc)}")
    if isinstance(exc, genai_errors.ServerError):
        raise AnalyzerError("Gemini is unavailable right now. Please try again in a moment.")
    raise AnalyzerError(f"Gemini API error: {getattr(exc, 'message', exc)}")


def _parse_from_text(text: str | None, schema: type) -> object:
    """Defensive fallback: extract the first JSON object from raw text."""
    log.warning("structured output missing, parsing %s from raw text", getattr(schema, "__name__", schema))
    if not text:
        raise AnalyzerError("The model returned an empty response. Please try again.")
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise AnalyzerError("Could not read the response from the model. Please try again.")
    try:
        return schema(**json.loads(text[start : end + 1]))
    except (json.JSONDecodeError, ValueError):
        raise AnalyzerError("The model response was malformed. Please try again.")


# --- Public API --------------------------------------------------------------

def analyze(resume: str, job: str) -> Analysis:
    """Compare resume against job and return a validated Analysis.

    Raises AnalyzerError with a friendly message on any expected failure.
    Automatically retries up to 3 times on transient server errors.
    """
    _validate(resume, job)
    client = _client()
    try:
        response = _generate(client, _build_analysis_prompt(resume, job), _ANALYSIS_SYSTEM, Analysis)
        if isinstance(response.parsed, Analysis):
            return response.parsed
        return _parse_from_text(response.text, Analysis)  # type: ignore[arg-type]
    except AnalyzerError:
        raise
    except Exception as exc:
        raise _handle_api_error(exc)


def generate_cover_letter(resume: str, job: str, tone: str = "Professional") -> CoverLetter:
    """Generate a tailored cover letter for the given resume + job.

    tone: one of 'Professional', 'Warm & Enthusiastic', 'Bold & Direct'.
    """
    _validate(resume, job)
    client = _client()
    try:
        response = _generate(client, _build_cover_letter_prompt(resume, job), _cover_letter_system(tone), CoverLetter)
        if isinstance(response.parsed, CoverLetter):
            return response.parsed
        return _parse_from_text(response.text, CoverLetter)  # type: ignore[arg-type]
    except AnalyzerError:
        raise
    except Exception as exc:
        raise _handle_api_error(exc)


def generate_interview_prep(resume: str, job: str) -> InterviewPrep:
    """Generate tailored interview questions and tips for the given resume + job."""
    _validate(resume, job)
    client = _client()
    try:
        response = _generate(client, _build_interview_prompt(resume, job), _INTERVIEW_SYSTEM, InterviewPrep)
        if isinstance(response.parsed, InterviewPrep):
            return response.parsed
        return _parse_from_text(response.text, InterviewPrep)  # type: ignore[arg-type]
    except AnalyzerError:
        raise
    except Exception as exc:
        raise _handle_api_error(exc)


def generate_skills_roadmap(resume: str, job: str) -> SkillsRoadmap:
    """Generate a prioritized skills gap roadmap for the given resume + job."""
    _validate(resume, job)
    client = _client()
    try:
        response = _generate(client, _build_roadmap_prompt(resume, job), _ROADMAP_SYSTEM, SkillsRoadmap)
        if isinstance(response.parsed, SkillsRoadmap):
            return response.parsed
        return _parse_from_text(response.text, SkillsRoadmap)  # type: ignore[arg-type]
    except AnalyzerError:
        raise
    except Exception as exc:
        raise _handle_api_error(exc)


def generate_linkedin_profile(resume: str, job: str) -> LinkedInProfile:
    """Generate LinkedIn headline, About section, and profile tips for the given resume + job."""
    _validate(resume, job)
    client = _client()
    try:
        response = _generate(client, _build_linkedin_prompt(resume, job), _LINKEDIN_SYSTEM, LinkedInProfile)
        if isinstance(response.parsed, LinkedInProfile):
            return response.parsed
        return _parse_from_text(response.text, LinkedInProfile)  # type: ignore[arg-type]
    except AnalyzerError:
        raise
    except Exception as exc:
        raise _handle_api_error(exc)


def analyze_resume_health(resume: str) -> ResumeHealth:
    """Evaluate the resume standalone - no job description needed."""
    if not resume.strip():
        raise AnalyzerError("Please paste your resume before checking its health.")
    if len(resume) > MAX_INPUT_CHARS:
        raise AnalyzerError(
            f"Resume is too long (limit {MAX_INPUT_CHARS:,} characters). "
            "Trim to the most relevant sections and try again."
        )
    client = _client()
    try:
        response = _generate(client, _build_resume_health_prompt(resume), _RESUME_HEALTH_SYSTEM, ResumeHealth)
        if isinstance(response.parsed, ResumeHealth):
            return response.parsed
        return _parse_from_text(response.text, ResumeHealth)  # type: ignore[arg-type]
    except AnalyzerError:
        raise
    except Exception as exc:
        raise _handle_api_error(exc)


def generate_email_templates(resume: str, job: str) -> EmailTemplates:
    """Generate follow-up, thank-you, and rejection-response email templates."""
    _validate(resume, job)
    client = _client()
    try:
        response = _generate(client, _build_email_prompt(resume, job), _EMAIL_SYSTEM, EmailTemplates)
        if isinstance(response.parsed, EmailTemplates):
            return response.parsed
        return _parse_from_text(response.text, EmailTemplates)  # type: ignore[arg-type]
    except AnalyzerError:
        raise
    except Exception as exc:
        raise _handle_api_error(exc)


def research_company(company_name: str, role: str = "") -> CompanyProfile:
    """Research a company and return culture, interview format, and prep tips."""
    if not company_name.strip():
        raise AnalyzerError("Please enter a company name to research.")
    if len(company_name) > 200:
        raise AnalyzerError("Company name is too long (200 character limit).")
    client = _client()
    try:
        response = _generate(client, _build_company_prompt(company_name, role), _COMPANY_SYSTEM, CompanyProfile)
        if isinstance(response.parsed, CompanyProfile):
            return response.parsed
        return _parse_from_text(response.text, CompanyProfile)  # type: ignore[arg-type]
    except AnalyzerError:
        raise
    except Exception as exc:
        raise _handle_api_error(exc)


def compare_jobs(resume: str, jobs: List[str]) -> JobComparison:
    """Compare one resume against 2-3 job descriptions and return a ranked JobComparison.

    `jobs` must contain 2 or 3 non-empty job description strings.
    """
    if not resume.strip():
        raise AnalyzerError("Please paste your resume before comparing jobs.")
    jobs = [j for j in jobs if j.strip()]
    if len(jobs) < 2:
        raise AnalyzerError("Paste at least 2 job descriptions to compare.")
    if len(jobs) > 3:
        jobs = jobs[:3]
    if len(resume) > MAX_INPUT_CHARS:
        raise AnalyzerError(
            f"Resume is too long (limit {MAX_INPUT_CHARS:,} characters). "
            "Trim to the most relevant sections and try again."
        )
    for i, j in enumerate(jobs, 1):
        if len(j) > MAX_INPUT_CHARS:
            raise AnalyzerError(
                f"Job {i} is too long (limit {MAX_INPUT_CHARS:,} characters). "
                "Trim and try again."
            )
    client = _client()
    try:
        response = _generate(
            client, _build_comparison_prompt(resume, jobs), _COMPARISON_SYSTEM, JobComparison
        )
        if isinstance(response.parsed, JobComparison):
            return response.parsed
        return _parse_from_text(response.text, JobComparison)  # type: ignore[arg-type]
    except AnalyzerError:
        raise
    except Exception as exc:
        raise _handle_api_error(exc)
