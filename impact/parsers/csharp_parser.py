import re
from pathlib import Path
from typing import Any, Dict, Set, Tuple

from impact.utils import calculate_file_hash
from impact.parsers.base import BaseLanguageParser


class CSharpLanguageParser(BaseLanguageParser):
    """
    Parser poliglota de dependências para C# / .NET (.cs).
    """

    USING_REGEX = re.compile(
        r'using\s+(?:static\s+)?([a-zA-Z0-9_.]+)\s*;'
    )

    @property
    def supported_extensions(self) -> Set[str]:
        return {".cs"}

    def parse_file(
        self, file_path: Path, project_root: Path
    ) -> Tuple[str, Dict[str, Any]]:
        file_hash = calculate_file_hash(file_path)
        rel_path = file_path.resolve().relative_to(project_root.resolve()).as_posix()

        runtime_imports: Set[str] = set()

        try:
            content = file_path.read_text(encoding="utf-8")
            usings = self.USING_REGEX.findall(content)

            for ns in usings:
                # Ignora namespaces do framework .NET padrão
                if ns.startswith(("System", "Microsoft", "Xunit", "NUnit")):
                    continue

                resolved_files = self._resolve_namespace_to_files(
                    ns, project_root
                )
                for resolved in resolved_files:
                    if resolved != rel_path:
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

    def _resolve_namespace_to_files(
        self, namespace_str: str, project_root: Path
    ) -> Set[str]:
        results: Set[str] = set()
        path_part = namespace_str.replace(".", "/")

        target_dir = project_root / path_part
        if target_dir.is_dir():
            for cs_file in target_dir.glob("*.cs"):
                results.add(
                    cs_file.relative_to(project_root.resolve()).as_posix()
                )

        # Procura também arquivos com o nome exato da classe (ex: Services/UserService.cs)
        single_file = project_root / f"{path_part}.cs"
        if single_file.is_file():
            results.add(
                single_file.relative_to(project_root.resolve()).as_posix()
            )

        return results