"""Tests for HTML reporter."""

from codeaudit.models import AuditResult, Finding, ProjectInfo, ProjectStats, Severity
from codeaudit.reporters.html import render_html


def test_html_contains_scores():
    result = AuditResult(
        project=ProjectInfo(root="/tmp/test", languages={"Python": 100.0}),
        stats=ProjectStats(source_files=3),
        scores={"Security": 50.0, "Testing": 80.0},
        overall_score=65.0,
        findings=[
            Finding("Security", Severity.HIGH, "Secret", "msg",
                    file="config.py", line=1, recommendation="Fix it"),
        ],
        recommendations=["Do something"],
    )
    html = render_html(result)
    assert "<!DOCTYPE html>" in html
    assert "65/100" in html
    assert "config.py" in html
    assert "Do something" in html
    assert "HIGH" in html
