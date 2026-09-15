"""Per-visitor identity for the job tracker.

The app runs on a shared public Streamlit host with one SQLite file, so every tracker row is
scoped to the browser session that created it. The id lives in `st.session_state` and is
never shown to the user; a new tab or a server restart starts a fresh, empty tracker.
"""

from __future__ import annotations

import uuid

import streamlit as st

_KEY = "tracker_owner"


def current_owner() -> str:
    """Return this session's stable owner id, creating it on first use."""
    if _KEY not in st.session_state:
        st.session_state[_KEY] = uuid.uuid4().hex
    return st.session_state[_KEY]
