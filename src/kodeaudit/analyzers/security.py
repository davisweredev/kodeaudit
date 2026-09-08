"""Security analyzer — conservative detection of potential secrets and credentials."""

from __future__ import annotations

import re
from pathlib import Path

from .base import AnalysisContext, BaseAnalyzer
from ..models import Finding, Severity

# Patterns that suggest hardcoded secrets. Conservative — high confidence.
SECRET_PATTERNS = [
    (re.compile(r"""(?:password|passwd|pwd)\s*[=:]\s*['"][^'"]{6,}['"]""", re.I),
     "Potential hardcoded password"),
    (re.compile(r"""(?:api_key|apikey|api[-_]?secret)\s*[=:]\s*['"][^'"]{10,}['"]""", re.I),
     "Potential hardcoded API key"),
    (re.compile(r"""(?:secret|token)\s*[=:]\s*['"][A-Za-z0-9+/=_\-]{20,}['"]""", re.I),
     "Potential hardcoded secret or token"),
    (re.compile(r"""(?:AWS_SECRET_ACCESS_KEY)\s*[=:]\s*['"][A-Za-z0-9/+=]{30,}['"]"""),
     "Potential AWS secret key"),
    (re.compile(r"""-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"""),
     "Potential embedded private key"),
    (re.compile(r"""(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}"""),
     "Potential GitHub personal access token"),
    (re.compile(r"""(?:sk_live|pk_live|sk_test|pk_test)_[A-Za-z0-9]{20,}"""),
     "Potential Stripe API key"),
]

SENSITIVE_FILE_NAMES = {
    ".env", ".env.local", ".env.production", ".env.development",
    ".env.staging", ".env.backup",
}

# Directories that frequently contain fake/example secrets (test fixtures).
# Scanning them produces noise; real scanners exclude these by default.
SKIP_DIR_PARTS = {"tests", "test", "__tests__", "fixtures", "mocks", "mock", "examples", "docs"}

CREDENTIAL_RECOMMENDATIONS = [
    "Move the credential to environment variables or a secrets manager.",
    "Never commit secrets to version control.",
    "Use .env files locally and add them to .gitignore.",
]


def _is_excluded_path(relative_path: str) -> bool:
    parts = relative_path.replace("\\", "/").split("/")
    return any(p in SKIP_DIR_PARTS for p in parts) or parts[-1].startswith("test_")


class SecurityAnalyzer(BaseAnalyzer):
    name = "security"

    def analyze(self, ctx: AnalysisContext) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._check_sensitive_files(ctx))
        if not ctx.quick:
            findings.extend(self._check_source_files(ctx))
        return findings

    def _check_sensitive_files(self, ctx: AnalysisContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in ctx.scan.files:
            if _is_excluded_path(f.relative_path):
                continue
            name = Path(f.relative_path).name.lower()
            if name in SENSITIVE_FILE_NAMES:
                findings.append(Finding(
                    category="Security",
                    severity=Severity.HIGH,
                    title=f"Sensitive file: {name}",
                    message=f"File '{f.relative_path}' may contain secrets or credentials.",
                    file=f.relative_path,
                    recommendation=CREDENTIAL_RECOMMENDATIONS[0],
                ))
        return findings

    def _check_source_files(self, ctx: AnalysisContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in ctx.scan.files:
            if not f.language:
                continue
            if _is_excluded_path(f.relative_path):
                continue
            if not f.path.is_file():
                continue
            try:
                content = f.path.read_text(errors="replace")
            except (OSError, UnicodeDecodeError):
                continue

            for pattern, title in SECRET_PATTERNS:
                for match in pattern.finditer(content):
                    line_no = content[:match.start()].count("\n") + 1
                    findings.append(Finding(
                        category="Security",
                        severity=Severity.HIGH,
                        title=title,
                        message="A credential-like value was detected. "
                                "The actual value has been hidden.",
                        file=f.relative_path,
                        line=line_no,
                        recommendation=CREDENTIAL_RECOMMENDATIONS[0],
                    ))
                    break  # One per pattern per file

        return findings
