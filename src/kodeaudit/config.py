"""Configuration support — optional .kodeaudit.toml file.

Configuration is entirely optional. When absent, sensible defaults are used.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    ignored_dirs: set[str] = field(default_factory=set)
    large_function_lines: int = 50
    large_file_lines: int = 500
    max_parameters: int = 6
    max_nesting_depth: int = 4
    enabled_analyzers: list[str] | None = None  # None = all
    scoring_weights: dict[str, float] = field(default_factory=dict)


DEFAULT_CONFIG = Config()


def load_config(project_root: str | Path) -> Config:
    """Load configuration from .kodeaudit.toml if present.

    Returns defaults when no config file exists or it can't be parsed.
    """
    config_path = Path(project_root) / ".kodeaudit.toml"
    if not config_path.exists():
        return Config()

    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return DEFAULT_CONFIG

    cfg = Config()

    ignored = data.get("ignored_dirs")
    if isinstance(ignored, list):
        cfg.ignored_dirs = {str(i) for i in ignored}

    thresholds = data.get("thresholds", {})
    if isinstance(thresholds, dict):
        cfg.large_function_lines = int(thresholds.get("large_function_lines", 50))
        cfg.large_file_lines = int(thresholds.get("large_file_lines", 500))
        cfg.max_parameters = int(thresholds.get("max_parameters", 6))
        cfg.max_nesting_depth = int(thresholds.get("max_nesting_depth", 4))

    analyzers = data.get("enabled_analyzers")
    if isinstance(analyzers, list):
        cfg.enabled_analyzers = [str(a) for a in analyzers]

    weights = data.get("scoring_weights", {})
    if isinstance(weights, dict):
        cfg.scoring_weights = {str(k): float(v) for k, v in weights.items()}

    return cfg
