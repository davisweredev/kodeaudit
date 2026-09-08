"""CLI entry point — KodeAudit command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import __version__
from .config import load_config
from .scanner import scan_project
from .detector import detect_project
from .models import AuditResult, Finding, ProjectStats, Severity
from .analyzers.base import AnalysisContext
from .analyzers.general import GeneralAnalyzer
from .analyzers.python import PythonAnalyzer
from .analyzers.codequality import CodeQualityAnalyzer
from .analyzers.security import SecurityAnalyzer
from .analyzers.dependencies import DependencyAnalyzer
from .analyzers.git import GitAnalyzer
from .analyzers.testing import TestingAnalyzer
from .scoring import calculate_scores
from .recommendations import generate_recommendations
from .reporters.terminal import render_terminal
from .reporters.json_report import serialize_result
from .reporters.html import render_html

CATEGORY_ANALYZERS = {
    "structure": ["general"],
    "security": ["security"],
    "dependencies": ["dependencies"],
    "git": ["git"],
    "testing": ["testing"],
    "python": ["python", "codequality", "general"],
    "quality": ["codequality", "python", "general"],
}

ANALYZER_CLASSES = {
    "general": GeneralAnalyzer,
    "python": PythonAnalyzer,
    "codequality": CodeQualityAnalyzer,
    "security": SecurityAnalyzer,
    "dependencies": DependencyAnalyzer,
    "git": GitAnalyzer,
    "testing": TestingAnalyzer,
}

ALL_ANALYZERS = list(ANALYZER_CLASSES.keys())

# Maps each analyzer to the score category its findings contribute to.
ANALYZER_SCORE_CATEGORIES = {
    "general": "Structure",
    "python": "Code Quality",
    "codequality": "Code Quality",
    "security": "Security",
    "dependencies": "Dependencies",
    "git": "Git",
    "testing": "Testing",
}


def _select_analyzers(categories: list[str] | None,
                      cfg) -> list[str]:
    """Choose which analyzers run based on requested categories and config."""
    if categories:
        selected = []
        for c in categories:
            selected.extend(CATEGORY_ANALYZERS.get(c, []))
        return list(dict.fromkeys(selected))
    if cfg.enabled_analyzers:
        return [a for a in ALL_ANALYZERS if a in cfg.enabled_analyzers]
    return ALL_ANALYZERS


def _analyzer_kwargs(cfg) -> dict:
    """Build per-analyzer constructor arguments from configuration."""
    return {
        "general": {"large_file_lines": cfg.large_file_lines},
        "python": {
            "large_function_lines": cfg.large_function_lines,
            "max_parameters": cfg.max_parameters,
            "max_nesting_depth": cfg.max_nesting_depth,
        },
    }


def _run_selected_analyzers(result: AuditResult, ctx: AnalysisContext,
                            selected: list[str], kwargs: dict) -> None:
    """Run each selected analyzer, catching and reporting per-analyzer failures."""
    for name in selected:
        cls = ANALYZER_CLASSES[name]
        try:
            analyzer = cls(**kwargs.get(name, {}))
            result.findings.extend(analyzer.analyze(ctx))
        except Exception:
            result.findings.append(Finding(
                category="System",
                severity=Severity.INFO,
                title=f"Analyzer '{name}' encountered an error",
                message="An unexpected error occurred during analysis.",
                recommendation="This may indicate a bug in KodeAudit. Please report it.",
            ))


def _finalize_scores(result: AuditResult, selected: list[str]) -> None:
    """Restrict reported scores to the categories whose analyzers ran."""
    kept = {
        name: cat
        for name, cat in ANALYZER_SCORE_CATEGORIES.items()
        if name in selected
    }
    result.scores = {
        cat: result.scores[cat]
        for cat in sorted(set(kept.values()))
        if cat in result.scores
    }
    result.analyzed_categories = sorted(set(kept.values()))

    full_categories = {
        "Structure", "Code Quality", "Security",
        "Dependencies", "Git", "Testing",
    }
    if set(result.analyzed_categories) != full_categories:
        # Partial audit: unweighted mean of the categories actually analyzed.
        if result.scores:
            result.overall_score = round(
                sum(result.scores.values()) / len(result.scores), 1)
    # Full audits keep the weighted overall score from calculate_scores().


def run_audit(
    project_path: str,
    quick: bool = False,
    categories: list[str] | None = None,
) -> AuditResult:
    """Run an audit against the given project path."""
    root = Path(project_path).resolve()

    if not root.is_dir():
        print(f"Error: '{project_path}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    cfg = load_config(root)

    scan = scan_project(root)
    project = detect_project(root, scan)

    stats = ProjectStats(
        total_files=len(scan.files),
        source_files=sum(1 for f in scan.files if f.language),
        directories=len(scan.directories),
        total_source_lines=sum(f.line_count or 0 for f in scan.files if f.language),
        size_bytes=sum(f.size_bytes for f in scan.files),
    )

    result = AuditResult(project=project, stats=stats)

    for error in scan.errors:
        result.findings.append(Finding(
            category="System",
            severity=Severity.INFO,
            title="Scanner warning",
            message=error,
            recommendation="Check file permissions or availability.",
        ))

    selected = _select_analyzers(categories, cfg)
    ctx = AnalysisContext(project=project, scan=scan, quick=quick)

    _run_selected_analyzers(result, ctx, selected, _analyzer_kwargs(cfg))

    result.findings.sort(key=lambda f: f.severity, reverse=True)
    calculate_scores(result)
    generate_recommendations(result)
    _finalize_scores(result, selected)

    return result


def _default_store() -> Path:
    return Path.home() / ".kodeaudit" / "last.json"


def cmd_compare(path_arg: str, store: str, quick: bool, json_mode: bool) -> None:
    store_path = Path(store) if store else _default_store()
    if not store_path.exists():
        print("No previous audit found.")
        print("Run `kodeaudit --save <file>` once to create a baseline.")
        sys.exit(1)
    try:
        previous = json.loads(store_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("Could not read previous audit file.", file=sys.stderr)
        sys.exit(1)

    current = run_audit(path_arg, quick=quick)

    prev_overall = previous.get("overall_score", 0.0)
    curr_overall = current.overall_score
    diff = curr_overall - prev_overall
    prev_scores = {k: float(v) for k, v in previous.get("scores", {}).items()}
    curr_scores = current.scores

    if json_mode:
        payload = {
            "previous": prev_overall,
            "current": curr_overall,
            "diff": diff,
            "previous_scores": prev_scores,
            "current_scores": curr_scores,
        }
        print(json.dumps(payload, indent=2))
        return

    print(f"PREVIOUS: {prev_overall:.0f}/100")
    print(f"CURRENT:  {curr_overall:.0f}/100")
    print()
    arrow = "+" if diff >= 0 else ""
    print(f"{arrow}{diff:.0f} change")
    print()

    all_cats = sorted(set(list(prev_scores) + list(curr_scores)))
    for cat in all_cats:
        p = prev_scores.get(cat, 0.0)
        c = curr_scores.get(cat, 0.0)
        if p == c:
            print(f"  {cat:<16} {c:>3.0f}  (no change)")
        else:
            d = c - p
            sign = "+" if d > 0 else ""
            print(f"  {cat:<16} {c:>3.0f}  {sign}{d:.0f}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kodeaudit",
        description="KodeAudit — Professional project health CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Commands:\n"
            "  kodeaudit              Audit the current directory\n"
            "  kodeaudit <path>       Audit a specific project directory\n"
            "  kodeaudit security     Audit only the security category\n"
            "  kodeaudit structure    Audit only the structure category\n"
            "  kodeaudit dependencies Audit only dependencies\n"
            "  kodeaudit git          Audit only Git state\n"
            "  kodeaudit testing      Audit only test coverage signals\n"
            "  kodeaudit python       Run all Python-focused analyzers\n"
            "  kodeaudit compare      Compare with a previously saved audit\n"
        ),
    )
    parser.add_argument(
        "args", nargs="*", metavar="...",
        help="Path to project and/or category keyword (see below)")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output results as JSON (machine-readable)")
    parser.add_argument(
        "--no-color", action="store_true",
        help="Disable colored terminal output")
    parser.add_argument(
        "--quick", action="store_true",
        help="Run a faster subset of analysis")
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print verbose diagnostic information")
    parser.add_argument(
        "--html", metavar="FILE",
        help="Write an HTML report to FILE")
    parser.add_argument(
        "--save", metavar="FILE",
        help="Save audit results to FILE for later comparison")
    parser.add_argument(
        "--store", metavar="FILE",
        help="Baseline file to read for `compare` (default: ~/.kodeaudit/last.json)")
    return parser


def _normalize_argv(argv: list[str]) -> list[str]:
    """Reorder argv so positionals come before options.

    argparse cannot match `nargs="*"` positionals that are interspersed
    with options (e.g. `kodeaudit compare --store F /path`). Moving all
    options to the end keeps positionals contiguous and parseable.
    """
    value_opts = {"--save", "--html", "--store"}
    positionals: list[str] = []
    options: list[str] = []
    i = 0
    while i < len(argv):
        token = argv[i]
        if token in value_opts and i + 1 < len(argv):
            options.extend([token, argv[i + 1]])
            i += 2
        elif token.startswith("-"):
            options.append(token)
            i += 1
        else:
            positionals.append(token)
            i += 1
    return positionals + options


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(_normalize_argv(list(argv)))
    tokens: list[str] = args.args

    use_color = not args.no_color and sys.stdout.isatty()

    if tokens and tokens[0] == "compare":
        path_arg = tokens[1] if len(tokens) > 1 else "."
        cmd_compare(path_arg, args.store or str(_default_store()),
                    args.quick, args.json_output)
        return

    category = None
    path_arg: str
    if tokens and tokens[0] in CATEGORY_ANALYZERS:
        category = tokens[0]
        if len(tokens) > 1:
            path_arg = tokens[1]
        else:
            path_arg = "."
    else:
        path_arg = tokens[0] if tokens else "."

    start = time.monotonic()
    result = run_audit(path_arg, quick=args.quick,
                       categories=[category] if category else None)
    elapsed = time.monotonic() - start

    if args.verbose:
        print(f"[verbose] analyzed {result.stats.total_files} files, "
              f"{result.stats.directories} directories in {elapsed:.3f}s",
              file=sys.stderr)
        print(f"[verbose] {len(result.findings)} findings, "
              f"{len(category and CATEGORY_ANALYZERS[category] or ALL_ANALYZERS)} analyzers",
              file=sys.stderr)

    if args.json_output:
        data = serialize_result(result)
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    if args.html:
        html = render_html(result)
        Path(args.html).write_text(html, encoding="utf-8")
        print(f"Report written to {args.html}", file=sys.stderr)
        return

    if args.save:
        try:
            Path(args.save).parent.mkdir(parents=True, exist_ok=True)
            Path(args.save).write_text(
                json.dumps(serialize_result(result), indent=2, ensure_ascii=False),
                encoding="utf-8")
        except OSError:
            print(f"Warning: could not write baseline to {args.save}", file=sys.stderr)

    render_terminal(result, use_color=use_color)


if __name__ == "__main__":
    main()