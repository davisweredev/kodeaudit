"""General code quality analyzer — TODOs, FIXMEs, long lines, etc."""

from __future__ import annotations

import re

from .base import AnalysisContext, BaseAnalyzer
from ..models import Finding, Severity

MARKER_PATTERN = re.compile(r"""(?:#|//)\s*(TODO|FIXME|HACK|XXX)\b""", re.IGNORECASE)
COMMENTED_CODE_PATTERN = re.compile(r"^\s*[#/]\s*(?:def |class |import |from |if |for |while |return |const |let |var |function )")
LONG_LINE_THRESHOLD = 200


class CodeQualityAnalyzer(BaseAnalyzer):
    name = "codequality"

    def analyze(self, ctx: AnalysisContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in ctx.scan.files:
            if not f.language:
                continue
            parts = f.relative_path.replace("\\", "/").split("/")
            if any(p in {"tests", "test", "__tests__", "fixtures"} for p in parts):
                continue
            if ctx.quick and f.line_count and f.line_count > 200:
                continue
            self._analyze_file(f, findings)
        return findings

    def _analyze_file(self, f, findings: list[Finding]) -> None:
        try:
            lines = f.path.read_text(errors="replace").splitlines()
        except OSError:
            return

        # Commented-out code detection:
        # Walk consecutive comment-only lines; flag a run if it contains
        # enough code-like patterns to look like disabled code.
        comment_run = 0
        code_like_in_run = 0
        run_start = 1

        def _flush_commented_run(end_line: int) -> None:
            nonlocal comment_run, code_like_in_run, run_start
            if comment_run >= 3 and code_like_in_run >= 2:
                findings.append(Finding(
                    category="Code Quality",
                    severity=Severity.LOW,
                    title=f"Block of commented-out code ({comment_run} lines)",
                    message="A block of commented-out code was detected.",
                    file=f.relative_path,
                    line=run_start,
                    recommendation="Remove commented-out code; use version control to recover old code.",
                ))
            comment_run = 0
            code_like_in_run = 0
            run_start = end_line

        for i, line in enumerate(lines, 1):
            # TODO / FIXME / HACK / XXX
            match = MARKER_PATTERN.search(line)
            if match:
                tag = match.group(1).upper()
                findings.append(Finding(
                    category="Code Quality",
                    severity=Severity.INFO if tag == "TODO" else Severity.LOW,
                    title=f"{tag} comment",
                    message=f"Found {tag} comment.",
                    file=f.relative_path,
                    line=i,
                    recommendation=f"Address the {tag} or create a tracking issue.",
                ))

            # Long lines
            if len(line) > LONG_LINE_THRESHOLD:
                findings.append(Finding(
                    category="Code Quality",
                    severity=Severity.INFO,
                    title=f"Long line ({len(line)} chars)",
                    message=f"Line {i} is {len(line)} characters long.",
                    file=f.relative_path,
                    line=i,
                    recommendation="Break long lines for readability.",
                ))

            # Track comment runs for commented-out code
            stripped = line.lstrip()
            is_comment = stripped.startswith("#") or stripped.startswith("//")
            if is_comment:
                if comment_run == 0:
                    run_start = i
                comment_run += 1
                if COMMENTED_CODE_PATTERN.match(line):
                    code_like_in_run += 1
            else:
                _flush_commented_run(i + 1)

        _flush_commented_run(len(lines) + 1)
