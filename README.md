# KodeAudit

KodeAudit is a fast, lightweight command-line tool that audits the health of any
software project. Run it from a project directory and get a readable report of
structure, code quality, security signals, dependencies, Git state, and testing —
plus a deterministic 0–100 health score and practical recommendations.

It is **not** another IDE, linter, or security scanner. It aggregates lightweight
analysis into a project-context health report, and is designed so deeper
language-specific analyzers can be added incrementally.

```text
KodeAudit
────────────────────────────────────────────────

Project: ~/my-projects/my-app
Languages: Python 100.0%
Size: Medium (37 source files, ~1,200 lines)
Git: detected (main, 42 commits)
Testing: ✓ Tests detected

PROJECT HEALTH
────────────────────────────────────────────────

Overall: 94/100

  Structure           100  ████████████████████
  Code Quality         80  ████████████████░░░░
  Security            100  ████████████████████
  Dependencies        100  ████████████████████
  Git                 100  ████████████████████
  Testing             100  ████████████████████
```

## Why it exists

Developers need quick, honest answers about a codebase before diving in:
*Is this project healthy? Where are the risk areas? What should I fix first?*

KodeAudit answers those questions in under a second, without modifying anything.

## Installation

Requires **Python 3.10+**. No third-party runtime dependencies.

```bash
pip install kodeaudit
```

During development (from the repository root):

```bash
pip install -e .
```

The `kodeaudit` command is installed on your `PATH` automatically — no manual
editing needed.

## Quick start

```bash
# audit the current directory
kodeaudit

# audit a specific project
kodeaudit /path/to/project

# machine-readable output
kodeaudit --json

# audit category subsets
kodeaudit security
kodeaudit structure
kodeaudit dependencies
kodeaudit git
kodeaudit testing

# full HTML report
kodeaudit --html report.html

# compare against a previously saved audit
kodeaudit --save /tmp/base.json
# ...make changes, then:
kodeaudit compare --store /tmp/base.json

# faster subset of analysis
kodeaudit --quick
```

## Supported languages

| Language   | Detection | AST analysis | Code quality |
|------------|-----------|--------------|--------------|
| Python     | Yes       | Yes (built-in `ast`) | Yes         |
| JavaScript | Yes       | Planned      | Yes         |
| TypeScript | Yes       | Planned      | Yes         |
| Go, Java, PHP, Ruby, Rust, C/C++, C#, Swift, Kotlin, Scala, Shell | Extension detection only | Planned | Planned |

### Framework detection

During project detection, KodeAudit looks for framework signals such as:

- Python: Django, Flask, FastAPI
- JavaScript/TypeScript: React, Next.js, Vue, Angular, Svelte, Express, NestJS, Vite, Nuxt, Fastify

Framework claims require file-based signals (e.g. a `manage.py`, a `next.config.*`,
or matching dependencies in `package.json`) — not just similar file names.

## Analyzer architecture

KodeAudit is built around an analyzer interface. Adding a new analyzer means
implementing one class and registering it — the engine, scoring, and reporters
do not change.

```text
KodeAudit
    |
    +-- Project Detector
    |
    +-- Analyzer Engine
    |       |
    |       +-- General Analyzer
    |       +-- Python Analyzer
    |       +-- Code Quality Analyzer
    |       +-- Security Analyzer
    |       +-- Dependency Analyzer
    |       +-- Git Analyzer
    |       +-- Testing Analyzer
    |
    +-- Scoring Engine
    |
    +-- Recommendation Engine
    |
    +-- Reporters
            |
            +-- Terminal
            +-- JSON
            +-- HTML
```

Each analyzer receives an `AnalysisContext` (project info + scanned files) and
returns a list of `Finding` objects.

```python
class Analyzer(abc.ABC):
    name: str

    def analyze(self, ctx: AnalysisContext) -> list[Finding]:
        ...
```

### Analysis principles

- **Python structural analysis uses the `ast` module.** Functions, classes,
  imports, calls, decorators, async functions, nesting, and syntax errors are
  detected via real syntax trees — never by string-searching `"def "` or `"print("`.
- **Text-based scanning** is reserved for things AST does not cover: TODO/FIXME
  markers, file names, commented-out code, and configuration patterns.
- **Generated/vendor directories are ignored** (configurable): `.git`,
  `node_modules`, `__pycache__`, `.venv`, `dist`, `build`, `.next`, `target`,
  `vendor`, and others.
- **Binary files are skipped** for line-counting.

## CLI commands

| Command | Description |
|---|---|
| `kodeaudit` | Full audit of the current directory |
| `kodeaudit <path>` | Audit a specific project |
| `kodeaudit --quick` | Faster subset of analysis |
| `kodeaudit security` | Only the security analysis |
| `kodeaudit structure` | Only structure analysis |
| `kodeaudit dependencies` | Only dependency analysis |
| `kodeaudit git` | Only Git-state analysis |
| `kodeaudit testing` | Only test-detection analysis |
| `kodeaudit python` | Python-focused analysis |
| `kodeaudit --json` | JSON output (no terminal text mixed in) |
| `kodeaudit --html <file>` | Self-contained HTML report |
| `kodeaudit --save <file>` | Save baseline for comparison |
| `kodeaudit compare` | Compare with a previous audit |
| `kodeaudit --no-color` | Plain terminal output |
| `kodeaudit --version` | Show version |

## Scoring system

Each category starts at 100 and loses points per finding, weighted by severity
(INFO 0, LOW 1, MEDIUM 3, HIGH 8, CRITICAL 15). Category scores are floored at 10
so a single finding can never zero-out a category. A project with source code
but **no automated tests** additionally loses 70 points from the Testing category,
since missing test infrastructure is a structural signal beyond any single finding.
The overall score is a weighted average:

```text
Structure    15%
Code Quality 30%
Security     25%
Dependencies 10%
Git           5%
Testing      15%
```

Scoring is **deterministic**: the same project always produces the same scores.
Every deduction is explainable by the findings that produced it.

## Configuration

Configuration is entirely optional. A developer can `pip install` KodeAudit and
run it with zero setup.

If a `.kodeaudit.toml` file exists in the project root, it is honored:

```toml
# Extra directories to ignore during scanning
ignored_dirs = ["vendor", "generated"]

[thresholds]
large_function_lines = 50
large_file_lines    = 500
max_parameters      = 6
max_nesting_depth   = 4

# Restrict which analyzers run
enabled_analyzers = ["python", "security", "git", "dependencies", "testing", "general", "codequality"]

[scoring_weights]
Testing   = 0.15
Security  = 0.25
```

## Security behavior

KodeAudit performs **conservative** secret scanning. It reports:

- Potential hardcoded passwords, API keys, tokens, and private keys
- `.env` and similar sensitive files
- Credential-shaped values in source files

Important guarantees:

- Findings are worded as *potential* issues and require human verification.
- **Actual secret values are never printed** — not in terminal output, JSON,
  HTML, logs, or exceptions.
- Test fixtures and documentation directories are skipped to avoid noise.

```text
config.py:42

[HIGH] Potential hardcoded secret

A credential-like value was detected.
The actual value has been hidden.

Recommendation:
Move the credential to environment-based configuration.
```

## Safety

KodeAudit is **read-only by default**. It never modifies source files, deletes
or renames files, changes Git state, installs dependencies, executes project
code, or runs project scripts. `kodeaudit compare` only reads the baseline file
you point it at.

## Development setup

```bash
git clone <repository>
cd kodeaudit
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

## Contributing

1. Fork the repository.
2. Implement your change against the analyzer interface.
3. Add tests under `tests/` using temporary directories (never the developer's
   machine).
4. Run `pytest` and verify `kodeaudit` still audits its own repository cleanly.
5. Open a pull request with a clear description.

Style notes: simple, maintainable Python with the standard library where
practical; no unnecessary abstractions; findings must include severity,
category, file, line, and a recommendation.

## Roadmap

- [x] V1 Foundation: CLI, scanner, detector, terminal output
- [x] V2 Python analysis with `ast`
- [x] V3 Code quality: TODO/FIXME, suspicious files, large files
- [x] V4 Security: conservative secret detection, safe reporting
- [x] V5 Health score + recommendations
- [x] V6 Git + dependencies + testing analyzers
- [x] V7 CLI modes: `--quick`, category subcommands
- [x] V8 Reports: JSON + HTML
- [x] V9 Comparison: `kodeaudit compare`
- [ ] V10 Optional integrations with Ruff, ESLint, Semgrep, package-manager
      audit tools (invoked explicitly and safely)
- [ ] V11 Safe fixes (`kodeaudit --fix`) for a small set of provably safe,
      reversible transformations
- [ ] JavaScript/TypeScript AST analysis
- [ ] Duplicate-code detection heuristics
- [ ] Preset weights and per-project severity overrides

## License

MIT