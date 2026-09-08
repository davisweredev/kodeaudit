"""Tests for project detection."""

from kodeaudit.scanner import scan_project
from kodeaudit.detector import detect_project


def test_detect_python_project(python_project):
    scan = scan_project(python_project)
    info = detect_project(python_project, scan)
    assert "Python" in info.languages
    assert info.languages["Python"] == 100.0


def test_detect_js_project(js_project):
    scan = scan_project(js_project)
    info = detect_project(js_project, scan)
    assert "JavaScript" in info.languages
    assert info.primary_language == "JavaScript"


def test_mixed_languages(python_project):
    # Add a JS file
    (python_project / "script.js").write_text("console.log('hi')")
    scan = scan_project(python_project)
    info = detect_project(python_project, scan)
    assert "Python" in info.languages
    assert "JavaScript" in info.languages


def test_python_framework_detection(python_project):
    scan = scan_project(python_project)
    info = detect_project(python_project, scan)
    assert "Python" in info.languages


def test_git_detection(python_project):
    scan = scan_project(python_project)
    info = detect_project(python_project, scan)
    assert info.has_git is True


def test_empty_directory(tmp_path):
    scan = scan_project(tmp_path)
    info = detect_project(tmp_path, scan)
    assert info.languages == {}


def test_detect_django(tmp_path):
    (tmp_path / "manage.py").write_text('#!/usr/bin/env python\n')
    (tmp_path / "requirements.txt").write_text("django>=4.0\n")
    scan = scan_project(tmp_path)
    info = detect_project(tmp_path, scan)
    assert "Django" in info.frameworks
