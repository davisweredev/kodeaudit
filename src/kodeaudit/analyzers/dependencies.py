"""Dependency analyzer — detects dependency files and reports basic health."""

from __future__ import annotations

from pathlib import Path

from .base import AnalysisContext, BaseAnalyzer
from ..models import Finding, Severity

PYTHON_DEPS_FILES = [
    "requirements.txt", "pyproject.toml", "Pipfile", "poetry.lock",
    "uv.lock", "setup.py", "setup.cfg",
]

JS_DEPS_FILES = [
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
]


class DependencyAnalyzer(BaseAnalyzer):
    name = "dependencies"

    def analyze(self, ctx: AnalysisContext) -> list[Finding]:
        findings: list[Finding] = []
        root = Path(ctx.project.root)

        # Python
        has_requirements = (root / "requirements.txt").exists()
        has_lock = any((root / f).exists() for f in ("poetry.lock", "uv.lock", "Pipfile.lock"))

        if has_requirements and not has_lock:
            findings.append(Finding(
                category="Dependencies",
                severity=Severity.LOW,
                title="No lock file detected",
                message="Found requirements.txt but no lock file. "
                        "Dependencies may not be reproducible.",
                recommendation="Consider using poetry, uv, or pip-tools to generate a lock file.",
            ))

        # JavaScript / TypeScript
        has_pkg = (root / "package.json").exists()
        has_pkg_lock = (root / "package-lock.json").exists()
        has_yarn = (root / "yarn.lock").exists()
        has_pnpm = (root / "pnpm-lock.yaml").exists()
        js_lock = has_pkg_lock or has_yarn or has_pnpm

        if has_pkg and not js_lock:
            findings.append(Finding(
                category="Dependencies",
                severity=Severity.MEDIUM,
                title="No JavaScript lock file",
                message="Found package.json but no lock file (package-lock.json, yarn.lock, or pnpm-lock.yaml).",
                recommendation="Run npm install / yarn install / pnpm install to generate a lock file.",
            ))

        # Check for dependency files that don't match detected languages
        # This is informational only
        lang_keys = set(ctx.project.languages.keys())
        has_python = "Python" in lang_keys
        has_js = any(l in lang_keys for l in ("JavaScript", "TypeScript"))

        if not has_python and any((root / f).exists() for f in PYTHON_DEPS_FILES):
            findings.append(Finding(
                category="Dependencies",
                severity=Severity.INFO,
                title="Python dependency files present",
                message="Python dependency files found but no Python source files detected.",
                recommendation="Verify these files are intentional.",
            ))

        if not has_js and has_pkg:
            findings.append(Finding(
                category="Dependencies",
                severity=Severity.INFO,
                title="JavaScript dependency files present",
                message="package.json found but no JavaScript/TypeScript source files detected.",
                recommendation="Verify these files are intentional.",
            ))

        return findings
