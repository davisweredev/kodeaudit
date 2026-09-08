"""Scoring engine — deterministic project health scoring.

Scoring model
=============
Each category starts at 100 and loses points for every finding, weighted by
severity:

    INFO      0 points
    LOW       1 point
    MEDIUM    3 points
    HIGH      8 points
    CRITICAL  15 points

Category scores are floored at 10 so a single flurry of findings can never
zero-out a category. Missing automated tests is treated as a category-level
problem (see ``MISSING_TESTS_PENALTY``) because test absence is a structural
signal, not just one more finding.

The overall score is the weighted sum of category scores:

    Structure      15%
    Code Quality   30%
    Security       25%
    Dependencies   10%
    Git             5%
    Testing        15%

Scoring is deterministic: identical findings always produce identical scores.
"""

from __future__ import annotations

from .models import AuditResult, Finding, Severity

# Base score every category starts from.
BASE_SCORE = 100.0

# Categories shown in the report and weighted in the overall score.
SCORE_CATEGORIES = [
    "Structure",
    "Code Quality",
    "Security",
    "Dependencies",
    "Git",
    "Testing",
]

# Severity -> points deducted from a category per finding.
SEVERITY_DEDUCTIONS = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 3,
    Severity.HIGH: 8,
    Severity.CRITICAL: 15,
}

# A "no tests detected" finding indicates a missing test setup entirely,
# which is far more significant than a single MEDIUM-finding deduction.
MISSING_TESTS_PENALTY = 70.0

# Well-known findings that signal the absence of any automated tests.
MISSING_TESTS_TITLES = {
    "No Python tests detected",
    "No JavaScript/TypeScript tests detected",
}

# Finding categories -> score categories they map into.
CATEGORY_MAP = {
    "Structure": "Structure",
    "Python": "Code Quality",
    "Code Quality": "Code Quality",
    "Security": "Security",
    "Dependencies": "Dependencies",
    "Git": "Git",
    "Testing": "Testing",
}

# Category weights for the overall score.
WEIGHTS = {
    "Structure": 0.15,
    "Code Quality": 0.30,
    "Security": 0.25,
    "Dependencies": 0.10,
    "Git": 0.05,
    "Testing": 0.15,
}


def _group_by_category(result: AuditResult) -> dict[str, list[Finding]]:
    by_category: dict[str, list[Finding]] = {}
    for finding in result.findings:
        by_category.setdefault(finding.category, []).append(finding)
    return by_category


def calculate_scores(result: AuditResult) -> None:
    """Calculate category and overall scores for an audit result.

    Modifies ``result.scores`` and ``result.overall_score`` in place.
    """
    by_category = _group_by_category(result)

    scores: dict[str, float] = {cat: BASE_SCORE for cat in SCORE_CATEGORIES}

    for finding_cat, findings in by_category.items():
        mapped = CATEGORY_MAP.get(finding_cat, "Code Quality")
        if mapped not in scores:
            scores[mapped] = BASE_SCORE

        total_deduction = sum(
            SEVERITY_DEDUCTIONS.get(f.severity, 0) for f in findings
        )
        scores[mapped] = max(10.0, scores[mapped] - total_deduction)

    # Missing tests is a category-level signal, penalized more heavily.
    missing_tests = 0
    for f in by_category.get("Testing", []):
        if f.title in MISSING_TESTS_TITLES:
            missing_tests += 1
    if missing_tests and not result.project.tests_detected:
        scores["Testing"] = max(0.0, scores["Testing"] - MISSING_TESTS_PENALTY)

    result.scores = {k: round(v, 1) for k, v in scores.items()}

    weighted_sum = sum(
        scores.get(cat, 0.0) * weight for cat, weight in WEIGHTS.items()
    )
    result.overall_score = round(weighted_sum, 1)