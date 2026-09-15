# Deployment - Resume Job-Fit AI

## Where it runs today

Streamlit Community Cloud, auto-deployed from `main`: https://resume-job-fit-ai.streamlit.app

**Known problem (2026-09-15):** the app currently redirects to a Streamlit login page (viewer authentication is on), so the public link is not public. Fix, Zaid only, 30 seconds:

1. https://share.streamlit.io -> the app's **Settings** -> **Sharing**.
2. Set **Who can view this app** to **Public** (turn viewer authentication off) -> Save.
3. Verify from a private browser window or `curl -sI -L https://resume-job-fit-ai.streamlit.app | grep -i location` (no `/-/login` redirect).

Secrets live in the Streamlit dashboard (**Settings** -> **Secrets**) as `GEMINI_API_KEY`; the shape is in `.streamlit/secrets.toml.example`.

## Fallback: Hugging Face Space (Docker, free)

If the Streamlit host stays gated, the same code runs as a Docker Space:

1. Create a Space (SDK: Docker, hardware: CPU basic, free).
2. Push this repo to the Space remote (`git remote add hf https://huggingface.co/spaces/<user>/resume-job-fit-ai && git push hf main`).
3. Add `GEMINI_API_KEY` under the Space's **Settings** -> **Variables and secrets**.
4. The `Dockerfile` in this repo already exposes port 7860 as Spaces expect.

## Data note

The job tracker is a single SQLite file on the host; rows are scoped per browser session (`session_owner.py`), so visitors never see each other's saved applications. The file is ephemeral on both hosts.
