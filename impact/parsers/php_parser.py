import re
from pathlib import Path
from typing import Any, Dict, Set, Tuple

from impact.ast_parser import calculate_file_hash
from impact.parsers.base import BaseLanguageParser


class PHPLanguageParser(BaseLanguageParser):
    """
    Parser poliglota de dependências para PHP (.php).
    Suporta Namespaces PSR-4 e instruções require/include.
    """

    USE_REGEX = re.compile(r'use\s+([a-zA-Z0-9_\\]+)\s*;')
    REQUIRE_REGEX = re.compile(
        r'(?:require|include)(?:_once)?\s*\(?\s*[\'"]([^\'"]+)[\'"]'
    )

    @property
    def supported_extensions(self) -> Set[str]:
        return {".php"}

    def parse_file(
        self, file_path: Path, project_root: Path
    ) -> Tuple[str, Dict[str, Any]]:
        file_hash = calculate_file_hash(file_path)
        rel_path = file_path.resolve().relative_to(project_root.resolve()).as_posix()

        runtime_imports: Set[str] = set()

        try:
            content = file_path.read_text(encoding="utf-8")

            # 1. Namespaces PSR-4: use App\Models\User;
            for ns in self.USE_REGEX.findall(content):
                resolved = self._resolve_psr4_import(ns, project_root)
                if resolved and resolved != rel_path:
                    runtime_imports.add(resolved)

            # 2. Inclusões diretas: require_once 'helpers.php';
            for req in self.REQUIRE_REGEX.findall(content):
                resolved = self._resolve_direct_include(
                    req, file_path.parent, project_root
                )
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

    def _resolve_psr4_import(
        self, use_statement: str, project_root: Path
    ) -> str | None:
        # App\Services\UserService -> Services/UserService
        parts = use_statement.split("\\")
        if not parts:
            return None

        # Mapeamento PSR-4 padrão: 'App\' -> 'app/' ou 'src/'
        if parts[0] == "App":
            sub_path = "/".join(parts[1:])
            for base in ["app", "src"]:
                candidate = project_root / base / f"{sub_path}.php"
                if candidate.is_file():
                    return candidate.relative_to(project_root.resolve()).as_posix()

        # Resolução direta por caminho relativo no projeto
        direct_path = project_root / f"{'/'.join(parts)}.php"
        if direct_path.is_file():
            return direct_path.relative_to(project_root.resolve()).as_posix()

        return None

    def _resolve_direct_include(
        self, include_path: str, current_dir: Path, project_root: Path
    ) -> str | None:
        target = (current_dir / include_path).resolve()
        if target.is_file() and target.exists():
            try:
                return target.relative_to(project_root.resolve()).as_posix()
            except ValueError:
                return None
        return None