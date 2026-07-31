"""Unit tests for ui_colors.py - the shared score-band color source of truth.

Guards the DESIGN.md-documented consolidation (app.py, pages/1_Compare_Jobs.py, and
pages/2_Job_Tracker.py all import score_color() from here instead of redefining it).
"""

from __future__ import annotations

from ui_colors import SCORE_COLOR_GOOD, SCORE_COLOR_LOW, SCORE_COLOR_MEDIUM, score_color


def test_score_color_thresholds():
    assert score_color(100) == SCORE_COLOR_GOOD
    assert score_color(75) == SCORE_COLOR_GOOD
    assert score_color(74) == SCORE_COLOR_MEDIUM
    assert score_color(50) == SCORE_COLOR_MEDIUM
    assert score_color(49) == SCORE_COLOR_LOW
    assert score_color(0) == SCORE_COLOR_LOW


def test_score_color_values_are_the_documented_hex_literals():
    # Exact-match guard: these are the same three literals that used to be
    # duplicated across app.py, pages/1_Compare_Jobs.py, and pages/2_Job_Tracker.py.
    assert SCORE_COLOR_GOOD == "#16a34a"
    assert SCORE_COLOR_MEDIUM == "#d97706"
    assert SCORE_COLOR_LOW == "#dc2626"
