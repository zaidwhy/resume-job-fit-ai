# Resume Job-Fit AI

A resume tool is only useful if you can trust what it writes. This one scores a resume against a
job description and rewrites bullets under a standing rule: it never invents experience, skills or
metrics the candidate does not have, and where a real number is unknown it leaves a placeholder
like `[X]`. Every model reply is parsed against a Pydantic schema, so the app handles typed fields
instead of free text.

It is for an applicant with one resume and one or more job descriptions. Everything runs on the
free tier of Google Gemini; nothing is stored except an optional local application tracker.

[![CI](https://github.com/zaidwhy/resume-job-fit-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/zaidwhy/resume-job-fit-ai/actions/workflows/ci.yml)

```bash
git clone https://github.com/zaidwhy/resume-job-fit-ai.git
cd resume-job-fit-ai
python -m venv venv && venv\Scripts\activate     # source venv/bin/activate on macOS / Linux
pip install -r requirements.txt
cp .env.example .env                              # paste a free key from aistudio.google.com/apikey
streamlit run app.py
```

Then click **Load sample**, **Analyze fit**, **Generate all sections**.

**Hosted copy:** the Streamlit Community Cloud app at `resume-job-fit-ai.streamlit.app` is not
publicly reachable. Checked 2026-11-13 with `curl -sI -L`: it redirects to a Streamlit login page
(viewer authentication is on). Treat it as not live until Zaid sets sharing to Public; steps in
[`DEPLOYMENT.md`](DEPLOYMENT.md).

![A recorded scoring run: paste a job description and a resume, get a fit score, salary range and keyword gaps](docs/demo-scoring.gif)

A recording of an earlier run of the app (an AI-internship job description against a real resume).
<!-- TODO(zaid): re-capture this GIF once the hosted app is public, or from the local app, with a date -->

## What it produces

| Output | Where | Notes |
|---|---|---|
| Fit score 0-100, verdict, salary range, matched and missing keywords | Analysis tab | salary range is the model's estimate from the job description |
| Bullet diff viewer, ATS tips | Analysis tab | original vs rewrite per bullet, copyable |
| Cover letter | Cover Letter tab | tones: Professional, Warm & Enthusiastic, Bold & Direct |
| Interview prep, skills gap roadmap, LinkedIn headline and About, email templates | their own tabs | follow-up, thank-you and rejection reply |
| Resume Health | Resume Health tab | standalone resume quality score and quick fixes |
| Generate all sections | one button | fills every tab |
| Multi-job comparison | `pages/1_Compare_Jobs.py` | 2-3 job descriptions, ranked, suggested apply order |
| Job tracker | `pages/2_Job_Tracker.py` | local SQLite: status, notes, score trend, funnel and histogram, CSV export |
| Company research | `pages/3_Company_Research.py` | culture, interview format, red flags, prep tips |
| Exports | download buttons | .txt and .docx; a tailored resume .docx with the rewrites substituted |
| PDF upload | main page | text extracted with pdfplumber |

## How it is built

| Part | File | Role |
|---|---|---|
| Entrypoint | `app.py` | layout, session state, 7 tabs, Generate all, PDF upload |
| Model layer | `analyzer.py` | Pydantic schemas passed as Gemini `response_schema`, prompts, retry, friendly errors |
| Panels | `ui_sections.py`, `ui_colors.py` | result panels; every model string goes through `html.escape()` before `unsafe_allow_html` |
| Exports | `exports.py` | .txt and .docx builders, no Streamlit |
| Persistence | `db.py`, `session_owner.py` | SQLite tracker; rows are scoped per browser session |
| Secrets | `secrets_bridge.py` | copies Streamlit Cloud `st.secrets` into the environment at startup |

Model: `gemini-2.5-flash-lite` (override with `GEMINI_MODEL`), chosen because `gemini-2.0-flash`
had no free quota and `gemini-2.5-flash` returned 503s under load when this was built. Inputs are
capped at 8,000 characters per resume and per job description, 200 for company name and role; the
app warns rather than truncates. Transient 429 and 5xx replies are retried up to 3 times with
backoff. Design notes on the UI as it exists: [`docs/DESIGN.md`](docs/DESIGN.md).

## What was learned

- Passing a Pydantic schema as `response_schema` removes string parsing of model output.
- One sentence in the system prompt, "never invent experience", does more for trust than model size.
- Every failure (bad key, rate limit, empty or oversized input, PDF parse error) surfaces as a short
  message, not a stack trace.
- Streamlit Cloud injects secrets through `st.secrets`, not `os.environ`; a startup shim bridges them.
- Streamlit reruns the whole script on each interaction; the uploaded PDF's name is kept in
  `st.session_state` so it is not re-extracted on every keypress.

## How it is tested

`python -m pytest tests/ -q`: 49 passed (2026-11-13, Windows 11, Python 3.14 venv). Gemini is mocked
everywhere; no key or network is needed. Coverage: `test_analyzer.py`, `test_exports.py`,
`test_db.py`, `test_secrets_bridge.py`, `test_ui_colors.py`, `test_run_cmd.py`, and
`test_app_smoke.py`, which renders the page headlessly with Streamlit's `AppTest`. CI runs the
same on Python 3.11 on every push to `main`; the latest run on `0cb5f94` succeeded.

Not measured: whether the fit score or salary estimate agree with any recruiter or market data.
No evaluation set exists, so the score is the model's judgement, not a calibrated measurement.
Rewrites stay truthful to your resume only as far as the prompt rule holds; review before sending.

## Status

Maintained; feature-complete against its original roadmap. The hosted app is gated (see above);
a Hugging Face Docker Space fallback is described in `DEPLOYMENT.md` and not deployed.

## Limits

- The tracker's SQLite file (`job_tracker.db`, gitignored) is ephemeral on Streamlit Cloud.
- Free-tier Gemini quotas and availability can change; the model choice is a snapshot.
- "Generate all sections" makes one model call per section, so it is the action most exposed to free-tier rate limits (retries are built in; exhaustion was not measured).

## License

MIT, see [LICENSE](LICENSE). Built by Zaid Ali Syed, [github.com/zaidwhy](https://github.com/zaidwhy).
Contributing notes: [CONTRIBUTING.md](CONTRIBUTING.md).
