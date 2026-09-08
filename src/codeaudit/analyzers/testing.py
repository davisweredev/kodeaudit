"""Testing analyzer — detects test structures and estimates coverage."""

from __future__ import annotations

from pathlib import Path

from .base import AnalysisContext, BaseAnalyzer
from ..models import Finding, Severity

PYTHON_TEST_INDICATORS = [
    "tests/", "test/", "test_*.py", "*_test.py",
    "conftest.py", "pytest.ini", "setup.cfg:[tool:pytest]",
    "pyproject.toml:pytest",
]

JS_TEST_INDICATORS = [
    "__tests__/", "*.test.js", "*.test.ts", "*.spec.js", "*.spec.ts",
    "jest.config.js", "jest.config.ts", "vitest.config.ts",
    ".mocharc.yml",
]


class TestingAnalyzer(BaseAnalyzer):
    name = "testing"

    def analyze(self, ctx: AnalysisContext) -> list[Finding]:
        findings: list[Finding] = []
        root = Path(ctx.project.root)
        lang_keys = set(ctx.project.languages.keys())

        # Python test detection
        if "Python" in lang_keys:
            if self._detect_python_tests(root):
                ctx.project.tests_detected = True
            else:
                findings.append(Finding(
                    category="Testing",
                    severity=Severity.MEDIUM,
                    title="No Python tests detected",
                    message="No test files or test directories were found for the Python source.",
                    recommendation="Add tests using pytest or unittest to improve code reliability.",
                ))

        # JS/TS test detection
        if any(l in lang_keys for l in ("JavaScript", "TypeScript")):
            if self._detect_js_tests(root):
                ctx.project.tests_detected = True
            else:
                findings.append(Finding(
                    category="Testing",
                    severity=Severity.MEDIUM,
                    title="No JavaScript/TypeScript tests detected",
                    message="No test files were found for JavaScript/TypeScript source.",
                    recommendation="Add tests using Jest, Vitest, or Mocha.",
                ))

        return findings

    def _detect_python_tests(self, root: Path) -> bool:
        # Check directories
        for d in ("tests", "test"):
            if (root / d).is_dir():
                py_files = list((root / d).rglob("*.py"))
                if py_files:
                    return True

        # Check for test files at root level
        test_files = list(root.glob("test_*.py")) + list(root.glob("*_test.py"))
        if test_files:
            return True

        # Check for conftest
        if (root / "conftest.py").exists():
            return True

        # Check pyproject.toml for pytest config
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text(errors="replace")
                if "pytest" in content:
                    return True
            except OSError:
                pass

        return False

    def _detect_js_tests(self, root: Path) -> bool:
        # Check __tests__ directory
        if (root / "__tests__").is_dir():
            return True

        # Check for test files
        for pattern in ("*.test.js", "*.test.ts", "*.spec.js", "*.spec.ts"):
            if list(root.rglob(pattern)):
                return True

        # Check for test config
        for cfg in ("jest.config.js", "jest.config.ts", "vitest.config.ts", ".mocharc.yml"):
            if (root / cfg).exists():
                return True

        return False
