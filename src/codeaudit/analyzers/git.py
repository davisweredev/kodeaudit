"""Git analyzer — read-only analysis of Git repository state."""

from __future__ import annotations

import subprocess

from .base import AnalysisContext, BaseAnalyzer
from ..models import Finding, Severity


def _run_git(args: list[str], root: str) -> str | None:
    """Run a git command safely. Returns stdout or None on failure."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


class GitAnalyzer(BaseAnalyzer):
    name = "git"

    def analyze(self, ctx: AnalysisContext) -> list[Finding]:
        findings: list[Finding] = []
        if not ctx.project.has_git:
            return findings

        root = ctx.project.root

        # Gather informational Git metadata (read-only).
        ctx.project.git_branch = _run_git(
            ["rev-parse", "--abbrev-ref", "HEAD"], root)
        count = _run_git(["rev-list", "--count", "HEAD"], root)
        if count is not None and count.isdigit():
            ctx.project.git_commit_count = int(count)

        if ctx.quick:
            return findings

        # Check for uncommitted changes.
        status = _run_git(["status", "--porcelain"], root)
        if status:
            changed_files = [l for l in status.splitlines() if l.strip()]
            if len(changed_files) > 10:
                findings.append(Finding(
                    category="Git",
                    severity=Severity.LOW,
                    title=f"{len(changed_files)} uncommitted changes",
                    message="There are uncommitted changes in the working tree.",
                    recommendation="Review and commit changes regularly to maintain clean history.",
                ))

        return findings