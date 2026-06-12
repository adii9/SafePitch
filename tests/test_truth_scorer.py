"""
Tests for the truth_scorer (Task 3 — verification layer).

Pure-function tests, no API calls, no secrets. Safe to run in CI.

The 6 cases mirror the ones validated in the 12 Jun 2026 session log:
- Case 1: 1 green + 2 deck-only → 100 (clamped from 102)
- Case 2: 3 red + 0 green + 1 null → 61
- Case 3: empty → 100
- Case 4: 2 red + 1 null + 25-word summary → 73, medium
- Case 5 (e2e override): LLM truth_score=999 → 84
- Case 6: realistic 5-field audit → 72, medium

Rubric (locked — do not change without updating SPEC + spec.md):
    Start at 100.
    -12 per red_flag, +4 per green_flag.
    -1 per field with source_url == "pitch_deck".
    -3 per field with source_url is None.
    Clamp to [0, 100].
    Tier: >=85 "high", >=60 "medium", else "low".
"""

import os
import sys
import pytest

# Make the src/ layout importable when pytest runs from the repo root.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO_ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from safepitch.models import (
    _tier_from_score,
    compute_truth_score,
    make_verification_report,
    VerificationReport,
    FlagSummary,
    VerifiedDataPoint,
)


# ---------------------------------------------------------------------------
# _tier_from_score
# ---------------------------------------------------------------------------

def test_tier_high():
    assert _tier_from_score(85) == "high"
    assert _tier_from_score(100) == "high"
    assert _tier_from_score(99) == "high"


def test_tier_medium():
    assert _tier_from_score(60) == "medium"
    assert _tier_from_score(84) == "medium"
    assert _tier_from_score(70) == "medium"


def test_tier_low():
    assert _tier_from_score(59) == "low"
    assert _tier_from_score(0) == "low"
    assert _tier_from_score(30) == "low"


# ---------------------------------------------------------------------------
# compute_truth_score
# ---------------------------------------------------------------------------

def test_case1_one_green_two_deck_only_clamps_to_100():
    # 100 + 4 (1 green) - 2 (2 deck-only) = 102 → clamp 100
    red = []
    green = [FlagSummary(flag="x", description="y")]
    data = {
        "a": VerifiedDataPoint(value="1", source_url="pitch_deck"),
        "b": VerifiedDataPoint(value="2", source_url="pitch_deck"),
    }
    assert compute_truth_score(red, green, data) == 100


def test_case2_three_red_zero_green_one_null():
    # 100 - 36 (3 red) - 3 (1 "Not found") = 61
    red = [FlagSummary(flag=f"r{i}", description="d") for i in range(3)]
    green = []
    data = {"a": VerifiedDataPoint(value="1", source_url="Not found")}
    assert compute_truth_score(red, green, data) == 61


def test_case3_empty_inputs_returns_100():
    assert compute_truth_score([], [], {}) == 100


def test_case4_two_red_one_null_with_summary():
    # 100 - 24 (2 red) - 3 (1 "Not found") = 73, medium
    red = [FlagSummary(flag=f"r{i}", description="d") for i in range(2)]
    data = {"a": VerifiedDataPoint(value="1", source_url="Not found")}
    summary = (
        "Two red flags regarding undisclosed financial metrics and missing "
        "regulatory clearances, plus a field that could not be verified online."
    )
    report = make_verification_report(red, [], data, summary)
    assert report.truth_score == 73
    assert report.tier == "medium"
    assert len(report.summary.split()) <= 25


def test_case5_end_to_end_override_replaces_llm_score():
    # Simulate the override in main.save_final_step: LLM emits truth_score=999,
    # Python recomputes deterministically and overwrites it.
    red = [FlagSummary(flag="a", description="b"), FlagSummary(flag="c", description="d")]
    green = [FlagSummary(flag="e", description="f")]
    data = {
        "verified": VerifiedDataPoint(value="v", source_url="https://example.com/source"),
    }
    # 100 - 24 (2 red) + 4 (1 green) = 80
    expected = 80
    llm_truth_score = 999  # LLM would have produced this; override discards it.
    report = make_verification_report(red, green, data, "Two red, one green, one verified externally.")
    assert report.truth_score == expected
    assert report.truth_score != llm_truth_score  # override must have replaced it


def test_case6_realistic_five_field_audit():
    # 100 - 24 (2 red) + 4 (1 green) - 1 (1 deck-only) - 3 (1 null) - 3 (1 null) = 73?
    # Spec from session log: 100 - 24 + 4 - 2 - 6 = 72
    # That implies 2 deck-only (-2) and 2 null (-6) — i.e. 5 fields total:
    #   1 external URL (no deduction)
    #   2 deck-only (-1 each = -2)
    #   2 "Not found" (-3 each = -6)
    red = [FlagSummary(flag=f"r{i}", description="d") for i in range(2)]
    green = [FlagSummary(flag="g", description="d")]
    data = {
        "verified_ext": VerifiedDataPoint(value="v", source_url="https://example.com"),
        "deck_a": VerifiedDataPoint(value="1", source_url="pitch_deck"),
        "deck_b": VerifiedDataPoint(value="2", source_url="pitch_deck"),
        "null_a": VerifiedDataPoint(value="?", source_url="Not found"),
        "null_b": VerifiedDataPoint(value="?", source_url="Not found"),
    }
    # 100 - 24 + 4 - 2 - 6 = 72
    assert compute_truth_score(red, green, data) == 72
    assert _tier_from_score(compute_truth_score(red, green, data)) == "medium"


def test_score_clamps_to_zero():
    # 10 red flags → 100 - 120 = -20, clamp 0
    red = [FlagSummary(flag=f"r{i}", description="d") for i in range(10)]
    assert compute_truth_score(red, [], {}) == 0
    assert _tier_from_score(0) == "low"


def test_score_clamps_to_hundred():
    # 5 green flags → 100 + 20 = 120, clamp 100
    green = [FlagSummary(flag=f"g{i}", description="d") for i in range(5)]
    assert compute_truth_score([], green, {}) == 100


def test_accepts_dict_inputs_not_just_pydantic():
    # compute_truth_score should accept raw dicts (from upstream LLM JSON)
    red = [{"flag": "a", "description": "b"}]
    green = [{"flag": "c", "description": "d"}]
    data = {"a": {"value": "1", "source_url": "pitch_deck"}}
    # 100 - 12 + 4 - 1 = 91
    assert compute_truth_score(red, green, data) == 91


def test_real_external_url_no_deduction():
    # VerifiedDataPoint with a real URL is the happy path — no score impact.
    red = []
    green = []
    data = {
        "a": VerifiedDataPoint(value="v", source_url="https://www.zoominfo.com/c/example/123"),
    }
    assert compute_truth_score(red, green, data) == 100


def test_make_verification_report_shape():
    report = make_verification_report(
        red_flags=[],
        green_flags=[],
        internet_verified_data={},
        summary="No issues found.",
    )
    assert isinstance(report, VerificationReport)
    assert report.truth_score == 100
    assert report.tier == "high"
    assert report.summary == "No issues found."


def test_pydantic_validation_truth_score_bounds():
    # truth_score is constrained to [0, 100]. Out-of-range should fail.
    with pytest.raises(Exception):
        VerificationReport(truth_score=-1, tier="low", summary="x")
    with pytest.raises(Exception):
        VerificationReport(truth_score=101, tier="high", summary="x")
