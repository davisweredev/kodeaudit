"""Base analyzer protocol."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..models import Finding, ProjectInfo
from ..scanner import ScanResult


@dataclass
class AnalysisContext:
    """Shared context passed to all analyzers."""
    project: ProjectInfo
    scan: ScanResult
    quick: bool = False


class BaseAnalyzer(ABC):
    """Abstract base for all analyzers."""

    name: str = "base"

    @abstractmethod
    def analyze(self, ctx: AnalysisContext) -> list[Finding]:
        """Run analysis and return findings."""
        ...
