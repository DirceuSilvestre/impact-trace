import hashlib
from pathlib import Path


def calculate_file_hash(file_path: Path) -> str:
    """
    Calcula o hash SHA-256 do conteúdo do arquivo em blocos de 64KB.
    """
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
    except OSError:
        return ""