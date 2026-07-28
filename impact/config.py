import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG: Dict[str, Any] = {
    "ignore_dirs": [
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".impact",
        ".pytest_cache",
        "build",
        "dist",
        ".egg-info",
        ".tox",
        ".mypy_cache",
    ]
}


def find_project_root(start_path: Path = Path(".")) -> Path:
    """
    Navega para cima no sistema de arquivos a partir do ponto de execução
    para encontrar a raiz real do projeto procurando por marcadores (.git, .impact, pyproject.toml).
    """
    current = start_path.resolve()
    if current.is_file():
        current = current.parent

    for parent in [current] + list(current.parents):
        if (
            (parent / ".git").exists()
            or (parent / ".impact").exists()
            or (parent / "pyproject.toml").exists()
            or (parent / "setup.py").exists()
        ):
            return parent

    return current


def load_config(project_root: Path = Path(".")) -> Dict[str, Any]:
    """
    Carrega as configurações do arquivo .impact/config.json na raiz informada.
    """
    root = project_root.resolve()
    config_file = root / ".impact" / "config.json"
    if config_file.is_file():
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
            return {**DEFAULT_CONFIG, **data}
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_CONFIG.copy()


def init_config(project_root: Path = Path(".")) -> Path:
    """
    Inicializa a pasta .impact e o arquivo config.json exatamente no diretório informado,
    sem navegar para cima na árvore de diretórios.
    """
    root = project_root.resolve()
    impact_dir = root / ".impact"
    impact_dir.mkdir(parents=True, exist_ok=True)
    config_file = impact_dir / "config.json"

    if not config_file.exists():
        config_file.write_text(
            json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return config_file