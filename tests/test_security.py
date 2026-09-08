"""Tests for security analyzer."""

from kodeaudit.analyzers.security import SecurityAnalyzer
from kodeaudit.scanner import scan_project
from kodeaudit.detector import detect_project
from kodeaudit.analyzers.base import AnalysisContext
from kodeaudit.models import Severity


def _analyze(tmp_path, quick=False):
    scan = scan_project(tmp_path)
    proj = detect_project(tmp_path, scan)
    ctx = AnalysisContext(project=proj, scan=scan, quick=quick)
    return SecurityAnalyzer().analyze(ctx)


def test_password_detected(tmp_path):
    (tmp_path / "config.py").write_text('PASSWORD = "mysecretpassword123"\n')
    findings = _analyze(tmp_path)
    assert any("password" in f.title.lower() for f in findings)
    assert all(f.severity == Severity.HIGH for f in findings)


def test_stripe_key_detected(tmp_path):
    key = "sk_" + "live_" + "1234567890abcdefghijklmnopqrstuvwxyz"
    (tmp_path / "config.py").write_text(f"API_KEY = '{key}'\n")
    findings = _analyze(tmp_path)
    assert any("Stripe" in f.title for f in findings)


def test_env_file_detected(tmp_path):
    (tmp_path / ".env").write_text("SECRET=abc123\n")
    findings = _analyze(tmp_path)
    assert any(f.file == ".env" for f in findings)


def test_no_secret_for_clean_file(tmp_path):
    (tmp_path / "config.py").write_text("import os\nNAME = 'project'\n")
    findings = _analyze(tmp_path)
    assert findings == []


def test_secret_value_hidden_in_output(tmp_path):
    secret = "sk_" + "live_" + "supersecretkey1234567890"
    (tmp_path / "config.py").write_text(f"API_KEY = '{secret}'\n")
    findings = _analyze(tmp_path)
    for f in findings:
        assert secret not in f.message
        assert secret not in f.title
