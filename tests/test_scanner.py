"""Tests for the file scanner."""

from kodeaudit.scanner import scan_project
from kodeaudit import scanner


def test_ignored_directories(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hi')\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "dep.js").write_text("console.log('x')\n")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "x.pyc").write_bytes(b"\x00")

    result = scan_project(tmp_path)
    files = [f.relative_path for f in result.files]
    assert "src/main.py" in files
    assert not any("node_modules" in f for f in files)
    assert not any("__pycache__" in f for f in files)


def test_custom_ignored_dirs(tmp_path):
    (tmp_path / "weird_dir").mkdir()
    (tmp_path / "weird_dir" / "file.py").write_text("x = 1\n")
    result = scan_project(tmp_path, extra_ignored_dirs={"weird_dir"})
    assert not any("weird_dir" in f.relative_path for f in result.files)


def test_source_line_count(tmp_path):
    (tmp_path / "main.py").write_text("a = 1\nb = 2\nc = 3\n")
    result = scan_project(tmp_path)
    assert len(result.files) == 1
    assert result.files[0].line_count == 3


def test_language_mapping():
    assert scanner.get_language(".py") == "Python"
    assert scanner.get_language(".PY") == "Python"
    assert scanner.get_language(".js") == "JavaScript"
    assert scanner.get_language(".ts") == "TypeScript"
    assert scanner.get_language(".txt") is None


def test_binary_file_skipped_for_line_count(tmp_path):
    (tmp_path / "data.py").write_bytes(b"\x00\x01\x02\x03" * 50)
    result = scan_project(tmp_path)
    # Binary file still listed but line_count should be None
    assert len(result.files) == 1
    assert result.files[0].line_count is None
