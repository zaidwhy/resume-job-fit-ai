# Handoff: Upgrade Plan Session - 2026-06-17

## ✅ Progress as of 2026-06-17 (same session, continued)

**8 of 10 planned features shipped** across 4 commits:

| Commit | Features |
|---|---|
| `f4ee7f6` | 1A Salary Range + 2A Bullet Diff Viewer |
| `b0c3121` | 1B Score Trend Chart + 2C Cover Letter Tone |
| `26e4b24` | 2B Analytics Dashboard + 3B Email Templates |
| `(current)` | 2D Resume Health Tab |

**App is now:** 3-page Streamlit app - Main (**7 tabs**) + Compare Jobs + Job Tracker

**Remaining from plan:** 3A Company Research Page, 3C Tailored Resume Export

---

## What This Session Did (original)

Read and analyzed all existing documentation (README, CLAUDE.md, all handoffs, all build logs)
and the full source code. No code was changed. This session produced a structured upgrade roadmap
to take the app from "feature-complete MVP" to "flagship portfolio project".

**App state entering this session:**
- Live at https://resume-job-fit-ai.streamlit.app
- 3-page Streamlit app: Main (5 tabs) + Compare Jobs + Job Tracker
- 26 unit tests, CI passing, SQLite tracker, DOCX export - all shipped

---

## Full Upgrade Roadmap

### Phase 1 - Quick Wins (Start Here)

#### 1A. Salary Range Estimator
**Effort: ~45 min | Files: `analyzer.py`, `app.py`**

- Add `salary_range: str` to the `Analysis` Pydantic schema in `analyzer.py`.
- Update `_ANALYSIS_SYSTEM` prompt to ask Gemini to estimate salary based on role/JD context.
- Render as an info box in the Analysis tab below the score.
- Include in `.txt` and `.docx` exports (`analysis_as_text()` and `export_docx()`).
- No new AI call - Gemini already sees the full JD; this is one new field.

#### 1B. Score Trend Chart in Job Tracker
**Effort: ~1 hr | Files: `db.py`, `pages/2_Job_Tracker.py`**

- Add `get_score_history()` to `db.py` returning `[{saved_on, score, job_title}]` ordered by date.
- In `pages/2_Job_Tracker.py`, add `st.line_chart()` above the stats row.
- Only show when 3+ saved entries (fewer is noise).
- Gives users a visual signal: "is my resume improving over applications?"

#### 1C. Load Sample Data Button
**Effort: ~30 min | Files: `app.py`**

- Add "Try with sample data →" button above the two input columns.
- On click: read `sample/sample_resume.txt` and `sample/sample_job.txt` (already in repo),
  populate session state text areas, clear any previous results, call `st.rerun()`.
- Critical for demos and first-time visitors - eliminates all friction.

---

### Phase 2 - Core Feature Depth

#### 2A. Resume Diff Viewer (Accept/Reject Rewrites)
**Effort: ~1 hr | Files: `app.py`**

- Replace the current flat bullet rewrite list with a two-column card per `BulletRewrite`:
  - Left column: original text (muted/grey background)
  - Right column: AI rewrite (green left-border highlight)
- Add "Copy" button per rewrite (reuse `st.code()` pattern already in app).
- Add "Copy All Rewrites" button that assembles all rewrites into one block.
- No new AI calls - works entirely from existing `Analysis.bullet_rewrites`.

#### 2B. Application Analytics Dashboard
**Effort: ~1.5 hr | Files: `pages/2_Job_Tracker.py`**

- Add `st.expander("📊 Analytics", expanded=False)` above the application cards.
- Inside: pipeline funnel (Saved → Applied → Interviewing → Offer counts as horizontal bars),
  score distribution histogram, success rate percentage.
- All data comes from existing `get_stats()` return value - no db.py changes needed.

#### 2C. Cover Letter Tone Selector
**Effort: ~1 hr | Files: `analyzer.py`, `app.py`**

- Add `tone: str = "Professional"` parameter to `generate_cover_letter(resume, job, tone)`.
- Tone options: `Professional` | `Warm & Enthusiastic` | `Bold & Direct`.
- Inject tone into `_COVER_LETTER_SYSTEM` via f-string.
- In `app.py` Cover Letter tab: add `st.radio()` for tone selection before the generate button.
- Regenerate button clears `cover_letter` from session state and re-calls with new tone.

#### 2D. Resume Strength Analyzer (Standalone)
**Effort: ~2 hr | Files: `analyzer.py`, `app.py`**

- New Pydantic schema `ResumeHealth`:
  ```python
  overall_score: int          # 0-100
  writing_score: int          # clarity, active voice
  quantification_score: int   # % of bullets with numbers
  verb_strength_score: int    # strong action verbs
  length_assessment: str      # "Ideal (1 page)", "Too long", etc.
  top_issues: list[str]
  quick_fixes: list[str]
  ```
- New system prompt `_RESUME_HEALTH_SYSTEM`: resume coach, evaluates standalone (no job).
- New function `analyze_resume_health(resume) -> ResumeHealth` in `analyzer.py`.
- Add as 6th tab "Resume Health" in `app.py`.
- Renders sub-score bars + bulleted quick fixes.
- Test with `@patch("analyzer._generate")` mock (match existing test pattern).

---

### Phase 3 - New Pages / Big Features

#### 3A. Company Research Page
**Effort: ~2.5 hr | Files: `analyzer.py`, `pages/3_Company_Research.py` (new)**

- New Pydantic schema `CompanyProfile`:
  ```python
  culture_summary: str
  work_style: str             # "Remote", "Hybrid", "Onsite"
  typical_interview_format: str
  what_they_value: list[str]
  red_flags: list[str]
  prep_tips: list[str]
  ```
- New function `research_company(company_name, role) -> CompanyProfile` in `analyzer.py`.
- New page `pages/3_Company_Research.py`: text input for company name + optional role,
  "Research" button, structured output sections.
- Cross-link: in Interview Prep tab, add "Research this company →" link if company name known.

#### 3B. Email Templates Generator
**Effort: ~2 hr | Files: `analyzer.py`, `app.py`**

- New Pydantic schema `EmailTemplates`:
  ```python
  follow_up: str           # 1 week after applying, no response
  thank_you: str           # 24h after interview
  rejection_response: str  # professional, door-open tone
  ```
- New function `generate_email_templates(resume, job) -> EmailTemplates` in `analyzer.py`.
- Add as 7th tab "Emails" in `app.py`.
- Each email in `st.code()` block with copy button.
- Add to "Generate all sections" flow as optional step.

#### 3C. Tailored Resume Export
**Effort: ~2 hr | Files: `app.py`**

- New function `export_tailored_resume_docx(analysis) -> bytes` in `app.py`.
- Assembles a ready-to-submit resume `.docx` by substituting AI rewrites in place of original bullets.
- Sections: Contact Placeholder → Summary (from ATS tips) → Work Experience (with rewrites) → Skills Gap addressed.
- Add "Download Tailored Resume (.docx)" as a third download button alongside existing two.
- No new AI calls - remixes existing `Analysis` data.

---

## Execution Status

| # | Feature | Status |
|---|---|---|
| 1 | 1C - Load Sample Data | ✅ Was already shipped |
| 2 | 1A - Salary Range Estimator | ✅ Done (`f4ee7f6`) |
| 3 | 2A - Diff Viewer (Rewrites) | ✅ Done (`f4ee7f6`) |
| 4 | 1B - Score Trend Chart | ✅ Done (`b0c3121`) |
| 5 | 2C - Cover Letter Tone | ✅ Done (`b0c3121`) |
| 6 | 2B - Analytics Dashboard | ✅ Done (`26e4b24`) |
| 7 | 3B - Email Templates | ✅ Done (`26e4b24`) |
| 8 | 2D - Resume Health Tab | ✅ Done (current session) |
| 9 | 3C - Tailored Resume Export | ⬜ Next |
| 10 | 3A - Company Research Page | ⬜ Next |

---

## Key Technical Constraints (Always Respect)

- **Free tier only** - `gemini-2.5-flash-lite` for all calls; no paid services.
- **UI-agnostic core** - all new AI schemas + functions go in `analyzer.py` (no Streamlit imports there).
- **Test every new analyzer function** - mock `_generate` with `@patch("analyzer._generate")`, match pattern in `tests/test_analyzer.py`.
- **Auto-commit hooks fire on saves** - `git reset --soft HEAD~N` before every proper commit.
- **Input limits** - 8000 char per input; `_validate()` enforces this.
- **XSS** - wrap all Gemini-generated strings in `html.escape()` before `unsafe_allow_html=True`.

## How to Run Locally

```bash
cd C:\Users\Asus\projects\resume-job-fit-ai
venv\Scripts\activate
streamlit run app.py
```

Tests:
```bash
pytest tests/ -v
```

---

## What to Tell Claude at the Start of Next Session

> "Read handoffs/HANDOFF-UPGRADE-PLAN-2026-06-17.md and continue with the two remaining features: 3C (Tailored Resume Export) and 3A (Company Research Page). Run tests after each."
