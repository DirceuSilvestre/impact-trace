from pathlib import Path
import subprocess
import pytest
from typer.testing import CliRunner
from impact.parsers.registry import ParserRegistry, registry


@pytest.fixture(autouse=True)
def reset_registry_state():
    """Garante que o estado do registro de parsers seja resetado a cada teste."""
    yield registry


@pytest.fixture
def runner() -> CliRunner:
    """Fixture do Test Runner do Typer para invocar comandos da CLI em ambiente isolado."""
    return CliRunner()


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Cria um diretório temporário para testes gerais."""
    project_dir = tmp_path / "monorepo"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def dummy_project(tmp_path: Path) -> Path:
    """Cria a estrutura de um projeto simples para os testes da CLI sem dependência de Git."""
    project_dir = tmp_path / "dummy_project"
    project_dir.mkdir()

    (project_dir / "main.py").write_text("import sys\nprint('Hello')", encoding="utf-8")
    (project_dir / "utils.py").write_text("def add(a, b): return a + b", encoding="utf-8")

    return project_dir


@pytest.fixture
def git_project(tmp_path: Path) -> Path:
    """
    Cria um repositório Git REAL e isolado com relações de dependência no grafo.
    Relação: main.py -> services.py -> db.py
    """
    project_dir = tmp_path / "git_project"
    project_dir.mkdir()

    # 1. Estrutura de código com dependências mapeáveis pela AST
    (project_dir / "db.py").write_text("class Database:\n    pass\n", encoding="utf-8")
    
    (project_dir / "services.py").write_text(
        "from db import Database\n\n"
        "def get_service():\n"
        "    return Database()\n",
        encoding="utf-8"
    )
    
    (project_dir / "utils.py").write_text("def add(a, b): return a + b", encoding="utf-8")
    
    (project_dir / "main.py").write_text(
        "from utils import add\n"
        "from services import get_service\n\n"
        "print(add(1, 2))\n",
        encoding="utf-8"
    )

    # 2. Inicialização e commit base do Git
    subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_dir, check=True, capture_output=True)

    return project_dir