from pathlib import Path
from impact.ast_parser import parse_python_file, scan_project_incremental


def test_parse_python_file_extracts_imports(tmp_path: Path):
    # O parser valida se a dependência interna existe fisicamente no projeto
    (tmp_path / "services.py").write_text("user_service = None\n", encoding="utf-8")

    file_path = tmp_path / "app.py"
    file_path.write_text(
        "import os\nfrom services import user_service\n", encoding="utf-8"
    )

    rel_path, data = parse_python_file(file_path, tmp_path)

    assert rel_path == "app.py"
    assert "hash" in data
    assert len(data["hash"]) == 64  # Hash SHA-256 válido
    assert data["runtime_imports"] == ["services.py"]


def test_parse_python_file_handles_syntax_error(tmp_path: Path):
    file_path = tmp_path / "broken.py"
    file_path.write_text("def invalid_syntax(:", encoding="utf-8")

    rel_path, data = parse_python_file(file_path, tmp_path)

    assert rel_path == "broken.py"
    assert data.get("has_error") is True
    assert data["runtime_imports"] == []


def test_scan_project_incremental_ignores_venv_and_git(dummy_project: Path):
    # Cria pasta venv simulada
    venv_dir = dummy_project / ".venv"
    venv_dir.mkdir()
    (venv_dir / "lib.py").write_text("import os", encoding="utf-8")

    project_map, stats = scan_project_incremental(dummy_project)

    assert ".venv/lib.py" not in project_map
    assert "main.py" in project_map
    assert stats["total_files"] == 4