import os
import platform
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Optional


class BrowserLaunchError(Exception):
    """Exceção disparada quando falha a inicialização do navegador."""
    pass


def get_browser_executable(browser_name: str) -> Optional[str]:
    """
    Mapeia nomes amigáveis de navegadores para seus respectivos executáveis
    ou nomes de binários dependendo do Sistema Operacional.
    """
    browser = browser_name.lower().strip()
    system = platform.system()

    if browser == "default":
        return None

    mapping = {
        "chrome": {
            "Darwin": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "Windows": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            "Linux": "google-chrome",
        },
        "firefox": {
            "Darwin": "/Applications/Firefox.app/Contents/MacOS/firefox",
            "Windows": r"C:\Program Files\Mozilla Firefox\firefox.exe",
            "Linux": "firefox",
        },
        "safari": {
            "Darwin": "safari",
            "Windows": None,
            "Linux": None,
        },
        "edge": {
            "Darwin": "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "Windows": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            "Linux": "microsoft-edge",
        },
        "brave": {
            "Darwin": "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "Windows": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            "Linux": "brave-browser",
        },
    }

    if browser not in mapping:
        return None

    return mapping[browser].get(system)


def open_in_browser(file_path: Path, browser_name: str = "default") -> str:
    """
    Abre o arquivo HTML no navegador solicitado com suporte a fallback.

    Returns:
        str: Nome do navegador efetivamente utilizado.
    """
    file_url = file_path.resolve().as_uri()
    browser_key = browser_name.lower().strip()

    if browser_key == "default":
        webbrowser.open(file_url)
        return "Navegador Padrão do Sistema"

    target_exec = get_browser_executable(browser_key)

    if not target_exec:
        # Tenta usar o registro padrão do Python webbrowser para a chave
        try:
            wb = webbrowser.get(browser_key)
            wb.open(file_url)
            return browser_key
        except webbrowser.Error:
            webbrowser.open(file_url)
            return f"Navegador Padrão (Fallback, '{browser_key}' não encontrado)"

    # macOS Safari Handling
    if platform.system() == "Darwin" and browser_key == "safari":
        try:
            subprocess.run(["open", "-a", "Safari", file_url], check=True)
            return "Safari"
        except subprocess.SubprocessError:
            webbrowser.open(file_url)
            return "Navegador Padrão (Fallback)"

    # Caso geral: Executável direto por caminho ou comando no PATH
    try:
        if os.path.exists(target_exec) or any(
            os.access(os.path.join(path, target_exec), os.X_OK)
            for path in os.environ.get("PATH", "").split(os.pathsep)
        ):
            subprocess.Popen([target_exec, file_url])
            return browser_key.capitalize()
        else:
            webbrowser.open(file_url)
            return f"Navegador Padrão (Fallback, '{target_exec}' não instalado)"
    except Exception:
        webbrowser.open(file_url)
        return "Navegador Padrão (Fallback)"