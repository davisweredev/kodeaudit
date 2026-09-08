"""Terminal reporter — clean CLI output with optional color."""

from __future__ import annotations

import sys

from ..models import AuditResult, Severity, Finding


# ANSI colors (disabled if not a TTY or --no-color)
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"

SEVERITY_COLORS = {
    Severity.CRITICAL: RED,
    Severity.HIGH: RED,
    Severity.MEDIUM: YELLOW,
    Severity.LOW: CYAN,
    Severity.INFO: DIM,
}

SEVERITY_LABELS = {
    Severity.CRITICAL: "CRIT",
    Severity.HIGH: "HIGH",
    Severity.MEDIUM: "MED ",
    Severity.LOW: "LOW ",
    Severity.INFO: "INFO",
}


def _score_color(score: float) -> str:
    if score >= 80:
        return GREEN
    if score >= 60:
        return YELLOW
    return RED


def _score_bar(score: float) -> str:
    filled = int(score / 5)
    return "█" * filled + "░" * (20 - filled)


def render_terminal(result: AuditResult, use_color: bool = True, file=None) -> None:
    """Render the audit result to the terminal."""
    out = file or sys.stdout
    c = lambda s, color: f"{color}{s}{RESET}" if use_color else s

    header = "KodeAudit"
    divider = "─" * 48

    print(c(header, BOLD), file=out)
    print(c(divider, DIM), file=out)
    print(file=out)

    # Project info
    lang_str = ", ".join(
        f"{lang} {pct}%" for lang, pct in list(result.project.languages.items())[:5]
    )
    print(f"Project: {result.project.root}", file=out)
    print(f"Languages: {lang_str or 'Unknown'}", file=out)
    if result.project.frameworks:
        print(f"Frameworks: {', '.join(result.project.frameworks)}", file=out)
    print(f"Size: {result.stats.approximate_size_label} "
          f"({result.stats.source_files} source files, "
          f"~{result.stats.total_source_lines:,} lines)", file=out)
    if "Git" in result.analyzed_categories:
        if result.project.has_git:
            branch = result.project.git_branch or "unknown"
            commit_count = result.project.git_commit_count
            commits = f", {commit_count} commits" if commit_count is not None else ""
            print(f"Git: {c('detected', GREEN)} ({branch}{commits})", file=out)
        else:
            print("Git: Not detected", file=out)
    if "Testing" in result.analyzed_categories:
        tests_status = "✓ Tests detected" if result.project.tests_detected else "No tests detected"
        print(f"Testing: {tests_status}", file=out)
    print(file=out)

    # Score
    print(c("PROJECT HEALTH", BOLD), file=out)
    print(c(divider, DIM), file=out)
    print(file=out)

    score_color = _score_color(result.overall_score)
    print(f"Overall: {c(f'{result.overall_score:.0f}/100', BOLD + score_color)}", file=out)
    print(file=out)

    for cat, score in result.scores.items():
        sc = _score_color(score)
        bar = _score_bar(score)
        print(f"  {cat:<16} {c(f'{score:>5.0f}', sc)}  {c(bar, sc)}", file=out)
    print(file=out)

    # Findings summary
    high_count = len(result.high_findings)
    med_count = len(result.medium_findings)
    low_count = len(result.low_findings)

    print(c("FINDINGS", BOLD), file=out)
    print(c(divider, DIM), file=out)

    def _count_line(label, count, color):
        if count > 0:
            print(f"  {c(label, BOLD)}  {c(str(count), color)}", file=out)
        else:
            print(f"  {label}  {c('0', DIM)}", file=out)

    _count_line("HIGH   ", high_count, RED)
    _count_line("MEDIUM ", med_count, YELLOW)
    _count_line("LOW    ", low_count, CYAN)
    print(file=out)

    # High findings
    if result.high_findings:
        print(c("HIGH", BOLD + RED), file=out)
        print(c(divider, DIM), file=out)
        for f in result.high_findings[:5]:
            _print_finding(f, out, c)
            print(c(divider, DIM), file=out)

    # Medium findings (first few)
    if result.medium_findings:
        print(c("MEDIUM", BOLD + YELLOW), file=out)
        print(c(divider, DIM), file=out)
        for f in result.medium_findings[:5]:
            _print_finding(f, out, c)
            print(c(divider, DIM), file=out)

    # Recommendations
    if result.recommendations:
        print(c("TOP RECOMMENDATIONS", BOLD), file=out)
        print(c(divider, DIM), file=out)
        for i, rec in enumerate(result.recommendations[:6], 1):
            print(f"  {c(str(i) + '.', BOLD)} {rec}", file=out)
        print(file=out)

    print(c("Audit complete.", DIM), file=out)


def _print_finding(f: Finding, out, c) -> None:
    sev_label = SEVERITY_LABELS.get(f.severity, "????")
    sev_color = SEVERITY_COLORS.get(f.severity, "")

    loc = f.file or ""
    if f.line:
        loc += f":{f.line}"

    print(f"  {c(sev_label, BOLD + sev_color)}  [{f.category}]", file=out)
    if loc:
        print(f"  {c(loc, DIM)}", file=out)
    print(file=out)
    print(f"  {f.title}", file=out)
    if f.message != f.title:
        print(f"  {c(f.message, DIM)}", file=out)
    if f.recommendation:
        print(f"  {c('Recommendation:', BOLD)} {f.recommendation}", file=out)
    print(file=out)
