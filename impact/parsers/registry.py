from pathlib import Path
from typing import Dict, Optional, Set
from impact.parsers.base import BaseLanguageParser


class ParserRegistry:
    """
    Gerenciador Central de Parsers de Linguagem (Registry Pattern).
    """

    def __init__(self) -> None:
        self._extension_map: Dict[str, BaseLanguageParser] = {}
        self._parsers: Set[BaseLanguageParser] = set()

    def register(self, parser: BaseLanguageParser) -> None:
        self._parsers.add(parser)
        for ext in parser.supported_extensions:
            self._extension_map[ext.lower()] = parser

    def get_parser_for_file(self, file_path: Path) -> Optional[BaseLanguageParser]:
        return self._extension_map.get(file_path.suffix.lower())

    def get_all_supported_extensions(self) -> Set[str]:
        return set(self._extension_map.keys())


# Instância global do Registro
registry = ParserRegistry()