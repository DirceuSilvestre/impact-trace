import os
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

from impact.parsers import registry
from impact.parsers.python_parser import PythonLanguageParser
from impact.utils import calculate_file_hash


def parse_python_file(file_path: Path, project_root: Path) -> Tuple[str, Dict[str, Any]]:
    """
    Wrapper de compatibilidade para parsear um único arquivo Python.
    Delega a execução diretamente para o PythonLanguageParser.
    """
    parser = PythonLanguageParser()
    return parser.parse_file(file_path, project_root)


def scan_project_incremental(
    project_root: Path,
    existing_cache: Optional[Dict[str, Any]] = None,
    ignore_dirs: Optional[Set[str]] = None,
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """
    Escaneia o projeto de forma INCREMENTAL e ULTRA-RÁPIDA (O(N)).
    Aplica o registro poliglota para identificar e parsear múltiplos tipos de arquivo.
    """
    project_root = project_root.resolve()
    if ignore_dirs is None:
        ignore_dirs = {
            ".git",
            ".venv",
            "venv",
            "__pycache__",
            ".impact",
            ".pytest_cache",
            "build",
            "dist",
            "node_modules",
            "target",
            "vendor",
        }

    cached_files = existing_cache.get("files", {}) if existing_cache else {}
    new_project_map: Dict[str, Any] = {}
    stats = {"cache_hits": 0, "reparsed": 0, "total_files": 0}

    for root, dirs, files in os.walk(project_root, topdown=True, followlinks=False):
        dirs[:] = [
            d for d in dirs
            if d not in ignore_dirs and not d.startswith(".")
        ]

        for file_name in files:
            file_path = Path(root) / file_name

            # Obtém o parser correspondente à extensão do arquivo
            parser = registry.get_parser_for_file(file_path)
            if not parser:
                continue

            rel_path = file_path.relative_to(project_root).as_posix()
            stats["total_files"] += 1
            current_hash = calculate_file_hash(file_path)

            if rel_path in cached_files and cached_files[rel_path].get("hash") == current_hash:
                new_project_map[rel_path] = cached_files[rel_path]
                stats["cache_hits"] += 1
            else:
                _, file_data = parser.parse_file(file_path, project_root)
                new_project_map[rel_path] = file_data
                stats["reparsed"] += 1

    return new_project_map, stats