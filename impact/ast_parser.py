import ast
import fnmatch
from pathlib import Path
from typing import Dict, List, Set

from impact.config import load_config


def parse_file_imports(file_path: Path) -> List[str]:
    """
    Lê um arquivo .py, analisa sua AST (Abstract Syntax Tree) e extrai
    todas as dependências importadas (via 'import' ou 'from ... import').

    Args:
        file_path (Path): Caminho do arquivo .py a ser analisado.

    Returns:
        List[str]: Lista ordenada com os nomes dos módulos/arquivos importados.
    """
    if not file_path.exists() or file_path.suffix != ".py":
        return []

    imported_modules: Set[str] = set()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.add(node.module)
                elif node.level > 0:
                    imported_modules.add("." * node.level)

    except SyntaxError:
        pass
    except Exception:
        pass

    return sorted(list(imported_modules))


def _should_ignore(relative_path: Path, ignore_patterns: List[str]) -> bool:
    """
    Verifica se um determinado caminho deve ser ignorado com base nas regras de ignore_patterns.
    """
    path_str = relative_path.as_posix()  # Normaliza barras para formato padrão '/'
    
    for pattern in ignore_patterns:
        # Se for um padrão de diretório tipo "venv/*" ou "*.pyc"
        clean_pattern = pattern.rstrip("/")
        if fnmatch.fnmatch(path_str, pattern) or fnmatch.fnmatch(path_str, clean_pattern):
            return True
        # Verifica se alguma pasta pai bate com o padrão ignorado (ex: venv/lib/site-packages)
        for part in relative_path.parts:
            if fnmatch.fnmatch(part, clean_pattern):
                return True
    return False


def _resolve_module_to_path(module_name: str, root_dir: Path) -> str | None:
    """
    Tenta resolver um nome de módulo importado (ex: 'impact.config') para o caminho
    relativo do arquivo físico correspondente no projeto (ex: 'impact/config.py').
    """
    # Converter notação de ponto para caminho (ex: 'impact.config' -> 'impact/config')
    relative_str = module_name.replace(".", "/")
    
    # 1. Tenta como um arquivo Python (.py)
    candidate_file = root_dir / f"{relative_str}.py"
    if candidate_file.exists():
        return candidate_file.relative_to(root_dir).as_posix()
        
    # 2. Tenta como um pacote Python (diretório contendo __init__.py)
    candidate_init = root_dir / relative_str / "__init__.py"
    if candidate_init.exists():
        return candidate_init.relative_to(root_dir).as_posix()

    # Se for uma biblioteca externa (ex: 'rich', 'typer', 'sys'), retorna None
    return None


def scan_project(root_dir: Path = Path(".")) -> Dict[str, List[str]]:
    """
    Percorre todo o projeto, identifica os arquivos .py respeitando as regras de ignore,
    e constrói o mapa de dependências entre os arquivos locais.

    Args:
        root_dir (Path): O diretório raiz do projeto.

    Returns:
        Dict[str, List[str]]: Dicionário no formato { "arquivo_origem.py": ["dependencia1.py", "dependencia2.py"] }
    """
    root_dir = root_dir.resolve()
    config = load_config(root_dir)
    ignore_patterns = config.get("ignore_patterns", [])

    project_map: Dict[str, List[str]] = {}

    # Percorre recursivamente todos os arquivos a partir da raiz
    for file_path in root_dir.rglob("*.py"):
        relative_path = file_path.relative_to(root_dir)

        # 1. Aplica o filtro de ignore
        if _should_ignore(relative_path, ignore_patterns):
            continue

        file_key = relative_path.as_posix()
        raw_imports = parse_file_imports(file_path)

        resolved_dependencies: Set[str] = set()

        # 2. Resolve quais imports pertencem ao projeto e descarta libs externas da linguagem
        for imp in raw_imports:
            resolved_path = _resolve_module_to_path(imp, root_dir)
            if resolved_path and resolved_path != file_key:
                resolved_dependencies.add(resolved_path)

        project_map[file_key] = sorted(list(resolved_dependencies))

    return project_map