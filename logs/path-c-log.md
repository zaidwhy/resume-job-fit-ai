# Path C Build Log - 2026-06-16

## Goal
Build the moat: SQLite-backed job application tracker that turns this from a one-shot analyzer into a job search command center.

---

## Changes Made

### 1. `db.py` - SQLite persistence layer (new)

Schema: one `applications` table - id, job_title, company, score, status, notes, saved_on.

Functions:
- `init_db()` - creates table if not exists; called at the top of every other function so no manual setup needed
- `save_application(job_title, score, company, notes)` - inserts a new row, returns the new id
- `update_status(row_id, status)` - updates status; validates against `STATUSES` list
- `update_notes(row_id, notes)` - updates notes field
- `delete_application(row_id)` - hard delete
- `get_all_applications()` - returns all rows newest-first as list of dicts
- `get_stats()` - returns total count, avg score, and per-status breakdown
- `export_csv()` - serializes all rows to CSV string (no temp files, returned as str for `st.download_button`)

Uses `contextmanager` for connection lifecycle - auto-commits and always closes.
`DB_PATH = project_root / "job_tracker.db"` - local only, never committed (added to `.gitignore`).

### 2. `pages/2_Job_Tracker.py` - tracker page (new)

Summary stats row: Total saved | Avg fit score | Applied | Interviewing | Offers - via `st.metric()`.

Filter + sort bar: filter by status (All / Saved / Applied / Interviewing / Offer / Rejected), sort by Newest / Score high-low / Score low-high.

Per-application cards (`st.container(border=True)`):
- Job title + company + date as heading
- Score rendered large with color coding (green/amber/red)
- Status dropdown - immediate update on change, triggers `st.rerun()`
- Notes text input - immediate update on change
- 🗑️ delete button

Export CSV button at the bottom - `st.download_button` with the CSV string from `export_csv()`.

### 3. `app.py` - "Save to tracker" form (updated)

- Imported `save_application` from `db`
- Added `tracker_saved: False` to session state defaults
- Resets `tracker_saved = False` on every new analysis
- After the download buttons: shows a `st.form` with Job Title + Company inputs and a "Save to tracker 📋" submit button
- On save: calls `save_application()`, sets `tracker_saved = True`, reruns to show success message
- Success message includes a link prompt to the Job Tracker sidebar page
- Once saved, the form is replaced by the success message (no double-save)

### 4. `.gitignore` - added `job_tracker.db`

### 5. `README.md` - updated feature table, roadmap, project structure

---

## Decisions

| Decision | Reason |
|---|---|
| SQLite not JSON/pickle | SQLite gives us proper querying, updates, and concurrent-safe writes with zero setup |
| `db.py` separate from `app.py` | Keeps persistence layer testable and UI-agnostic; could be imported in a CLI or test |
| `init_db()` called on every function | Idempotent setup - no "did you run migrations?" problem |
| `st.form` for save | Prevents partial submissions (job title + company saved atomically on submit) |
| `tracker_saved` in session state | Prevents double-saves; form replaced by success message after first save |
| Status update on selectbox change | Immediate UX - no "Save changes" button needed; status writes are cheap |
| `export_csv()` returns string | `st.download_button(data=...)` accepts str - no temp file or BytesIO needed |

---

## Files Created / Modified

| File | Change |
|------|--------|
| `db.py` | New - SQLite layer (init, save, update, delete, get_all, get_stats, export_csv) |
| `pages/2_Job_Tracker.py` | New - full tracker UI: stats, filter/sort, per-app cards, CSV export |
| `app.py` | Added `from db import save_application`; tracker_saved session state; Save to tracker form |
| `.gitignore` | Added `job_tracker.db` |
| `README.md` | Feature table, roadmap, project structure updated |
