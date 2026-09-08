"""Tests for JSON output format."""

import json

from kodeaudit.models import AuditResult, Finding, ProjectInfo, ProjectStats, Severity
from kodeaudit.reporters.json_report import render_json


def test_json_output_valid():
    result = AuditResult(
        project=ProjectInfo(root="/tmp/test", languages={"Python": 100.0}),
        stats=ProjectStats(
            total_files=5,
            source_files=3,
            directories=2,
            total_source_lines=150,
        ),
        findings=[
            Finding("Security", Severity.HIGH, "Secret", "msg",
                    file="config.py", line=5, recommendation="Fix it"),
        ],
        scores={"Security": 50.0},
        overall_score=70.0,
        recommendations=["Fix things"],
    )
    output = render_json(result)
    data = json.loads(output)
    assert data["project"]["root"] == "/tmp/test"
    assert data["overall_score"] == 70.0
    assert data["scores"]["Security"] == 50.0
    assert data["findings"][0]["severity"] == "HIGH"
    assert data["findings"][0]["file"] == "config.py"
    assert data["findings"][0]["line"] == 5
    assert data["recommendations"] == ["Fix things"]


def test_json_contains_all_findings():
    findings = [
        Finding("A", Severity.LOW, "t1", "m1"),
        Finding("B", Severity.MEDIUM, "t2", "m2"),
        Finding("C", Severity.HIGH, "t3", "m3"),
    ]
    result = AuditResult(
        project=ProjectInfo(root="/tmp/test"),
        stats=ProjectStats(),
        findings=findings,
    )
    output = render_json(result)
    data = json.loads(output)
    assert len(data["findings"]) == 3
