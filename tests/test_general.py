"""Tests for general analyzer."""

from kodeaudit.analyzers.general import GeneralAnalyzer
from kodeaudit.scanner import scan_project
from kodeaudit.detector import detect_project
from kodeaudit.analyzers.base import AnalysisContext


def _analyze(tmp_path):
    scan = scan_project(tmp_path)
    proj = detect_project(tmp_path, scan)
    ctx = AnalysisContext(project=proj, scan=scan)
    return GeneralAnalyzer().analyze(ctx)


def test_suspicious_filename(tmp_path):
    (tmp_path / "final.py").write_text("x = 1\n")
    (tmp_path / "final2.py").write_text("x = 2\n")
    (tmp_path / "backup.py").write_text("x = 3\n")
    (tmp_path / "normal.py").write_text("x = 4\n")
    findings = _analyze(tmp_path)
    titles = [f.title for f in findings]
    assert any("final" in t.lower() for t in titles)
    assert any("backup" in t.lower() for t in titles)


def test_large_file(tmp_path):
    (tmp_path / "huge.py").write_text("x = 1\n" * 600)
    findings = _analyze(tmp_path)
    assert any("Large file" in f.title for f in findings)


def test_empty_file(tmp_path):
    (tmp_path / "empty.py").write_text("")
    findings = _analyze(tmp_path)
    assert any("Empty" in f.title for f in findings)


def test_clean_project_no_findings(tmp_path):
    (tmp_path / "main.py").write_text("x = 1\n")
    (tmp_path / "utils.py").write_text("def helper():\n    return 1\n")
    findings = _analyze(tmp_path)
    assert findings == []
