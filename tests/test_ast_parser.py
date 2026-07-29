from pathlib import Path
from impact.ast_parser import parse_python_file, scan_project_incremental


def test_parse_python_file_direct(tmp_path: Path):
    project_root = tmp_path
    py_file = project_root / "app.py"
    py_file.write_text("import sys\nfrom pathlib import Path", encoding="utf-8")

    rel_path, file_data = parse_python_file(py_file, project_root)

    assert rel_path == "app.py"
    assert "hash" in file_data
    assert isinstance(file_data["runtime_imports"], list)


def test_scan_project_incremental_basic(tmp_path: Path):
    project_root = tmp_path
    (project_root / "main.py").write_text("print('hello')", encoding="utf-8")

    project_map, stats = scan_project_incremental(project_root)

    assert stats["total_files"] == 1
    assert "main.py" in project_map