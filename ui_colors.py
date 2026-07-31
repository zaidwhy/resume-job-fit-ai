"""Shared UI color tokens for score-band rendering.

Single source of truth for the fit-score color rule used across app.py and the
pages/ scripts (Streamlit reruns each page as its own script, so this needs to
be importable independently of app.py). No Streamlit import here on purpose -
keeps this trivially importable from any page.
"""

SCORE_COLOR_GOOD = "#16a34a"
SCORE_COLOR_MEDIUM = "#d97706"
SCORE_COLOR_LOW = "#dc2626"


def score_color(score: int) -> str:
    if score >= 75:
        return SCORE_COLOR_GOOD
    if score >= 50:
        return SCORE_COLOR_MEDIUM
    return SCORE_COLOR_LOW
