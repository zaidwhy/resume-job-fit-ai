# Path A Build Log - 2026-06-16

## Goal
Get real users fast: deploy to Streamlit Community Cloud + "Generate all sections" UX shortcut.

---

## Changes Made

### 1. Streamlit Cloud deploy support

**`.streamlit/config.toml`** (new)
- Sets `headless = true` and `port = 8501` for Cloud compatibility.
- Applies a clean indigo theme (`primaryColor = "#4f46e5"`) consistently across local and Cloud.

**`.streamlit/secrets.toml.example`** (new)
- Documents the secrets format for Streamlit Cloud (`GEMINI_API_KEY = "your-key-here"`).
- The real `.streamlit/secrets.toml` is already in `.gitignore`.

**`app.py` - secrets injection shim**
- Added `import os` and a startup block that reads `st.secrets` and injects any key found into `os.environ`.
- Why needed: Streamlit Cloud secrets live in `st.secrets`, not `os.environ`. `analyzer.py` uses `os.environ.get()` to stay UI-agnostic. The shim bridges both without coupling the core logic to Streamlit.
- Wrapped in a simple `for` loop + conditional so it's a no-op locally (env var already set via `.env`).

**README - Deploy section**
- Added "Deploy to Streamlit Community Cloud (free)" step-by-step section.
- Added Streamlit badge (`[![Open in Streamlit](...)](https://resume-job-fit-ai.streamlit.app)`).
- Added `.streamlit/` to project structure diagram.
- Added "Streamlit secrets ≠ env vars on Cloud" to What I Learned.

### 2. "Generate all sections" button

**`app.py`** - inserted between the fit score result and the tab bar:
- Checks `st.session_state` for which of the 4 AI sections (`cover_letter`, `interview_prep`, `skills_roadmap`, `linkedin_profile`) are still `None`.
- If any are missing, shows a **"Generate all sections ✨"** primary button in a narrow column so it doesn't span the full width.
- On click: iterates through all 4 generators in order, updating `st.progress()` after each one (`0% → 25% → 50% → 75% → 100%`). Each generator failure is a `st.warning()` (non-fatal) so the others still run.
- After all generators complete, calls `st.rerun()` to render all tabs populated.
- Button disappears automatically once all sections are generated (no sections left as `None`).

---

## Decisions

| Decision | Reason |
|---|---|
| Shim in `app.py`, not `analyzer.py` | Keeps `analyzer.py` UI-agnostic and testable without Streamlit |
| `st.progress()` with text updates | Users see which section is being generated - 4 API calls take 20-40s total |
| Non-fatal per-section errors (`st.warning`) | A single 429 shouldn't abort the other 3 generators |
| Button only shown when sections are missing | Disappears once all done - no clutter |

---

## Files Modified

| File | Change |
|------|--------|
| `.streamlit/config.toml` | Created - theme + server config |
| `.streamlit/secrets.toml.example` | Created - Cloud secrets format |
| `app.py` | Added `import os`, secrets shim, "Generate all sections" button with progress bar |
| `README.md` | Added Streamlit badge, deploy section, updated project structure, roadmap |

---

## What the User Still Needs to Do (manual - can't be automated)

1. Go to [share.streamlit.io](https://share.streamlit.io) → New app → select `syzayd/resume-job-fit-ai` → `app.py`
2. Under Advanced settings → Secrets: paste `GEMINI_API_KEY = "your-key-here"`
3. Click Deploy
4. Once live, update the badge URL in README.md (`https://resume-job-fit-ai.streamlit.app` → actual URL from Streamlit)
