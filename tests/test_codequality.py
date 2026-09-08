"""Tests for code quality analyzer."""

from codeaudit.analyzers.codequality import CodeQualityAnalyzer
from codeaudit.scanner import scan_project
from codeaudit.detector import detect_project
from codeaudit.analyzers.base import AnalysisContext


def _analyze(tmp_path):
    scan = scan_project(tmp_path)
    proj = detect_project(tmp_path, scan)
    ctx = AnalysisContext(project=proj, scan=scan)
    return CodeQualityAnalyzer().analyze(ctx)


def test_todo_detected(tmp_path):
    (tmp_path / "main.py").write_text("# TODO: fix this later\nx = 1\n")
    findings = _analyze(tmp_path)
    assert any(f.title == "TODO comment" for f in findings)


def test_fixme_detected(tmp_path):
    (tmp_path / "main.py").write_text("# FIXME: this leaks\nx = 1\n")
    findings = _analyze(tmp_path)
    assert any(f.title == "FIXME comment" for f in findings)


def test_hack_detected(tmp_path):
    (tmp_path / "main.py").write_text("# HACK: quick workaround\nx = 1\n")
    findings = _analyze(tmp_path)
    assert any("HACK" in f.title for f in findings)


def test_commented_out_code(tmp_path):
    content = """x = 1

# def old_function():
#     return 1
# 
# def another_one():
#     return 2

y = 2
"""
    (tmp_path / "main.py").write_text(content)
    findings = _analyze(tmp_path)
    assert any("commented-out" in f.title for f in findings)


def test_long_line_detected(tmp_path):
    (tmp_path / "main.py").write_text(f"x = 1{'a' * 250}\n")
    findings = _analyze(tmp_path)
    assert any("Long line" in f.title for f in findings)


def test_clean_file_no_findings(tmp_path):
    (tmp_path / "main.py").write_text("def add(a, b):\n    return a + b\n")
    findings = _analyze(tmp_path)
    assert findings == []
