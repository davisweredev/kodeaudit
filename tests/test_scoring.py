"""Tests for the scoring engine."""

from codeaudit.models import (
    AuditResult, Finding, ProjectInfo, ProjectStats, Severity,
)
from codeaudit.scoring import calculate_scores


def _make_result(findings=None, project=None, stats=None):
    result = AuditResult(
        project=project or ProjectInfo(root="/tmp/test"),
        stats=stats or ProjectStats(),
        findings=findings or [],
    )
    return result


def test_clean_project_full_score():
    result = _make_result(findings=[])
    calculate_scores(result)
    assert result.overall_score == 100.0


def test_no_deduction_for_info():
    result = _make_result([
        Finding("Structure", Severity.INFO, "test", "test"),
        Finding("Code Quality", Severity.INFO, "test", "test"),
    ])
    calculate_scores(result)
    assert result.scores["Structure"] == 100.0
    assert result.scores["Code Quality"] == 100.0


def test_severity_deductions():
    result = _make_result([
        Finding("Security", Severity.HIGH, "test", "test"),
        Finding("Security", Severity.MEDIUM, "test", "test"),
    ])
    calculate_scores(result)
    assert result.scores["Security"] == 100.0 - 8.0 - 3.0


def test_total_score_with_findings():
    findings = [
        Finding("Security", Severity.CRITICAL, "test", "test"),
        Finding("Code Quality", Severity.HIGH, "test", "test"),
    ]
    result = _make_result(findings=findings)
    calculate_scores(result)
    assert 0 <= result.overall_score <= 100


def test_scores_bounded_with_many_findings():
    many = [Finding("Security", Severity.CRITICAL, "t", "t") for _ in range(50)]
    result = _make_result(findings=many)
    calculate_scores(result)
    assert result.scores["Security"] >= 10.0
    assert result.overall_score >= 0


def test_deterministic():
    findings = [Finding("Security", Severity.HIGH, "t", "t")]
    r1 = _make_result(findings=findings)
    r2 = _make_result(findings=findings)
    calculate_scores(r1)
    calculate_scores(r2)
    assert r1.scores == r2.scores
    assert r1.overall_score == r2.overall_score


def test_calculate_scores_weighted_overall():
    result = _make_result(findings=[
        Finding("Security", Severity.HIGH, "t", "t"),
    ])
    calculate_scores(result)
    weights = {
        "Structure": 0.15, "Code Quality": 0.30, "Security": 0.25,
        "Dependencies": 0.10, "Git": 0.05, "Testing": 0.15,
    }
    expected = round(
        sum(result.scores[cat] * w for cat, w in weights.items()), 1)
    assert result.overall_score == expected


def test_missing_tests_penalty_applies():
    result = _make_result(findings=[
        Finding("Testing", Severity.MEDIUM, "No Python tests detected", "t"),
    ])
    result.project.tests_detected = False
    calculate_scores(result)
    assert result.scores["Testing"] <= 30


def test_missing_tests_penalty_skipped_when_tests_detected():
    result = _make_result(findings=[
        Finding("Testing", Severity.MEDIUM, "No Python tests detected", "t"),
    ])
    result.project.tests_detected = True
    calculate_scores(result)
    assert result.scores["Testing"] >= 90
