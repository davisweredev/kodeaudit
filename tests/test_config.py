"""Tests for configuration loading."""

from kodeaudit.config import load_config, DEFAULT_CONFIG


def test_default_config_when_no_file(tmp_path):
    cfg = load_config(tmp_path)
    assert cfg == DEFAULT_CONFIG


def test_load_ignored_dirs(tmp_path):
    (tmp_path / ".kodeaudit.toml").write_text(
        'ignored_dirs = ["vendor", "generated"]\n'
    )
    cfg = load_config(tmp_path)
    assert cfg.ignored_dirs == {"vendor", "generated"}


def test_load_thresholds(tmp_path):
    (tmp_path / ".kodeaudit.toml").write_text(
        '[thresholds]\n'
        'large_function_lines = 30\n'
        'max_parameters = 5\n'
    )
    cfg = load_config(tmp_path)
    assert cfg.large_function_lines == 30
    assert cfg.max_parameters == 5


def test_load_enabled_analyzers(tmp_path):
    (tmp_path / ".kodeaudit.toml").write_text(
        'enabled_analyzers = ["python", "security"]\n'
    )
    cfg = load_config(tmp_path)
    assert cfg.enabled_analyzers == ["python", "security"]


def test_invalid_toml_falls_back_to_defaults(tmp_path):
    (tmp_path / ".kodeaudit.toml").write_text("not [valid toml")
    cfg = load_config(tmp_path)
    assert cfg == DEFAULT_CONFIG


def test_scoring_weights(tmp_path):
    (tmp_path / ".kodeaudit.toml").write_text(
        '[scoring_weights]\n'
        'Testing = 0.5\n'
        'Security = 0.2\n'
    )
    cfg = load_config(tmp_path)
    assert cfg.scoring_weights["Testing"] == 0.5
    assert cfg.scoring_weights["Security"] == 0.2
