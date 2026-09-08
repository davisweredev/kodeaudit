"""General project analyzer — structure, size, suspicious files."""

from __future__ import annotations

import re
from pathlib import Path

from .base import AnalysisContext, BaseAnalyzer
from ..models import Finding, Severity

SUSPICIOUS_PATTERNS = [
    re.compile(r"^final(_?\w+)?\.\w+$", re.I),
    re.compile(r"^final2?\.\w+$", re.I),
    re.compile(r"^old[\d_]*\.\w+$", re.I),
    re.compile(r"^new[\d_]*\.\w+$", re.I),
    re.compile(r"^(new|old|final)_?(copy|version|backup)[\d_]*\.\w+$", re.I),
    re.compile(r"^backup[\d_]*\.\w+$", re.I),
    re.compile(r"^copy[\d_]*\.\w+$", re.I),
    re.compile(r"^test_old[\d_]*\.\w+$", re.I),
    re.compile(r"^temp[\d_]*\.\w+$", re.I),
    re.compile(r"^untitled[\d_]*\.\w+$", re.I),
    re.compile(r"^debug[\d_]*\.\w+$", re.I),
    re.compile(r"^tmpfiles?\.\w+$", re.I),
    re.compile(r"^\d{4,}-(\d{2}-)+\d{4,}(\.\w+)?$", re.I),  # date-stamped files
    re.compile(r"\.py\.(old|bak|orig|copy)$", re.I),
]

BACKUP_EXTENSIONS = {".bak", ".orig", ".old", ".backup", "~"}


class GeneralAnalyzer(BaseAnalyzer):
    name = "general"

    def __init__(self, large_file_lines: int = 500):
        self.large_file_lines = large_file_lines

    def analyze(self, ctx: AnalysisContext) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._check_suspicious_files(ctx))
        findings.extend(self._check_large_files(ctx))
        findings.extend(self._check_deep_nesting(ctx))
        findings.extend(self._check_empty_files(ctx))
        return findings

    def _check_suspicious_files(self, ctx: AnalysisContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in ctx.scan.files:
            name = Path(f.relative_path).name
            for pattern in SUSPICIOUS_PATTERNS:
                if pattern.match(name):
                    findings.append(Finding(
                        category="Structure",
                        severity=Severity.INFO,
                        title=f"Suspicious file name: {name}",
                        message=f"File '{f.relative_path}' has a name that may indicate "
                                "temporary, backup, or leftover code.",
                        file=f.relative_path,
                        recommendation="Review whether this file is intentional and needed.",
                    ))
                    break

            # Check backup extensions
            if f.extension in BACKUP_EXTENSIONS:
                findings.append(Finding(
                    category="Structure",
                    severity=Severity.INFO,
                    title=f"Backup file: {name}",
                    message=f"File '{f.relative_path}' appears to be a backup file.",
                    file=f.relative_path,
                    recommendation="Consider removing backup files if they are no longer needed.",
                ))

        return findings

    def _check_large_files(self, ctx: AnalysisContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in ctx.scan.files:
            if f.line_count is None:
                continue
            if f.line_count > self.large_file_lines:
                sev = Severity.MEDIUM if f.line_count <= self.large_file_lines * 2 else Severity.HIGH
                findings.append(Finding(
                    category="Structure",
                    severity=sev,
                    title=f"Large file ({f.line_count} lines)",
                    message=f"File '{f.relative_path}' contains approximately {f.line_count} lines.",
                    file=f.relative_path,
                    recommendation="Consider splitting into smaller, focused modules.",
                ))
        return findings

    def _check_deep_nesting(self, ctx: AnalysisContext) -> list[Finding]:
        # Python nesting is handled by the AST analyzer.
        # For non-Python files, use a simple indentation heuristic.
        findings: list[Finding] = []
        for f in ctx.scan.files:
            if f.language == "Python":
                continue
            if not f.language:
                continue
            try:
                text = f.path.read_text(errors="replace")
            except OSError:
                continue

            lines = text.splitlines()
            for i, line in enumerate(lines, 1):
                stripped = line.rstrip()
                if not stripped:
                    continue
                leading = len(stripped) - len(stripped.lstrip())
                # Use 2-space indent for JS/TS/other
                indent_level = leading // 2
                if indent_level >= 7:
                    findings.append(Finding(
                        category="Structure",
                        severity=Severity.MEDIUM,
                        title="Deeply nested code detected",
                        message=f"Line {i} in '{f.relative_path}' is deeply indented.",
                        file=f.relative_path,
                        line=i,
                        recommendation="Consider extracting nested logic into helper functions.",
                    ))
                    break

        return findings

    def _check_empty_files(self, ctx: AnalysisContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in ctx.scan.files:
            # Empty __init__.py is idiomatic Python packaging — not an issue.
            if f.language == "Python" and Path(f.relative_path).name == "__init__.py":
                continue
            if f.language and f.line_count == 0:
                findings.append(Finding(
                    category="Structure",
                    severity=Severity.INFO,
                    title="Empty source file",
                    message=f"File '{f.relative_path}' has no content.",
                    file=f.relative_path,
                    recommendation="Remove empty files or add intended content.",
                ))
        return findings
