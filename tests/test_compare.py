"""Tests for compare mode."""

import json
import subprocess
import sys


def test_compare_no_baseline(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "kodeaudit.cli", "compare",
         "--store", str(tmp_path / "missing.json"), str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "No previous audit" in result.stdout


def test_compare_with_baseline(tmp_path):
    # Create a project
    (tmp_path / "main.py").write_text("x = 1\n")
    base = tmp_path / "base.json"
    base.write_text(json.dumps({
        "overall_score": 70.0,
        "scores": {"Security": 60.0, "Code Quality": 80.0},
    }))
    result = subprocess.run(
        [sys.executable, "-m", "kodeaudit.cli", "compare",
         "--store", str(base), str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "PREVIOUS:" in result.stdout
    assert "CURRENT:" in result.stdout
