import ast
from pathlib import Path
from typing import List, Set


def parse_file_imports(file_path: Path) -> List[str]:
    """
    Lê um arquivo .py, analisa sua AST (Abstract Syntax Tree) e extrai
    todas as dependências importadas (via 'import' ou 'from ... import').

    Args:
        file_path (Path): Caminho do arquivo .py a ser analisado.

    Returns:
        List[str]: Lista ordenada com os nomes dos módulos/arquivos importados.
    """
    if not file_path.exists() or file_path.suffix != ".py":
        return []

    imported_modules: Set[str] = set()

    try:
        # 1. Lê o conteúdo do arquivo Python
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 2. Transforma o texto do código na Árvore de Sintaxe Abstrata (AST)
        tree = ast.parse(content, filename=str(file_path))

        # 3. Percorre todos os nós da árvore procurando comandos de importação
        for node in ast.walk(tree):
            
            # Caso 1: Comandos do tipo 'import foo' ou 'import foo.bar'
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name)

            # Caso 2: Comandos do tipo 'from foo import bar' ou 'from . import config'
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.add(node.module)
                elif node.level > 0:
                    # Registra imports relativos (ex: 'from . import utils')
                    imported_modules.add("." * node.level)

    except SyntaxError:
        # Se o arquivo do usuário tiver um erro de sintaxe, ignoramos graciosamente
        # para não travar o scanner do sistema inteiro.
        pass
    except Exception:
        # Trata possíveis erros de leitura de arquivo ou problemas de encoding
        pass

    return sorted(list(imported_modules))