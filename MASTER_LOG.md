# Master Log - resume-job-fit-ai

**Project:** AI-powered resume ↔ job fit analyzer  
**Owner:** Zaid Ali Syed (sidzaid72@gmail.com · github.com/syzayd)  
**Live URL:** https://resume-job-fit-ai.streamlit.app  
**Total commits:** 28  
**Total unit tests:** 26 (all passing)  
**Log generated:** 2026-06-22

---

## Purpose

Dual-purpose project:
1. **Portfolio piece** - demonstrates AI engineering skill publicly on GitHub
2. **LinkedIn content engine** - "built in public" post material for building AI authority targeting recruiters and tech leads

Constraint throughout: **free-tier only** - no paid APIs, no credit cards.

---

## Tech Stack (final)

| Layer | Choice | Why |
|---|---|---|
| UI | Streamlit | Fastest path from Python to shareable web app |
| AI model | `gemini-2.5-flash-lite` via Google AI SDK | Only reliably-available free-tier Gemini model |
| Data validation | Pydantic schemas | Structured JSON output from Gemini |
| PDF parsing | pdfplumber | Extract resume text from uploaded PDFs |
| Word export | python-docx | DOCX download without paid services |
| Charts | Altair | Declarative, works inside Streamlit |
| Persistence | SQLite (local) | Zero-infra job tracker |
| CI | GitHub Actions | Pytest on every push/PR to main |
| Deploy | Streamlit Community Cloud | Free hosting, secrets via st.secrets |

---

## Chronological Build Log

---

### 2026-06-15 - Session 1: Foundation

#### Commit `8c40504` - Project scaffold
- Created `.env.example` documenting `GEMINI_API_KEY`
- Created `.gitignore` (excludes `.env`, `*.db`, `__pycache__`, etc.)
- Created `requirements.txt` with initial dependencies

#### Commit `531c24d` - Claude Sonnet analyzer (initial)
- `analyzer.py` created with Claude Sonnet as the AI backend
- Pydantic schemas defined for structured JSON output
- 131 lines; first working AI integration

#### Commit `0ca42d3` - Streamlit UI + sample loader
- `app.py` created (115 lines)
- Sample loader button to pre-fill inputs
- Results view showing fit score + keyword gaps
- `sample/sample_resume.txt` and `sample/sample_job.txt` added

#### Commit `5e88f43` - README
- Run instructions
- "What I learned" section

#### Commit `f6d72d4` - Placeholder screenshot in README

#### Commit `bf5bab8` - Better billing error message
- Clear "out of credits" message instead of raw API error when Claude quota exceeded

#### Commit `ba46291` - Switch from Claude to Google Gemini (free tier)
- Complete rewrite of `analyzer.py` AI backend
- Uses `gemini-2.0-flash` via Google AI SDK
- Pydantic schemas reused via Gemini `response_schema`
- **Reason:** Claude free tier ran out; Gemini is free with no credit card

#### Commit `e89bc6b` - Fix model to `gemini-2.5-flash-lite`
- `gemini-2.0-flash` had 0 free-tier quota in practice
- `gemini-2.5-flash` returned 503s under load
- `gemini-2.5-flash-lite` was the only reliably working free model
- Added `GEMINI_MODEL` env var for easy override

#### Commit `7e6ce54` - First live demo screenshot added to README

#### Commit `0011c6b` - Auto-retry on Gemini 503s
- Exponential backoff with up to 3 retry attempts
- Transient server errors no longer surface to user unless all retries fail

#### Commit `9de3492` - Cover letter tab + .txt download
- New "Cover Letter" tab in app
- Generates tailored 3-paragraph cover letter via Gemini
- "Download full analysis" button exports analysis + cover letter as `.txt`

#### Commit `e21d603` - Security fixes from code review
- **XSS fix:** HTML-escape `result.verdict` and keyword chip items before injecting into `unsafe_allow_html` HTML (Gemini output is user-influenced)
- **Retry 429s:** Widened `_generate()` retry loop to catch `ClientError` with code 429 (rate-limit hits were not retried)
- **Type safety:** Annotated `_handle_api_error` as `NoReturn` with explicit raises

#### Commit `a8ea8e7` - README formatting fixes

---

### 2026-06-16 - Session 2: Feature Expansion

#### Commit `9434fb4` - PDF upload + interview prep + skills roadmap
Three major features in one commit:

**PDF Upload**
- Added `pdfplumber>=0.11` dependency
- File uploader in the resume column
- Extracted text auto-fills the text area (still editable)
- Tracks uploaded filename in session state to avoid re-extracting on reruns

**Interview Prep tab (tab 3)**
- New `InterviewQuestion` + `InterviewPrep` Pydantic schemas in `analyzer.py`
- `generate_interview_prep()` - calls Gemini with hiring-manager system prompt
- Returns 5–7 tailored questions, why each is asked, and a concrete tip grounded in the candidate's actual resume
- Renders as bordered cards with importance context

**Skills Gap Roadmap tab (tab 4)**
- New `Resource`, `SkillGap`, `SkillsRoadmap` schemas
- `generate_skills_roadmap()` - gaps in priority order, each with importance rating, how-to-learn advice, 2–3 named resources (real courses/certs/projects with provider)
- Surfaces quick wins + estimated learning timeline
- Color-coded importance badges (High / Medium / Low)

All three features persist in session state, clear on re-analysis, included in `.txt` export.

#### Commit `6119e28` - README + session handoff
- README updated to reflect all 4 tabs, PDF upload, tech decisions
- `handoffs/HANDOFF-2026-06-16-2308.md` created (first session handoff document)

#### Commit `4e23454` - LinkedIn optimizer + copy UX + higher input limit
- **New tab 5:** LinkedIn Profile Optimizer
  - Optimized headline (max 220 chars)
  - Ready-to-paste About section
  - 8–10 skills to add
  - 3–5 actionable profile tips
  - All grounded in actual resume + target role
- **Copy-to-clipboard** expanders on Cover Letter and each Interview Prep card using `st.code` built-in copy button
- **`MAX_INPUT_CHARS`** bumped 6000 → 8000 to accommodate longer resumes and JDs
- LinkedIn output included in `.txt` download

#### Commit `2ef6f6f` - Path A: Streamlit Cloud deploy + Generate All button

**Streamlit Cloud support:**
- `.streamlit/config.toml` - indigo theme + headless server settings
- `.streamlit/secrets.toml.example` - documents Cloud secrets format
- `app.py` startup shim: injects `st.secrets` into `os.environ` so `analyzer.py` works on Cloud without coupling to Streamlit

**Generate All Sections button:**
- Single "Generate all sections ✨" button fires all 4 AI generators (cover letter, interview prep, skills roadmap, LinkedIn) in sequence
- `st.progress()` bar with per-section text shows what's generating
- Per-section errors are warnings (non-fatal) so others still run
- Button auto-hides once all sections are populated

#### Commit `0622ef0` - Path B: Multi-job comparison + DOCX export + tests + CI

**Multi-job comparison (`pages/1_Compare_Jobs.py` - new sidebar page):**
- New `JobMatch` + `JobComparison` Pydantic schemas in `analyzer.py`
- `compare_jobs()` accepts 2–3 JDs and returns a ranked comparison in one Gemini call: scores, strengths, gaps, recommended job, apply order
- 3-column JD inputs, scored cards, medal ranking, recommendation banner

**DOCX export:**
- `export_docx()` builds a formatted Word document with heading hierarchy, page breaks per section, bold labels, List Bullet styles for tips/gaps
- Download buttons now show `.txt` and `.docx` side by side
- `python-docx>=1.1` added to `requirements.txt`

**Tests:**
- `tests/test_analyzer.py` - 26 unit tests covering `_validate`, `_parse_from_text`, `analyze`, `generate_cover_letter`, `generate_interview_prep`, `generate_skills_roadmap`, `generate_linkedin_profile`, `compare_jobs`
- All Gemini calls mocked (no API key needed to run tests)

**CI:**
- `.github/workflows/ci.yml` - Python 3.11, pytest on every push/PR to `main`
- CI badge added to README

#### Commit `d1256b2` - Path C: SQLite job application tracker

**`db.py` (new file):**
- SQLite persistence layer - `applications` table (job_title, company, score, status, notes, saved_on)
- Functions: `init_db`, `save_application`, `update_status`, `update_notes`, `delete_application`, `get_all_applications`, `get_stats`, `export_csv`
- `job_tracker.db` is local-only (added to `.gitignore`)

**`pages/2_Job_Tracker.py` (new sidebar page):**
- Summary stats: total | avg score | applied | interviewing | offers
- Filter by status + sort options (newest / score high-low / low-high)
- Per-app cards: colored score, live status dropdown, notes input, delete button
- Export all applications as CSV download

**`app.py` changes:**
- "Save to tracker" form below download buttons (job title + company inputs)
- `tracker_saved` session state prevents double-saves
- Success message links to the Job Tracker sidebar page

#### Commit `58dce23` - Live demo URL added
- App deployed to https://resume-job-fit-ai.streamlit.app
- Prominent live link above badges in README
- `app.py` footer, `pages/1_Compare_Jobs.py` footer, `pages/2_Job_Tracker.py` footer all updated with "Live demo" + "GitHub" links

#### Commit `68266a0` - 3-page composite screenshot
- Replaced stale single-page screenshot with 1820×354 composite
- Shows all three live pages side-by-side with labelled colour bars: Main (indigo), Compare Jobs (blue), Job Tracker (green)
- Captured from live deployment

#### Commit `aa2cafa` - Marked deploy tasks complete
- `HANDOFF-PATH-C.md`: checked off deploy, badge URL, and screenshot tasks
- README roadmap: screenshot item marked `[x]`

#### Commit `82046f3` - Upgrade plan handoff (10-feature roadmap)
- `handoffs/HANDOFF-UPGRADE-PLAN-2026-06-17.md` created
- Documented 10 planned features across 3 phases for the next session:
  - **Phase 1 (quick wins):** salary range estimator, score trend chart, sample data button
  - **Phase 2 (core depth):** diff viewer, analytics dashboard, cover letter tone selector, resume health tab
  - **Phase 3 (new pages):** company research, email templates, tailored resume export

---

### 2026-06-17 - Session 3: 10-Feature Upgrade Sprint

All 10 features from the handoff roadmap shipped in a single session.

#### Commit `f4ee7f6` - Phase 1A + 2A: Salary range estimator + resume diff viewer

**Salary Range Estimator:**
- `salary_range` field added to `Analysis` Pydantic schema
- System prompt + analysis prompt updated to request market salary estimation from Gemini
- Renders as a pill badge below the fit score in the app
- Included in `.txt` and `.docx` exports

**Resume Diff Viewer:**
- Replaced flat bullet rewrite cards with side-by-side diff view
- Grey column = original bullet, Green column = AI rewrite
- Per-bullet copy expander + "Copy all rewrites" block at bottom

#### Commit `b0c3121` - Phase 1B + 2C: Score trend chart + cover letter tone selector

**Score Trend Chart:**
- `get_score_history()` added to `db.py` - returns saved_on/score/job_title ordered oldest-first for charting
- Altair line chart with dot markers and hover tooltips (role name + score + date) in Job Tracker page
- Shown when 3+ entries exist; nudge caption shown when fewer

**Cover Letter Tone Selector:**
- Converted `_COVER_LETTER_SYSTEM` constant to `_cover_letter_system(tone)` function in `analyzer.py`
- 3 tone variants: **Professional** / **Warm & Enthusiastic** / **Bold & Direct**
- `tone` param added to `generate_cover_letter()` with "Professional" default
- Tone radio selector in Cover Letter tab in `app.py`
- Button label changes to "Regenerate" when letter already exists
- Generate All passes the currently selected tone
- `cover_letter_tone` added to session state defaults

#### Commit `26e4b24` - Phase 2B + 3B: Analytics dashboard + email templates

**Analytics Dashboard (Job Tracker page):**
- Collapsible Analytics expander with:
  - Altair horizontal bar chart (per-status pipeline counts, greyed-out zeros)
  - Altair score distribution histogram
  - Offer-rate metric
- `get_all_applications()` called once and reused for both analytics and cards

**Email Templates Generator (new tab 6):**
- New `EmailTemplates` schema in `analyzer.py`: `follow_up`, `thank_you`, `rejection_response`
- `_EMAIL_SYSTEM` prompt + `_build_email_prompt()` function
- `generate_email_templates()` public function
- New "Emails" tab in `app.py` with `render_email_templates()` - 3 copyable text blocks
- `email_templates` added to session state, all clear/reset paths, Generate All, `.txt` export, `.docx` export

#### Commit `b01952e` - Phase 2D: Resume health tab

**Resume Health Analyzer:**
- New `ResumeHealth` Pydantic schema: `overall`, `writing`, `quantification`, `verb_strength` scores (0–100); `length_assessment`; `top_issues` list; `quick_fixes` list
- `_RESUME_HEALTH_SYSTEM` constant + `_build_resume_health_prompt()` function
- `analyze_resume_health(resume)` public function - resume-only analysis, no job description required

**UI in `app.py`:**
- `render_resume_health()` with score pill, 3-column sub-score breakdown with progress bars, issues vs. fixes side-by-side
- New 7th tab "Resume Health" with generate button
- Session state + all clear paths

All 22 unit tests passing after this commit.

---

### 2026-06-19 - Session 4: Phase 3 Completion

#### Commit `76b1338` - Phase 3A + 3C: Company research page + tailored resume export

**Company Research page (`pages/3_Company_Research.py` - new sidebar page):**
- New `CompanyProfile` Pydantic schema in `analyzer.py`
- `research_company()` function - culture summary, interview format, what they value, red flags, prep tips
- Page UI: company name + role inputs, structured output render, copy-all expander for prep tips
- Cross-link from Interview Prep tab pointing to Company Research page

**Tailored Resume Export:**
- `export_tailored_resume_docx()` function in `app.py`
- Standalone resume `.docx` with AI rewrites substituted in for original bullets
- ATS notes pre-filled in the document
- Third download button added ("Download tailored resume")

**Tests:**
- 4 new tests for `research_company()` added to `tests/test_analyzer.py`
- **Total: 26 unit tests, all passing**

**Docs:**
- README updated: all 10/10 features checked off
- Handoff documents updated to reflect complete status

---

## Feature Inventory (final state)

### Main app (`app.py`) - 7 tabs

| Tab | Feature |
|---|---|
| 1. Analyze Fit | Fit score + salary range pill + keyword gap chips + side-by-side diff viewer |
| 2. Cover Letter | Tone selector (Professional / Warm / Bold) + generated letter + regenerate button |
| 3. Interview Prep | 5–7 tailored questions with importance context + per-card copy |
| 4. Skills Roadmap | Prioritized skill gaps with resources, quick wins, learning timeline |
| 5. LinkedIn | Optimized headline + About section + skills list + profile tips |
| 6. Emails | Follow-up, thank-you, and rejection-response email templates |
| 7. Resume Health | Overall score + sub-scores (writing/quantification/verb strength) + issues + quick fixes |

### Sidebar pages

| Page | Feature |
|---|---|
| Compare Jobs (`pages/1_Compare_Jobs.py`) | Compare 2–3 job descriptions at once; ranked output with medal system |
| Job Tracker (`pages/2_Job_Tracker.py`) | SQLite-backed application tracker; status/notes editing; CSV export; score trend chart; pipeline analytics |
| Company Research (`pages/3_Company_Research.py`) | Company culture, interview format, red flags, prep tips via Gemini |

### Downloads

| Button | Output |
|---|---|
| Download full analysis (.txt) | All 7 tabs' output as plain text |
| Download full analysis (.docx) | Formatted Word document with heading hierarchy |
| Download tailored resume (.docx) | Resume with AI rewrites substituted in + ATS notes |

### Other features

- PDF upload (pdfplumber) with auto-fill of resume text area
- "Generate all sections ✨" button fires all generators in sequence with progress bar
- "Save to tracker" form on main page saves to SQLite job tracker
- Session state management - all outputs persist across tab switches; clear on re-analysis
- Auto-retry on Gemini 503/429 with exponential backoff (up to 3 attempts)
- XSS-safe HTML rendering (all Gemini output escaped before `unsafe_allow_html`)
- `MAX_INPUT_CHARS = 8000` per input field

---

## Files Created / Modified

```
app.py                                  # Main Streamlit app (7 tabs, 3 download buttons)
analyzer.py                             # All Gemini logic (9 public functions, Pydantic schemas)
db.py                                   # SQLite persistence layer
pages/
  1_Compare_Jobs.py                     # Multi-job comparison page
  2_Job_Tracker.py                      # Job application tracker page
  3_Company_Research.py                 # Company research page
tests/
  test_analyzer.py                      # 26 unit tests (all Gemini calls mocked)
.github/
  workflows/ci.yml                      # Pytest CI on every push to main
.streamlit/
  config.toml                           # Indigo theme + headless settings
  secrets.toml.example                  # Secrets format documentation
sample/
  sample_resume.txt                     # Sample resume for demo
  sample_job.txt                        # Sample job description for demo
handoffs/
  HANDOFF-2026-06-16-2308.md            # Session 2 handoff
  HANDOFF-PATH-A.md                     # Path A notes
  HANDOFF-PATH-C.md                     # Path C notes
  HANDOFF-UPGRADE-PLAN-2026-06-17.md   # 10-feature upgrade roadmap
requirements.txt                        # pdfplumber, python-docx, streamlit, google-generativeai, pydantic, altair
.env.example                            # GEMINI_API_KEY template
.gitignore                              # excludes .env, job_tracker.db, __pycache__, venv
README.md                               # Full feature table, live demo link, badges, roadmap
```

---

## Key Decisions & Dead Ends

| Decision | Reason |
|---|---|
| Switched Claude → Gemini | Claude free tier quota exhausted; Gemini is reliably free |
| `gemini-2.5-flash-lite` not `gemini-2.0-flash` or `gemini-2.5-flash` | 2.0-flash had 0 actual free quota; 2.5-flash 503'd under load; lite was the only stable option |
| SQLite over any hosted DB | Zero infra, no config, works on Streamlit Cloud with ephemeral note |
| Pydantic schemas for all Gemini responses | Ensures structured output; allows mocking in tests without real API calls |
| `MAX_INPUT_CHARS = 8000` | Balances free-tier token limits vs. real-world resume/JD length |
| Auto-commits come from Claude Code, not repo git hooks | `.git/hooks` holds only samples (verified 2026-07-02); the "auto: update X" commits are made by a global Claude Code PostToolUse hook in settings.json. Safe to push as-is; `git reset --soft HEAD~N` only if a cleaner history is wanted |

---

## What's Running Right Now

- **Local:** `venv\Scripts\activate && streamlit run app.py`
- **Live:** https://resume-job-fit-ai.streamlit.app (Streamlit Community Cloud)
- **CI:** GitHub Actions - pytest runs on every push to `main`
- **Tests:** `pytest tests/` - 26 passing, 0 failing

---

## 2026-07-02 - Refinement pass (repo hygiene + unpushed work recovered)

- **Recovered stranded work:** the 2026-06-22 MASTER_LOG commit (399 lines) had never been pushed to GitHub; it goes up with this pass.
- **Em dash purge (global style rule):** README, app.py, analyzer.py, db.py, and all three pages/ modules cleaned; all files verified parsing and the full suite re-run after the sweep.
- **Health check:** 26/26 tests passing locally in 1.4s; live Streamlit deployment responding; README's docs/screenshot.png reference verified present.

## 2026-09-24 - Refinement pass (refine-repo)

- Em dash purge: 291 occurrences replaced with " - " across 12 tracked files (docs, handoffs, logs, .gitignore comments, test strings).
- Verified after: pytest tests 40 passed before and after (CLAUDE.md still says 26, stale count).
