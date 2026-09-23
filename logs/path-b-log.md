# Path B Build Log - 2026-06-16

## Goal
Make this a standout portfolio piece: multi-job comparison, DOCX export, tests + CI.

---

## Changes Made

### 1. Multi-job comparison

**`analyzer.py`**
- New schemas: `JobMatch` (job_number, job_title, score, top_strengths, top_gaps, verdict) and `JobComparison` (matches list ranked best-first, recommended_job, recommendation_reason, apply_order).
- `_COMPARISON_SYSTEM` prompt - senior recruiter persona, calibrated scoring, honest gap assessment.
- `_build_comparison_prompt(resume, jobs)` - builds a multi-job prompt with clearly labeled `=== JOB N ===` blocks.
- `compare_jobs(resume, jobs)` - validates inputs (min 2 jobs, max 3, char limits per job), calls `_generate()`, falls back to `_parse_from_text()`.

**`pages/1_Compare_Jobs.py`** (new Streamlit page)
- Three-column job description inputs (Job 1, Job 2, Job 3 optional).
- PDF upload + text area for resume (same UX as main page).
- Results: recommendation banner (`st.success`), apply order (`st.info`), per-job cards with score colored by value (green/amber/red), strengths vs gaps in two columns.
- Medal labels (🥇🥈🥉) derived from `apply_order` ranking.
- Full secrets shim so it works on Streamlit Cloud.

### 2. DOCX export

**`requirements.txt`** - added `python-docx>=1.1`.

**`app.py` - `export_docx()`**
- Builds a `python-docx` `Document` with proper heading hierarchy (H0 title, H1 sections, H2 subsections, H3 per item).
- Score rendered bold at Pt 18 centered.
- Bullet rewrites as Before/After bold-labelled paragraphs.
- ATS tips, quick wins, roadmap resources, LinkedIn skills all use `List Bullet` style.
- Page breaks between major sections (Cover Letter, Interview Prep, Roadmap, LinkedIn) for clean printing.
- Returns `bytes` from an in-memory `BytesIO` buffer - no temp files.

**`app.py` - download buttons**
- Replaced single `st.download_button` with a two-column row: **Download (.txt)** and **Download (.docx)** side by side.

### 3. Tests + GitHub Actions CI

**`tests/test_analyzer.py`** (new, 26 test cases)
- `TestValidate` - empty resume, empty job, oversized resume, oversized job, valid inputs.
- `TestParseFromText` - valid JSON, empty text, no JSON, malformed JSON, JSON wrapped in markdown fences.
- `TestAnalyze` - parsed result returned, fallback to `_parse_from_text`, empty input error.
- `TestGenerateCoverLetter` - returns `CoverLetter`, empty resume error.
- `TestGenerateInterviewPrep` - returns `InterviewPrep` with questions.
- `TestGenerateSkillsRoadmap` - returns `SkillsRoadmap` with gaps.
- `TestGenerateLinkedInProfile` - returns `LinkedInProfile`.
- `TestCompareJobs` - returns comparison, raises on 1 job, raises on empty resume, caps at 3 jobs.
- All Gemini calls mocked via `unittest.mock.patch` - tests run without a real API key.

**`.github/workflows/ci.yml`** (new)
- Runs on every push/PR to `main`.
- Ubuntu, Python 3.11, pip cache.
- Installs `requirements.txt` + `pytest`.
- Sets `GEMINI_API_KEY=dummy-key-for-tests` env var (never hits the real API - all mocked).
- `pytest tests/ -v --tb=short`.

**`requirements.txt`** - added `pytest>=8.0`.

**`README.md`** - added CI badge, updated "What it does" table, updated Roadmap.

---

## Decisions

| Decision | Reason |
|---|---|
| Multi-job comparison as a separate Streamlit page (`pages/`) | Keeps `app.py` focused; Streamlit's multi-page setup gives free sidebar navigation |
| `List[str] jobs` capped at 3 | A single Gemini prompt with 3 full JDs is ~20-24k chars - stays within free-tier context limit |
| DOCX via `python-docx` not `docxtpl` | Standard library, no template file needed, clean API for programmatic doc creation |
| Tests use `unittest.mock.patch`, not a full fixture | Lighter setup, no need for a test Gemini client or real API key in CI |
| `GEMINI_API_KEY=dummy-key-for-tests` in CI | `_client()` reads the env var and would raise without it - dummy value satisfies the check since all calls are mocked before reaching `_client()` |

---

## Files Modified / Created

| File | Change |
|------|--------|
| `analyzer.py` | Added `JobMatch`, `JobComparison` schemas; `_COMPARISON_SYSTEM`, `_build_comparison_prompt`, `compare_jobs` |
| `pages/1_Compare_Jobs.py` | New Streamlit page - full multi-job comparison UI |
| `app.py` | Added `export_docx()`; replaced single download button with .txt + .docx side-by-side |
| `requirements.txt` | Added `python-docx>=1.1`, `pytest>=8.0` |
| `tests/__init__.py` | New - makes tests/ a package |
| `tests/test_analyzer.py` | New - 26 unit tests, all Gemini mocked |
| `.github/workflows/ci.yml` | New - CI: Python 3.11, pytest on every push/PR |
| `README.md` | CI badge, updated feature table, updated roadmap |
