import json
import subprocess
from pathlib import Path
from typer.testing import CliRunner
from impact.cli import app


def test_cli_init_creates_config(runner: CliRunner, tmp_path: Path):
    result = runner.invoke(app, ["init", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "inicializado com sucesso" in result.stdout
    assert (tmp_path / ".impact" / "config.json").is_file()


def test_cli_scan_generates_cache(runner: CliRunner, dummy_project: Path):
    result = runner.invoke(app, ["scan", "--root", str(dummy_project)])
    assert result.exit_code == 0
    assert "Escaneamento incremental concluído" in result.stdout
    assert (dummy_project / ".impact" / "cache.json").is_file()


def test_cli_analyze_text_format(runner: CliRunner, git_project: Path):
    # Executa o scan inicial
    runner.invoke(app, ["scan", "--root", str(git_project)])

    # Modifica o db.py
    (git_project / "db.py").write_text("class Database:\n    # Change\n    pass\n")

    result = runner.invoke(app, ["analyze", "--root", str(git_project)])
    assert result.exit_code == 0
    assert "db.py" in result.stdout


def test_cli_analyze_ai_json_format(runner: CliRunner, git_project: Path):
    runner.invoke(app, ["scan", "--root", str(git_project)])

    # Modifica o db.py
    (git_project / "db.py").write_text("class Database:\n    # Change\n    pass\n")

    result = runner.invoke(app, ["analyze", "--root", str(git_project), "--format", "ai-json"])
    assert result.exit_code == 0

    data = json.loads(result.stdout)
    assert "summary" in data
    assert "db.py" in data["changed_files"]
    assert "services.py" in data["impact_analysis"]["direct_impact"]


def test_cli_graph_generation(runner: CliRunner, dummy_project: Path):
    result = runner.invoke(app, ["graph", "--root", str(dummy_project), "--no-open"])
    assert result.exit_code == 0
    assert "Grafo Arquitetural Completo gerado com sucesso" in result.stdout
    assert (dummy_project / ".impact" / "graph.html").is_file()