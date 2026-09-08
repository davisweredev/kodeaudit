"""Core domain models for KodeAudit findings and results."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class Severity(enum.IntEnum):
    """Finding severity — higher value means more severe."""
    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    def label(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Finding:
    """A single auditable finding."""
    category: str
    severity: Severity
    title: str
    message: str
    file: str | None = None
    line: int | None = None
    recommendation: str = ""


@dataclass
class ProjectInfo:
    """Detected project metadata."""
    root: str
    languages: dict[str, float] = field(default_factory=dict)  # lang -> percentage
    frameworks: list[str] = field(default_factory=list)
    has_git: bool = False
    has_docker: bool = False
    has_ci: bool = False
    git_branch: str | None = None
    git_commit_count: int | None = None
    tests_detected: bool = False

    @property
    def primary_language(self) -> str:
        if not self.languages:
            return "Unknown"
        return max(self.languages, key=self.languages.get)


@dataclass
class ProjectStats:
    """General project size statistics."""
    total_files: int = 0
    source_files: int = 0
    directories: int = 0
    total_source_lines: int = 0
    by_language: dict[str, int] = field(default_factory=dict)  # lang -> file count
    size_bytes: int = 0

    @property
    def approximate_size_label(self) -> str:
        if self.size_bytes < 100_000:
            return "Small"
        if self.size_bytes < 1_000_000:
            return "Medium"
        if self.size_bytes < 10_000_000:
            return "Large"
        return "Very Large"


@dataclass
class AuditResult:
    """Complete result of an audit run."""
    project: ProjectInfo
    stats: ProjectStats
    findings: list[Finding] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)  # category -> 0-100
    overall_score: float = 0.0
    recommendations: list[str] = field(default_factory=list)
    analyzed_categories: list[str] = field(default_factory=list)

    @property
    def high_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity >= Severity.HIGH]

    @property
    def medium_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == Severity.MEDIUM]

    @property
    def low_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity <= Severity.LOW]
