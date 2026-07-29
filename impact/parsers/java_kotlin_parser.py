import re
from pathlib import Path
from typing import Any, Dict, Set, Tuple

from impact.utils import calculate_file_hash
from impact.parsers.base import BaseLanguageParser


class JavaKotlinLanguageParser(BaseLanguageParser):
    """
    Parser poliglota de dependências para Java (.java) e Kotlin (.kt).
    """

    IMPORT_REGEX = re.compile(r'import\s+([a-zA-Z0-9_.]+);?')

    @property
    def supported_extensions(self) -> Set[str]:
        return {".java", ".kt"}

    def parse_file(
        self, file_path: Path, project_root: Path
    ) -> Tuple[str, Dict[str, Any]]:
        file_hash = calculate_file_hash(file_path)
        rel_path = file_path.resolve().relative_to(project_root.resolve()).as_posix()

        runtime_imports: Set[str] = set()

        try:
            content = file_path.read_text(encoding="utf-8")
            imports = self.IMPORT_REGEX.findall(content)

            for imp in imports:
                resolved = self._resolve_package_import(imp, project_root)
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

    def _resolve_package_import(
        self, import_str: str, project_root: Path
    ) -> str | None:
        # Transforma com.empresa.app.Service -> com/empresa/app/Service
        path_part = import_str.replace(".", "/")

        # Procura os arquivos correspondentes nas estruturas padrão do Gradle/Maven
        candidate_paths = [
            f"src/main/java/{path_part}.java",
            f"src/main/kotlin/{path_part}.kt",
            f"src/main/java/{path_part}.kt",
            f"src/{path_part}.java",
            f"src/{path_part}.kt",
            f"{path_part}.java",
            f"{path_part}.kt",
        ]

        for rel_candidate in candidate_paths:
            full_path = project_root / rel_candidate
            if full_path.is_file():
                return full_path.relative_to(project_root.resolve()).as_posix()

        return None