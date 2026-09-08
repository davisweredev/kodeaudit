"""File system scanner — walks a project tree efficiently."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_IGNORED_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".env",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".next",
    "target",
    "vendor",
    ".tox",
    ".nox",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".hypothesis",
    "htmlcov",
    ".eggs",
    ".cache",
    ".pixi",
    "__pypackages__",
    "develop-eggs",
    "downloads",
    "eggs",
    "lib",
    "lib64",
    "parts",
    "sdist",
    "var",
    "wheels",
    "share",
    ".abstra",
    "mnesia",
    "rabbitmq",
    "rabbitmq-data",
    "activemq-data",
}

SOURCE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".mts": "TypeScript",
    ".go": "Go",
    ".java": "Java",
    ".php": "PHP",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
}


@dataclass
class ScannedFile:
    path: Path
    relative_path: str
    extension: str
    language: str | None
    size_bytes: int
    line_count: int | None = None


@dataclass
class ScanResult:
    root: Path
    files: list[ScannedFile] = field(default_factory=list)
    directories: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def get_language(extension: str) -> str | None:
    return SOURCE_EXTENSIONS.get(extension.lower())


def _count_lines(file_path: Path, max_file_size: int) -> int | None:
    """Count source lines for a text file, skipping binary and huge files."""
    try:
        with open(file_path, "rb") as f:
            head = f.read(4096)
    except OSError:
        return None
    if b"\x00" in head:
        return None
    try:
        with open(file_path, "r", errors="replace") as f:
            return sum(1 for _ in f)
    except (OSError, UnicodeDecodeError):
        return None


def _scan_file(result: ScanResult, file_path: Path, ignored: set[str],
               max_file_size: int) -> None:
    """Process a single file and add it to the scan result."""
    rel = file_path.relative_to(result.root)
    ext = file_path.suffix.lower()
    lang = get_language(ext)

    try:
        size = file_path.stat().st_size
    except OSError:
        result.errors.append(f"Could not stat: {rel}")
        return

    line_count = None
    if lang and size <= max_file_size:
        line_count = _count_lines(file_path, max_file_size)

    result.files.append(ScannedFile(
        path=file_path,
        relative_path=str(rel),
        extension=ext,
        language=lang,
        size_bytes=size,
        line_count=line_count,
    ))


def scan_project(
    root: str | Path,
    extra_ignored_dirs: set[str] | None = None,
    max_file_size: int = 10 * 1024 * 1024,
) -> ScanResult:
    root = Path(root).resolve()
    ignored = DEFAULT_IGNORED_DIRS | (extra_ignored_dirs or set())
    result = ScanResult(root=root)

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dir_path = Path(dirpath)

        dirnames[:] = [d for d in dirnames if d not in ignored]

        if dir_path != root:
            result.directories.append(dir_path)

        for fname in filenames:
            _scan_file(result, dir_path / fname, ignored, max_file_size)

    return result
