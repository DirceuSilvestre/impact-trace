import subprocess
from pathlib import Path
from typing import List

from impact.parsers.registry import registry


class GitServiceError(Exception):
    """Exceção customizada para erros relacionados à execução do Git."""
    pass


def is_git_repository(root_dir: Path = Path(".")) -> bool:
    """
    Verifica se o diretório informado pertence a um repositório Git válido.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=root_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"
    except FileNotFoundError:
        # O executável 'git' não está instalado ou disponível no PATH do SO
        return False


def get_changed_files(root_dir: Path = Path(".")) -> List[str]:
    """
    Obtém a lista de arquivos alterados no Git cujas extensões
    sejam suportadas pelos parsers registrados no ImpactTrace.

    Args:
        root_dir (Path): Diretório raiz do repositório Git.

    Returns:
        List[str]: Lista ordenada de caminhos relativos no formato POSIX (ex: 'src/app.ts')

    Raises:
        GitServiceError: Se o diretório não for um repositório Git ou se ocorrer erro na execução.
    """
    root_dir = root_dir.resolve()

    if not is_git_repository(root_dir):
        raise GitServiceError(
            f"O diretório '{root_dir}' não é um repositório Git válido ou o Git não está instalado."
        )

    # Obtém a lista dinâmica de extensões suportadas (.py, .ts, .tsx, .js, .go, .rs, etc)
    supported_exts = registry.get_all_supported_extensions()

    try:
        # 'git status --porcelain' entrega uma saída padronizada e estável para scripts
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )

        changed_files: set[str] = set()

        for line in result.stdout.splitlines():
            if not line:
                continue

            # Os 2 primeiros caracteres representam a flag de status no Git (ex: ' M', 'M ', '??')
            path_part = line[3:].strip()

            # Trata caso de arquivo renomeado (ex: 'old.ts -> new.ts')
            if "->" in path_part:
                path_part = path_part.split("->")[-1].strip()

            # Remove aspas caso o Git formate nomes com espaços ou caracteres especiais
            path_part = path_part.strip('"\'')

            file_path = Path(path_part)

            # AQUI ESTÁ A MUDANÇA PRINCIPAL:
            # Em vez de aceitar só '.py', aceita qualquer extensão que algum parser saiba analisar
            if file_path.suffix.lower() in supported_exts:
                changed_files.add(file_path.as_posix())

        return sorted(list(changed_files))

    except subprocess.CalledProcessError as e:
        raise GitServiceError(f"Erro ao executar comando do Git: {e.stderr.strip()}")