"""Project detector — identifies languages, frameworks, and project type."""

from __future__ import annotations

from pathlib import Path

from .models import ProjectInfo
from .scanner import ScanResult


# Framework detection signals: (indicator_file_or_pattern, framework_name)
_PYTHON_FRAMEWORKS = [
    ("manage.py", "Django"),
    ("wsgi.py", "Django"),
    ("asgi.py", "Django"),
    ("pyproject.toml:fastapi", "FastAPI"),
    ("pyproject.toml:flask", "Flask"),
    ("requirements.txt:django", "Django"),
    ("requirements.txt:flask", "Flask"),
    ("requirements.txt:fastapi", "FastAPI"),
]

_JS_FRAMEWORKS = [
    ("next.config.js", "Next.js"),
    ("next.config.mjs", "Next.js"),
    ("next.config.ts", "Next.js"),
    ("nuxt.config.js", "Nuxt.js"),
    ("nuxt.config.ts", "Nuxt.js"),
    ("nuxt.config.mjs", "Nuxt.js"),
    ("angular.json", "Angular"),
    ("vue.config.js", "Vue"),
    ("vite.config.js", "Vite"),
    ("vite.config.ts", "Vite"),
    ("vite.config.mjs", "Vite"),
    ("svelte.config.js", "Svelte"),
]

_DOCKER_INDICATORS = [
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".dockerignore",
]


def _read_file_safe(path: Path, max_bytes: int = 65536) -> str:
    """Read a file safely, returning empty string on failure."""
    try:
        return path.read_text(errors="replace")[:max_bytes]
    except (OSError, UnicodeDecodeError):
        return ""


def _detect_frameworks(root: Path) -> list[str]:
    """Detect frameworks from project files and content."""
    detected: list[str] = []
    seen: set[str] = set()

    # Python frameworks
    for indicator, name in _PYTHON_FRAMEWORKS:
        if ":" in indicator:
            fname, search = indicator.split(":", 1)
            fp = root / fname
            if fp.exists() and search in _read_file_safe(fp):
                if name not in seen:
                    detected.append(name)
                    seen.add(name)
        else:
            if (root / indicator).exists():
                if name not in seen:
                    detected.append(name)
                    seen.add(name)

    # JS/TS frameworks
    for indicator, name in _JS_FRAMEWORKS:
        if (root / indicator).exists():
            if name not in seen:
                detected.append(name)
                seen.add(name)

    # Check package.json for deeper signals
    pkg_json = root / "package.json"
    if pkg_json.exists():
        content = _read_file_safe(pkg_json)
        checks = [
            ("next", "Next.js"),
            ("nuxt", "Nuxt.js"),
            ("@angular/core", "Angular"),
            ("vue", "Vue"),
            ("react", "React"),
            ("svelte", "Svelte"),
            ("express", "Express"),
            ("@nestjs", "NestJS"),
            ("fastify", "Fastify"),
        ]
        for keyword, name in checks:
            if f'"{keyword}"' in content or f"'{keyword}'" in content:
                if name not in seen:
                    detected.append(name)
                    seen.add(name)

    return detected


def detect_project(root: str | Path, scan: ScanResult) -> ProjectInfo:
    """Detect project type from scan results."""
    root = Path(root).resolve()
    info = ProjectInfo(root=str(root))

    # Language detection by file extension
    lang_counts: dict[str, int] = {}
    for f in scan.files:
        if f.language:
            lang_counts[f.language] = lang_counts.get(f.language, 0) + 1

    total = sum(lang_counts.values())
    if total > 0:
        info.languages = {
            lang: round(count / total * 100, 1)
            for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1])
        }

    # Frameworks
    info.frameworks = _detect_frameworks(root)

    # Docker
    for indicator in _DOCKER_INDICATORS:
        if (root / indicator).exists():
            info.has_docker = True
            break

    # CI detection
    ci_paths = [
        ".github/workflows",
        ".gitlab-ci.yml",
        ".circleci",
        "Jenkinsfile",
        ".travis.yml",
    ]
    for p in ci_paths:
        if (root / p).exists():
            info.has_ci = True
            break

    # Git
    info.has_git = (root / ".git").exists()

    return info
