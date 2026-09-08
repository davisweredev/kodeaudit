"""Tests for the recommendations engine."""

from kodeaudit.models import AuditResult, Finding, ProjectInfo, ProjectStats, Severity
from kodeaudit.recommendations import generate_recommendations


def test_recommendations_from_findings():
    result = AuditResult(
        project=ProjectInfo(root="/tmp/test"),
        stats=ProjectStats(),
        findings=[
            Finding(
                "Security", Severity.HIGH, "Secret",
                "msg",
                file="config.py",
                line=1,
                recommendation="Move to env vars",
            ),
            Finding(
                "Code Quality", Severity.MEDIUM, "Large function",
                "msg",
                file="main.py",
                recommendation="Split the function",
            ),
            Finding(
                "Testing", Severity.LOW, "No tests",
                "msg",
                recommendation="Add tests",
            ),
        ],
    )
    generate_recommendations(result)
    assert len(result.recommendations) >= 1
    assert "Move to env vars" in result.recommendations[0]


def test_no_recommendations_for_clean():
    result = AuditResult(
        project=ProjectInfo(root="/tmp/test"),
        stats=ProjectStats(),
        findings=[
            Finding("Security", Severity.INFO, "Info", "msg", recommendation=""),
        ],
    )
    generate_recommendations(result)
    assert result.recommendations == []
