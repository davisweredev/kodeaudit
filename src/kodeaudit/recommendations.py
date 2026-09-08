"""Recommendation engine — generates actionable recommendations from findings."""

from __future__ import annotations

from .models import AuditResult


MAX_RECOMMENDATIONS = 8


def generate_recommendations(result: AuditResult) -> None:
    """Generate prioritized recommendations from findings.

    Modifies result.recommendations in place.
    """
    recs: list[tuple[int, str]] = []  # (priority_score, recommendation_text)

    # Collect from findings, prioritized by severity
    for f in result.findings:
        if not f.recommendation:
            continue
        priority = f.severity.value * 10
        # Add file-level specificity bonus
        if f.file:
            priority += 1
        text = f.recommendation
        # Deduplicate
        if text not in [r for _, r in recs]:
            recs.append((priority, text))

    # Sort by priority descending
    recs.sort(key=lambda x: -x[0])

    result.recommendations = [text for _, text in recs[:MAX_RECOMMENDATIONS]]
