import subprocess
from pathlib import Path
import pytest
from typer.testing import CliRunner

from impact.cli import app


@pytest.fixture
def runner() -> CliRunner:
    """Retorna o executor de comandos CLI do Typer."""
    return CliRunner()


@pytest.fixture
def dummy_project(tmp_path: Path) -> Path:
    """
    Cria uma árvore de arquivos Python simulando dependências:
    
    main.py -> services.py -> db.py
    utils.py (isolado)
    """
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()

    # db.py
    (project_dir / "db.py").write_text(
        "class Database:\n    pass\n", encoding="utf-8"
    )

    # services.py (importa db)
    (project_dir / "services.py").write_text(
        "import db\n\ndef get_user():\n    return db.Database()\n", encoding="utf-8"
    )

    # main.py (importa services)
    (project_dir / "main.py").write_text(
        "import services\n\nprint(services.get_user())\n", encoding="utf-8"
    )

    # utils.py (sem dependências ativas)
    (project_dir / "utils.py").write_text(
        "def add(a, b):\n    return a + b\n", encoding="utf-8"
    )

    return project_dir


@pytest.fixture
def git_project(dummy_project: Path) -> Path:
    """Inicializa um repositório Git real dentro do diretório temporário do teste."""
    subprocess.run(["git", "init"], cwd=dummy_project, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "QA Tester"], cwd=dummy_project, check=True)
    subprocess.run(["git", "config", "user.email", "tester@impact.local"], cwd=dummy_project, check=True)
    subprocess.run(["git", "add", "."], cwd=dummy_project, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=dummy_project, check=True)
    return dummy_project