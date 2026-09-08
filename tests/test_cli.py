"""Tests for CLI behavior."""

import json
import subprocess
import sys


def test_cli_runs_and_outputs(tmp_path):
    (tmp_path / "main.py").write_text("x = 1\n")
    result = subprocess.run(
        [sys.executable, "-m", "kodeaudit.cli", "--no-color", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "PROJECT HEALTH" in result.stdout
    assert "Python" in result.stdout


def test_cli_version():
    result = subprocess.run(
        [sys.executable, "-m", "kodeaudit.cli", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "kodeaudit" in result.stdout.lower()


def test_cli_json_output(tmp_path):
    (tmp_path / "main.py").write_text("x = 1\n")
    result = subprocess.run(
        [sys.executable, "-m", "kodeaudit.cli", "--json", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "scores" in data
    assert "overall_score" in data
    assert "findings" in data


def test_cli_nonexistent_path():
    result = subprocess.run(
        [sys.executable, "-m", "kodeaudit.cli", "/nonexistent/path12345"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1


def test_cli_quick_mode(tmp_path):
    (tmp_path / "main.py").write_text("x = 1\n")
    result = subprocess.run(
        [sys.executable, "-m", "kodeaudit.cli", "--quick", "--json", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "overall_score" in data


def test_cli_category_subcommand(tmp_path):
    (tmp_path / "main.py").write_text("x = 1\n")
    result = subprocess.run(
        [sys.executable, "-m", "kodeaudit.cli", "structure", "--json", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "Structure" in data["scores"]
    assert "Security" not in data["scores"]


def test_cli_save_baseline(tmp_path):
    (tmp_path / "main.py").write_text("x = 1\n")
    base = tmp_path / "base.json"
    result = subprocess.run(
        [sys.executable, "-m", "kodeaudit.cli", "--save", str(base), str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert base.exists()
    data = json.loads(base.read_text())
    assert "overall_score" in data
