import re
from pathlib import Path
from typing import Any, Dict, Set, Tuple
from impact.parsers.base import BaseLanguageParser
from impact.utils import calculate_file_hash


class TSJSModuleParser(BaseLanguageParser):
    """
    Parser de Dependências para JavaScript, TypeScript, JSX e TSX.
    Suporta: import, export from, e require().
    """

    # Captura: import ... from './path', require('./path'), export ... from './path'
    IMPORT_REGEX = re.compile(
        r'(?:import|export)\s+[\s\S]*?\s+from\s+[\'"]([^\'"]+)[\'"]|'
        r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
    )

    @property
    def supported_extensions(self) -> Set[str]:
        return {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}

    def parse_file(
        self, file_path: Path, project_root: Path
    ) -> Tuple[str, Dict[str, Any]]:
        file_hash = calculate_file_hash(file_path)
        rel_path = file_path.resolve().relative_to(project_root.resolve()).as_posix()

        runtime_imports: Set[str] = set()

        try:
            content = file_path.read_text(encoding="utf-8")
            matches = self.IMPORT_REGEX.findall(content)

            for match in matches:
                # O regex possui dois grupos de captura (import ou require)
                raw_import = match[0] or match[1]

                # Filtra apenas imports locais/relativos (ignora pacotes do node_modules como 'react', 'lodash')
                if raw_import.startswith(".") or raw_import.startswith("@/"):
                    resolved = self._resolve_ts_import(
                        raw_import, file_path, project_root
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

    def _resolve_ts_import(
        self, import_str: str, current_file: Path, project_root: Path
    ) -> str | None:
        """
        Resolve imports do TS/JS testando extensões implícitas (.ts, .tsx, .js, /index.ts, etc)
        """
        if import_str.startswith("@/"):
            # Trata Aliases do tsconfig/vite padrão (@/ -> src/)
            base_target = project_root / "src" / import_str[2:]
        else:
            base_target = current_file.parent / import_str

        # Tenta o arquivo direto com as extensões possíveis
        possible_extensions = [
            "",
            ".ts",
            ".tsx",
            ".js",
            ".jsx",
            "/index.ts",
            "/index.tsx",
            "/index.js",
        ]

        for ext in possible_extensions:
            candidate = Path(str(base_target) + ext).resolve()
            if candidate.is_file() and candidate.exists():
                try:
                    return candidate.relative_to(project_root.resolve()).as_posix()
                except ValueError:
                    return None

        return None