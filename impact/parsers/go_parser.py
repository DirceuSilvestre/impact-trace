import re
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

from impact.ast_parser import calculate_file_hash
from impact.parsers.base import BaseLanguageParser


class GoLanguageParser(BaseLanguageParser):
    """
    Parser poliglota de dependências para Go (.go).
    Lê o go.mod do projeto para mapear o namespace do módulo para arquivos locais.
    """

    SINGLE_IMPORT_REGEX = re.compile(r'import\s+(?:[a-zA-Z0-9_]+\s+)?"([^"]+)"')
    MULTI_IMPORT_REGEX = re.compile(r'import\s*\(([\s\S]*?)\)')
    MODULE_PATH_REGEX = re.compile(r'^\s*module\s+([^\s]+)', re.MULTILINE)

    def __init__(self) -> None:
        self._cached_module_name: Optional[str] = None

    @property
    def supported_extensions(self) -> Set[str]:
        return {".go"}

    def parse_file(
        self, file_path: Path, project_root: Path
    ) -> Tuple[str, Dict[str, Any]]:
        file_hash = calculate_file_hash(file_path)
        rel_path = file_path.resolve().relative_to(project_root.resolve()).as_posix()

        module_name = self._get_go_module_name(project_root)
        runtime_imports: Set[str] = set()

        try:
            content = file_path.read_text(encoding="utf-8")

            # 1. Imports em bloco: import ( "pkg/a" "pkg/b" )
            for block in self.MULTI_IMPORT_REGEX.findall(content):
                for line in block.splitlines():
                    match = re.search(r'"([^"]+)"', line)
                    if match:
                        imp_path = match.group(1)
                        resolved = self._resolve_go_import(
                            imp_path, module_name, file_path, project_root
                        )
                        if resolved:
                            runtime_imports.add(resolved)

            # 2. Imports de linha única: import "pkg/a"
            for imp_path in self.SINGLE_IMPORT_REGEX.findall(content):
                resolved = self._resolve_go_import(
                    imp_path, module_name, file_path, project_root
                )
                if resolved:
                    runtime_imports.add(resolved)

            return rel_path, {
                "hash": file_hash,
                "runtime_imports": sorted(list(runtime_imports)),
                "type_checking_imports": [],
            }

        except (UnicodeDecodeError, OSError):
            return rel_path, {
                "hash": file_hash,
                "runtime_imports": [],
                "type_checking_imports": [],
                "has_error": True,
            }

    def _get_go_module_name(self, project_root: Path) -> Optional[str]:
        if self._cached_module_name:
            return self._cached_module_name

        go_mod = project_root / "go.mod"
        if go_mod.is_file():
            try:
                content = go_mod.read_text(encoding="utf-8")
                match = self.MODULE_PATH_REGEX.search(content)
                if match:
                    self._cached_module_name = match.group(1).strip()
                    return self._cached_module_name
            except OSError:
                pass
        return None

    def _resolve_go_import(
        self,
        import_path: str,
        module_name: Optional[str],
        current_file: Path,
        project_root: Path,
    ) -> Optional[str]:
        # 1. Import do próprio módulo Go local
        if module_name and import_path.startswith(module_name):
            rel_dir_str = import_path[len(module_name) :].lstrip("/")
            target_dir = project_root / rel_dir_str

            if target_dir.is_dir():
                # Em Go, pacotes são diretórios. Encontra arquivos .go dentro do pacote
                go_files = list(target_dir.glob("*.go"))
                if go_files:
                    return target_dir.relative_to(project_root.resolve()).as_posix()

        # 2. Import relativo local
        if import_path.startswith("."):
            target_dir = (current_file.parent / import_path).resolve()
            if target_dir.is_dir():
                return target_dir.relative_to(project_root.resolve()).as_posix()

        return None