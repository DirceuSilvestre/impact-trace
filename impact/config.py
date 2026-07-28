import json
from pathlib import Path
from typing import Any, Dict

# Nome da pasta oculta de configuração e do arquivo dentro do projeto
IMPACT_DIR_NAME = ".impact"
CONFIG_FILE_NAME = "config.json"

# Configuração padrão que será gravada no primeiro 'impact init'
DEFAULT_CONFIG: Dict[str, Any] = {
    "version": "1.0",
    "ignore_patterns": [
        ".git/*",
        ".impact/*",
        "venv/*",
        ".venv/*",
        "env/*",
        "__pycache__/*",
        "*.pyc",
        ".pytest_cache/*",
        ".mypy_cache/*",
        "build/*",
        "dist/*",
        "*.egg-info/*"
    ],
    "default_mode": "cli",
    "max_depth": 5,
    "cache_file": ".impact/cache.json"
}


def get_impact_dir(project_root: Path = Path(".")) -> Path:
    """
    Retorna o caminho absoluto do diretório .impact do projeto.
    """
    return project_root.resolve() / IMPACT_DIR_NAME


def get_config_path(project_root: Path = Path(".")) -> Path:
    """
    Retorna o caminho absoluto do arquivo .impact/config.json.
    """
    return get_impact_dir(project_root) / CONFIG_FILE_NAME


def init_config(project_root: Path = Path(".")) -> Path:
    """
    Cria a pasta .impact/ e o arquivo config.json com as regras padrão,
    caso ainda não existam.

    Returns:
        Path: O caminho absoluto do arquivo config.json gerado.
    """
    impact_dir = get_impact_dir(project_root)
    config_path = get_config_path(project_root)

    # 1. Cria a pasta .impact/ se ela não existir
    impact_dir.mkdir(parents=True, exist_ok=True)

    # 2. Cria o arquivo config.json padrão apenas se não existir (para não sobrescrever edições do usuário)
    if not config_path.exists():
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)

    return config_path


def load_config(project_root: Path = Path(".")) -> Dict[str, Any]:
    """
    Carrega as configurações salvas em .impact/config.json.
    Se o arquivo não existir, inicializa com os padrões automaticamente.

    Returns:
        dict: O dicionário com as configurações lidas.
    """
    config_path = get_config_path(project_root)

    # Se o usuário tentar carregar sem ter inicializado, cria automaticamente
    if not config_path.exists():
        init_config(project_root)

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)