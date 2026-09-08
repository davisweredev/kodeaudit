"""Integration tests — full audit pipeline."""

from codeaudit.cli import run_audit


def test_full_audit_python_project(python_project):
    result = run_audit(str(python_project))
    assert result.project.primary_language == "Python"
    assert result.stats.source_files >= 3
    assert 0 <= result.overall_score <= 100
    assert result.scores
    assert isinstance(result.recommendations, list)


def test_full_audit_security_project(security_project):
    result = run_audit(str(security_project))
    security = [f for f in result.findings if f.category == "Security"]
    assert len(security) >= 1
    # Check no secret values leaked
    import json
    data = json.dumps({
        "findings": [
            {"title": f.title, "message": f.message} for f in security
        ]
    })
    # Verify the secret values are hidden
    assert "sk_live" not in data
    assert "password123" not in data
    assert "super_secret_password" not in data


def test_quick_mode_returns_valid(python_project):
    result = run_audit(str(python_project), quick=True)
    assert 0 <= result.overall_score <= 100
    assert result.scores


def test_audit_empty_directory(tmp_path):
    result = run_audit(str(tmp_path))
    assert result.overall_score > 0
    assert result.project.languages == {}


def test_audit_js_project(js_project):
    result = run_audit(str(js_project))
    assert "JavaScript" in result.project.languages


def test_broken_symlink_does_not_crash(tmp_path):
    import os
    (tmp_path / "real.py").write_text("x = 1\n")
    os.symlink(tmp_path / "nonexistent.py", tmp_path / "broken.py")
    result = run_audit(str(tmp_path))
    assert 0 <= result.overall_score <= 100


def test_full_audit_uses_weighted_overall(python_project):
    result = run_audit(str(python_project))
    # Weighted overall must equal the sum of (category weights * score).
    weights = {
        "Structure": 0.15, "Code Quality": 0.30, "Security": 0.25,
        "Dependencies": 0.10, "Git": 0.05, "Testing": 0.15,
    }
    weighted = round(
        sum(result.scores[cat] * w for cat, w in weights.items()), 1)
    assert result.overall_score == weighted
