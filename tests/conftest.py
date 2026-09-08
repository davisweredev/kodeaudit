"""Shared test fixtures."""

import os

import pytest


@pytest.fixture
def tmp_project(tmp_path):
    """Create a minimal temporary project directory."""
    return tmp_path


@pytest.fixture
def python_project(tmp_path):
    """Create a temporary Python project with realistic structure."""
    # Source code
    src = tmp_path / "mypackage"
    src.mkdir()
    (src / "__init__.py").write_text('"""My package."""\n')
    (src / "core.py").write_text('''"""Core module."""

import os
import sys


def process_data(data):
    """Process input data."""
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result


class DataProcessor:
    """A data processor class."""

    def __init__(self, name):
        self.name = name
        self._data = []

    def add(self, item):
        self._data.append(item)

    def process(self):
        return process_data(self._data)
''')
    (src / "utils.py").write_text('''"""Utility functions."""

# TODO: refactor this module
# FIXME: handle edge cases


def helper(x, y, z, a, b, c, d):
    """Helper with too many params."""
    return x + y + z + a + b + c + d


print("utils loaded")
''')

    # Tests
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "__init__.py").write_text("")
    (tests / "test_core.py").write_text('''"""Tests for core module."""
from mypackage.core import process_data


def test_process_data():
    assert process_data([1, 2, 3]) == [2, 4, 6]


def test_empty():
    assert process_data([]) == []
''')

    # Config files
    (tmp_path / "pyproject.toml").write_text('''[project]
name = "mypackage"
version = "0.1.0"

[tool.pytest.ini_options]
testpaths = ["tests"]
''')
    (tmp_path / "requirements.txt").write_text("requests>=2.28.0\nflask>=2.0\n")
    (tmp_path / "README.md").write_text("# My Package\n\nA test package.\n")

    # Init git
    os.system(f"cd {tmp_path} && git init -q 2>/dev/null && git add -A && git commit -q -m 'init' 2>/dev/null")

    return tmp_path


@pytest.fixture
def js_project(tmp_path):
    """Create a temporary JavaScript project."""
    (tmp_path / "package.json").write_text('''{
  "name": "myapp",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.0.0",
    "express": "^4.18.0"
  }
}''')
    src = tmp_path / "src"
    src.mkdir()
    (src / "index.js").write_text('''const express = require('express');
const app = express();
app.listen(3000);
''')
    (src / "utils.js").write_text('''// TODO: implement
function helper() {
    return true;
}
module.exports = { helper };
''')
    return tmp_path


@pytest.fixture
def security_project(tmp_path):
    """Create a project with potential security issues."""
    src = tmp_path / "config"
    src.mkdir()
    stripe_key = "sk_" + "live_" + "abc123def456ghi789jkl012mno"
    (src / "settings.py").write_text(f'''"""Settings module."""

DATABASE_URL = "postgresql://user:password123@localhost/mydb"
API_KEY = "{stripe_key}"
SECRET_TOKEN = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
PASSWORD = "super_secret_password"
''')
    (tmp_path / ".env").write_text("SECRET_KEY=mysecretvalue123\n")
    return tmp_path
