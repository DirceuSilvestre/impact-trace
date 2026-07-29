from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


class BaseLanguageParser(ABC):
    """
    Contrato Abstrato para Parsers de Linguagens no ImpactTrace.
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> Set[str]:
        """Retorna o conjunto de extensões suportadas (ex: {'.ts', '.tsx', '.js', '.jsx'})."""
        pass

    @abstractmethod
    def parse_file(
        self, file_path: Path, project_root: Path
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Parseia um arquivo específico e retorna:
        (caminho_relativo_posix, data_dict_com_imports_e_hash)
        """
        pass