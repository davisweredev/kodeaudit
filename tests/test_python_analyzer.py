"""Tests for the Python AST analyzer."""

from codeaudit.analyzers.python import PythonAnalyzer
from codeaudit.models import Severity


def _mk_project(tmp_path, content, filename="main.py"):
    fpath = tmp_path / filename
    fpath.write_text(content)


def _analyze(tmp_path, content, filename="main.py"):
    fpath = tmp_path / filename
    fpath.write_text(content)
    from codeaudit.scanner import scan_project
    from codeaudit.detector import detect_project
    from codeaudit.analyzers.base import AnalysisContext
    scan = scan_project(tmp_path)
    proj = detect_project(tmp_path, scan)
    ctx = AnalysisContext(project=proj, scan=scan)
    return PythonAnalyzer().analyze(ctx)


def test_syntax_error(tmp_path):
    findings = _analyze(tmp_path, "def foo(:\n    pass\n")
    assert any(f.title == "Syntax error" for f in findings)


def test_large_function_detected(tmp_path):
    lines = ["def big_function():\n"]
    lines += ["    x = 1\n"] * 60
    content = "".join(lines)
    findings = _analyze(tmp_path, content)
    large = [f for f in findings if "big_function" in f.title]
    assert len(large) == 1


def test_async_function(tmp_path):
    content = "async def fetch_data():\n    return 1\n"
    findings = _analyze(tmp_path, content)
    # No findings expected - no issues
    assert len(findings) == 0


def test_class_detection(tmp_path):
    content = """class MyClass:
    def method1(self):
        pass
"""
    findings = _analyze(tmp_path, content)
    # No problematic findings
    assert len(findings) == 0


def test_print_call_detected(tmp_path):
    content = """def main():
    print("hello world")
"""
    findings = _analyze(tmp_path, content)
    assert any(f.title == "print() call detected" for f in findings)


def test_print_in_string_not_detected(tmp_path):
    content = """def main():
    text = "print(this should not be found)"
    return text
"""
    findings = _analyze(tmp_path, content)
    assert not any(f.title == "print() call detected" for f in findings)


def test_bare_except_detected(tmp_path):
    content = """def safe():
    try:
        return 1
    except:
        return 0
"""
    findings = _analyze(tmp_path, content)
    assert any(f.title == "Bare except clause" for f in findings)
    assert all(f.severity == Severity.MEDIUM for f in findings)


def test_wildcard_import_detected(tmp_path):
    content = """from os import *
import sys
"""
    findings = _analyze(tmp_path, content)
    assert any(f.title == "Wildcard import" for f in findings)


def test_deep_nesting_detected(tmp_path):
    content = """def complex():
    if x:
        for y in z:
            while w:
                with f:
                    try:
                        return 1
                    except Exception:
                        pass
"""
    findings = _analyze(tmp_path, content)
    assert any("Deep nesting" in f.title for f in findings)


def test_no_findings_for_clean_code(tmp_path):
    content = """def add(a, b):
    return a + b


class Calculator:
    def __init__(self):
        self.total = 0

    def add(self, value):
        self.total += value
        return self.total
"""
    findings = _analyze(tmp_path, content)
    assert findings == []


def test_long_parameter_list(tmp_path):
    content = """def too_many(a, b, c, d, e, f, g, h):
    return a
"""
    findings = _analyze(tmp_path, content)
    assert any("parameters" in f.title for f in findings)
