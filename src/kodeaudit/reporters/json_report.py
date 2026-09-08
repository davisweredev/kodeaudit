"""JSON reporter — machine-readable output."""

from __future__ import annotations

import json
import sys

from ..models import AuditResult


def serialize_result(result: AuditResult) -> dict:
    """Convert an audit result into a plain JSON-serializable dict."""
    return {
        "project": {
            "root": result.project.root,
            "languages": result.project.languages,
            "frameworks": result.project.frameworks,
            "has_git": result.project.has_git,
            "git_branch": result.project.git_branch,
            "git_commit_count": result.project.git_commit_count,
            "tests_detected": result.project.tests_detected,
        },
        "stats": {
            "total_files": result.stats.total_files,
            "source_files": result.stats.source_files,
            "directories": result.stats.directories,
            "total_source_lines": result.stats.total_source_lines,
            "approximate_size": result.stats.approximate_size_label,
        },
        "scores": result.scores,
        "overall_score": result.overall_score,
        "findings": [
            {
                "category": f.category,
                "severity": f.severity.name,
                "title": f.title,
                "message": f.message,
                "file": f.file,
                "line": f.line,
                "recommendation": f.recommendation,
            }
            for f in result.findings
        ],
        "recommendations": result.recommendations,
    }


def render_json(result: AuditResult, file=None) -> str:
    """Render audit result as JSON to file or stdout. Returns the JSON string."""
    output = json.dumps(serialize_result(result), indent=2, ensure_ascii=False)
    target = file if file is not None else sys.stdout
    print(output, file=target)
    return output
