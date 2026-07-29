import ast
import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from impact.parsers.python_parser import PythonLanguageParser
from impact.parsers.registry import registry
from impact.parsers.ts_js_parser import TSJSModuleParser

# Registra os Parsers Nativos
registry.register(PythonLanguageParser())
registry.register(TSJSModuleParser())


def calculate_file_hash(file_path: Path) -> str:
    """
    Calcula o hash SHA-256 do conteúdo do arquivo em blocos de 64KB.
    """
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
    except OSError:
        return ""


class EnhancedASTDependencyVisitor(ast.NodeVisitor):
    """
    Visitor da AST otimizado para extração de dependências locais com suporte a:
    - Imports relativos (. e ..)
    - Distinção entre dependências de Runtime vs TYPE_CHECKING
    - Re-exports de __init__.py
    """

    def __init__(self, file_path: Path, project_root: Path) -> None:
        self.file_path = file_path.resolve()
        self.project_root = project_root.resolve()
        self.file_relative_path = self.file_path.relative_to(self.project_root)

        self.runtime_imports: Set[str] = set()
        self.type_checking_imports: Set[str] = set()
        self._in_type_checking_block: bool = False

    def visit_If(self, node: ast.If) -> None:
        is_type_checking = self._is_type_checking_guard(node.test)
        prev_state = self._in_type_checking_block

        if is_type_checking:
            self._in_type_checking_block = True

        self.generic_visit(node)
        self._in_type_checking_block = prev_state

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            resolved = self._resolve_absolute_import(alias.name)
            if resolved:
                self._add_dependency(resolved)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module_name = node.module or ""
        level = node.level

        if level > 0:
            resolved = self._resolve_relative_import(module_name, level, [a.name for a in node.names])
            for dep in resolved:
                self._add_dependency(dep)
        else:
            resolved = self._resolve_from_import(module_name, [a.name for a in node.names])
            for dep in resolved:
                self._add_dependency(dep)

    def _add_dependency(self, dep_path: str) -> None:
        if dep_path == self.file_relative_path.as_posix():
            return

        if self._in_type_checking_block:
            self.type_checking_imports.add(dep_path)
        else:
            self.runtime_imports.add(dep_path)

    def _is_type_checking_guard(self, test_node: ast.expr) -> bool:
        if isinstance(test_node, ast.Name) and test_node.id == "TYPE_CHECKING":
            return True
        if isinstance(test_node, ast.Attribute) and test_node.attr == "TYPE_CHECKING":
            return True
        return False

    def _resolve_relative_import(
        self, module: str, level: int, imported_names: List[str]
    ) -> Set[str]:
        results: Set[str] = set()
        base_dir = self.file_path.parent

        for _ in range(level - 1):
            if base_dir != self.project_root:
                base_dir = base_dir.parent

        target_base = base_dir
        if module:
            target_base = base_dir.joinpath(*module.split("."))

        py_file = target_base.with_suffix(".py")
        if py_file.is_file():
            results.add(py_file.relative_to(self.project_root).as_posix())
            return results

        init_file = target_base / "__init__.py"
        if init_file.is_file():
            results.add(init_file.relative_to(self.project_root).as_posix())

        for name in imported_names:
            submodule_py = target_base / f"{name}.py"
            if submodule_py.is_file():
                results.add(submodule_py.relative_to(self.project_root).as_posix())
            else:
                submodule_init = target_base / name / "__init__.py"
                if submodule_init.is_file():
                    results.add(submodule_init.relative_to(self.project_root).as_posix())

        return results

    def _resolve_absolute_import(self, module_path: str) -> Optional[str]:
        parts = module_path.split(".")
        candidate = self.project_root.joinpath(*parts)

        py_file = candidate.with_suffix(".py")
        if py_file.is_file():
            return py_file.relative_to(self.project_root).as_posix()

        init_file = candidate / "__init__.py"
        if init_file.is_file():
            return init_file.relative_to(self.project_root).as_posix()

        return None

    def _resolve_from_import(self, module: str, imported_names: List[str]) -> Set[str]:
        results: Set[str] = set()

        if module:
            base_resolved = self._resolve_absolute_import(module)
            if base_resolved:
                results.add(base_resolved)

            mod_parts = module.split(".")
            for name in imported_names:
                sub_candidate = self.project_root.joinpath(*mod_parts, f"{name}.py")
                if sub_candidate.is_file():
                    results.add(sub_candidate.relative_to(self.project_root).as_posix())
                else:
                    sub_init = self.project_root.joinpath(*mod_parts, name, "__init__.py")
                    if sub_init.is_file():
                        results.add(sub_init.relative_to(self.project_root).as_posix())

        return results


def parse_python_file(file_path: Path, project_root: Path) -> Tuple[Dict[str, Any], str]:
    """
    Parseia um único arquivo Python e retorna o mapa de dependências + Hash SHA-256.
    """
    file_hash = calculate_file_hash(file_path)
    rel_path = file_path.resolve().relative_to(project_root.resolve()).as_posix()

    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
        visitor = EnhancedASTDependencyVisitor(file_path, project_root)
        visitor.visit(tree)

        file_data = {
            "hash": file_hash,
            "runtime_imports": sorted(list(visitor.runtime_imports)),
            "type_checking_imports": sorted(list(visitor.type_checking_imports)),
        }
        return rel_path, file_data

    except (SyntaxError, UnicodeDecodeError, OSError):
        return rel_path, {
            "hash": file_hash,
            "runtime_imports": [],
            "type_checking_imports": [],
            "has_error": True,
        }


def scan_project_incremental(
    project_root: Path,
    existing_cache: Optional[Dict[str, Any]] = None,
    ignore_dirs: Optional[Set[str]] = None,
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """
    Escaneia o projeto de forma INCREMENTAL e ULTRA-RÁPIDA ($O(N)$).
    Utiliza os.walk com PODA ATIVA no nível do Sistema Operacional.
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
            ".egg-info",
            ".tox",
            ".mypy_cache",
        }

    cached_files = existing_cache.get("files", {}) if existing_cache else {}
    new_project_map: Dict[str, Any] = {}

    stats = {"cache_hits": 0, "reparsed": 0, "total_files": 0}

    # PODA ATIVA: topdown=True + dirs[:] modifica a busca em tempo real.
    # O Python NUNCA entrará em subpastas ignoradas ou ocultas.
    for root, dirs, files in os.walk(project_root, topdown=True, followlinks=False):
        # Filtra subdiretórios em tempo de varredura
        dirs[:] = [
            d for d in dirs
            if d not in ignore_dirs and not d.startswith(".")
        ]

        for file_name in files:
            if not file_name.endswith(".py"):
                continue

            py_file = Path(root) / file_name
            rel_path = py_file.relative_to(project_root).as_posix()

            stats["total_files"] += 1
            current_hash = calculate_file_hash(py_file)

            # Reutiliza o cache se o Hash SHA-256 for idêntico
            if rel_path in cached_files and cached_files[rel_path].get("hash") == current_hash:
                new_project_map[rel_path] = cached_files[rel_path]
                stats["cache_hits"] += 1
            else:
                _, file_data = parse_python_file(py_file, project_root)
                new_project_map[rel_path] = file_data
                stats["reparsed"] += 1

    return new_project_map, stats