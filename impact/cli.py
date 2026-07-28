import typer
from rich import print
from impact.config import init_config

# Inicializa o aplicativo Typer com metadados de ajuda
app = typer.Typer(
    name="impact",
    help="ImpactTrace: Ferramenta de Análise de Impacto de Mudanças no Código.",
    add_completion=False,
)


@app.command()
def init() -> None:
    """
    Inicializa o ImpactTrace no projeto atual, criando a pasta .impact/ e o config.json.
    """
    try:
        config_path = init_config()
        print("[bold green]✓[/bold green] ImpactTrace inicializado com sucesso!")
        print(f"[dim]Arquivo de configuração:[/dim] [cyan]{config_path}[/cyan]")
    except Exception as e:
        print(f"[bold red]✗ Erro ao inicializar o ImpactTrace:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def scan() -> None:
    """
    Mapeia todo o projeto e atualiza o grafo de dependências no cache local.
    """
    print("[yellow]ℹ Comando 'scan' será implementado na Fase 3.[/yellow]")


@app.command()
def analyze() -> None:
    """
    Analisa os arquivos alterados (via Git Diff) e calcula o impacto das mudanças.
    """
    print("[yellow]ℹ Comando 'analyze' será implementado na Fase 4.[/yellow]")


if __name__ == "__main__":
    app()