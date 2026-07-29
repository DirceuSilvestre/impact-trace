import re
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

from impact.parsers.base import BaseLanguageParser
from impact.utils import calculate_file_hash


class RustLanguageParser(BaseLanguageParser):
    """
    Parser poliglota de dependências para Rust (.rs).
    """

    MOD_REGEX = re.compile(r'mod\s+([a-zA-Z0-9_]+)\s*;')
    USE_CRATE_REGEX = re.compile(r'use\s+crate::([a-zA-Z0-9_:]+)')

    @property
    def supported_extensions(self) -> Set[str]:
        return {".rs"}

    def parse_file(
        self, file_path: Path, project_root: Path
    ) -> Tuple[str, Dict[str, Any]]:
        file_hash = calculate_file_hash(file_path)
        rel_path = file_path.resolve().relative_to(project_root.resolve()).as_posix()

        runtime_imports: Set[str] = set()

        try:
            content = file_path.read_text(encoding="utf-8")

            # 1. Declarações de submódulos: mod auth;
            for mod_name in self.MOD_REGEX.findall(content):
                resolved = self._resolve_rust_module(
                    mod_name, file_path.parent, project_root
                )
                if resolved:
                    runtime_imports.add(resolved)

            # 2. Re-uso de módulos internos: use crate::models::User;
            for crate_path in self.USE_CRATE_REGEX.findall(content):
                resolved = self._resolve_rust_path(crate_path, project_root)
                if resolved and resolved != rel_path:
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

    def _resolve_rust_module(
        self, mod_name: str, current_dir: Path, project_root: Path
    ) -> Optional[str]:
        file_candidate = current_dir / f"{mod_name}.rs"
        if file_candidate.is_file():
            return file_candidate.relative_to(project_root.resolve()).as_posix()

        folder_candidate = current_dir / mod_name / "mod.rs"
        if folder_candidate.is_file():
            return folder_candidate.relative_to(project_root.resolve()).as_posix()

        return None

    def _resolve_rust_path(
        self, crate_import_path: str, project_root: Path
    ) -> Optional[str]:
        """
        Resolve caminhos 'crate::a::b::Item'.
        Realiza busca regressiva: testa o caminho completo e, se for um item/struct,
        remove o último segmento para localizar o módulo hospedeiro (ex: mod.rs ou .rs).
        """
        src_dir = project_root / "src"
        parts = crate_import_path.split("::")

        while parts:
            sub_path = "/".join(parts)

            file_candidate = src_dir / f"{sub_path}.rs"
            if file_candidate.is_file():
                return file_candidate.relative_to(project_root.resolve()).as_posix()

            folder_candidate = src_dir / sub_path / "mod.rs"
            if folder_candidate.is_file():
                return folder_candidate.relative_to(project_root.resolve()).as_posix()

            # Descarta o último elemento (ex: nome de struct/função/enum) e tenta o módulo pai
            parts.pop()

        return None