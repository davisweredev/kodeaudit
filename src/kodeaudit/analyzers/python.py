"""Python AST-based analyzer."""

from __future__ import annotations

import ast
from pathlib import Path

from .base import AnalysisContext, BaseAnalyzer
from ..models import Finding, Severity


class PythonAnalyzer(BaseAnalyzer):
    name = "python"

    def __init__(self, large_function_lines: int = 50,
                 max_parameters: int = 6, max_nesting_depth: int = 4):
        self.LARGE_FUNCTION_LINES = large_function_lines
        self.VERY_LARGE_FUNCTION_LINES = 100
        self.CRITICAL_FUNCTION_LINES = 200
        self.MAX_PARAMETERS = max_parameters
        self.MAX_NESTING_DEPTH = max_nesting_depth

    def analyze(self, ctx: AnalysisContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in ctx.scan.files:
            if f.language != "Python":
                continue
            parts = f.relative_path.replace("\\", "/").split("/")
            if any(p in {"tests", "test", "__tests__", "fixtures"} for p in parts):
                continue
            file_findings = self._analyze_file(f.path, f.relative_path)
            findings.extend(file_findings)
        return findings

    def _analyze_file(self, path: Path, rel_path: str) -> list[Finding]:
        findings: list[Finding] = []
        try:
            source = path.read_text(errors="replace")
        except OSError:
            return findings

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as e:
            findings.append(Finding(
                category="Python",
                severity=Severity.MEDIUM,
                title="Syntax error",
                message=f"Python syntax error: {e.msg}",
                file=rel_path,
                line=e.lineno,
                recommendation="Fix the syntax error to enable full analysis.",
            ))
            return findings

        self._check_functions(tree, source, rel_path, findings)
        self._check_classes(tree, rel_path, findings)
        self._check_print_calls(tree, rel_path, findings)
        self._check_bare_except(tree, rel_path, findings)
        self._check_star_imports(tree, rel_path, findings)

        return findings

    def _check_functions(
        self,
        tree: ast.Module,
        source: str,
        rel_path: str,
        findings: list[Finding],
    ) -> None:
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            func_name = node.name
            end_line = getattr(node, "end_lineno", None) or node.lineno
            func_lines = end_line - node.lineno + 1

            if func_lines >= self.LARGE_FUNCTION_LINES:
                if func_lines >= self.CRITICAL_FUNCTION_LINES:
                    sev = Severity.HIGH
                else:
                    sev = Severity.MEDIUM

                prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                findings.append(Finding(
                    category="Python",
                    severity=sev,
                    title=f"{prefix}function `{func_name}` is {func_lines} lines",
                    message=f"Function '{func_name}' spans approximately {func_lines} lines.",
                    file=rel_path,
                    line=node.lineno,
                    recommendation="Split into smaller, focused functions.",
                ))

            all_args = self._count_parameters(node)
            if all_args > self.MAX_PARAMETERS:
                findings.append(Finding(
                    category="Python",
                    severity=Severity.LOW,
                    title=f"Function `{func_name}` has {all_args} parameters",
                    message=f"Function '{func_name}' accepts {all_args} parameters.",
                    file=rel_path,
                    line=node.lineno,
                    recommendation="Consider grouping related parameters into a dataclass or dict.",
                ))

            depth = self._max_nesting_depth(node)
            if depth > self.MAX_NESTING_DEPTH:
                findings.append(Finding(
                    category="Python",
                    severity=Severity.MEDIUM,
                    title=f"Deep nesting in `{func_name}` (depth {depth})",
                    message=f"Function '{func_name}' has nesting depth of {depth}.",
                    file=rel_path,
                    line=node.lineno,
                    recommendation="Reduce nesting by extracting guard clauses or helper functions.",
                ))

    def _count_parameters(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        count = 0
        args = node.args
        regular = args.args
        if regular:
            start = 1 if regular[0].arg in ("self", "cls") else 0
            count += len(regular) - start
        count += len(args.posonlyargs)
        count += len(args.kwonlyargs)
        if args.vararg:
            count += 1
        if args.kwarg:
            count += 1
        return count

    def _max_nesting_depth(self, node: ast.AST) -> int:
        nesting_types = {ast.If, ast.For, ast.While, ast.Try, ast.With, ast.AsyncWith}
        max_depth = 0

        def _walk(n: ast.AST, depth: int) -> None:
            nonlocal max_depth
            if type(n) in nesting_types:
                depth += 1
            if depth > max_depth:
                max_depth = depth
            for child in ast.iter_child_nodes(n):
                _walk(child, depth)

        _walk(node, 0)
        return max_depth

    def _check_classes(self, tree: ast.Module, rel_path: str, findings: list[Finding]) -> None:
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if len(methods) > 20:
                findings.append(Finding(
                    category="Python",
                    severity=Severity.MEDIUM,
                    title=f"Large class `{node.name}` ({len(methods)} methods)",
                    message=f"Class '{node.name}' has {len(methods)} methods.",
                    file=rel_path,
                    line=node.lineno,
                    recommendation="Consider splitting responsibilities into separate classes.",
                ))

    def _check_print_calls(self, tree: ast.Module, rel_path: str, findings: list[Finding]) -> None:
        print_locations: list[int] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if self._is_print_call(node):
                print_locations.append(getattr(node, "lineno", 0))

        if not print_locations:
            return

        # One finding per file to avoid noise: report the count.
        count = len(print_locations)
        if count <= 2:
            sev = Severity.INFO
            title = "print() call detected"
            message = "A print() call was detected. Consider using logging instead."
        else:
            sev = Severity.LOW
            title = f"Multiple print() calls ({count})"
            message = f"{count} print() calls were detected in this file. " \
                      "Likely debugging output or CLI code that could use logging."

        findings.append(Finding(
            category="Python",
            severity=sev,
            title=title,
            message=message,
            file=rel_path,
            line=print_locations[0],
            recommendation="Use the logging module for application output.",
        ))

    def _is_print_call(self, node: ast.Call) -> bool:
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            return True
        if isinstance(node.func, ast.Attribute) and node.func.attr == "print":
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "sys":
                return False
            return True
        return False

    def _check_bare_except(self, tree: ast.Module, rel_path: str, findings: list[Finding]) -> None:
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if node.type is None:
                findings.append(Finding(
                    category="Python",
                    severity=Severity.MEDIUM,
                    title="Bare except clause",
                    message="A bare 'except:' clause catches all exceptions including "
                            "KeyboardInterrupt and SystemExit.",
                    file=rel_path,
                    line=getattr(node, "lineno", None),
                    recommendation="Catch specific exception types instead.",
                ))

    def _check_star_imports(self, tree: ast.Module, rel_path: str, findings: list[Finding]) -> None:
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            for alias in node.names:
                if alias.name == "*":
                    findings.append(Finding(
                        category="Python",
                        severity=Severity.LOW,
                        title="Wildcard import",
                        message=f"Wildcard import from '{node.module}' pollutes the namespace.",
                        file=rel_path,
                        line=getattr(node, "lineno", None),
                        recommendation="Import specific names instead.",
                    ))
