from pathlib import Path
import typer
from rich import print
from rich.console import Console

from impact.ast_parser import scan_project
from impact.config import init_config
from impact.graph_engine import build_graph, save_graph_cache

# Inicializa o aplicativo Typer com metadados de ajuda
app = typer.Typer(
    name="impact",
    help="ImpactTrace: Ferramenta de Análise de Impacto de Mudanças no Código.",
    add_completion=False,
)

console = Console()


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
def scan(
    project_root: Path = typer.Option(
        Path("."),
        "--root",
        "-r",
        help="Caminho do diretório raiz do projeto a ser escaneado."
    )
) -> None:
    """
    Mapeia todo o projeto, constrói o grafo de dependências e atualiza o cache local (.impact/cache.json).
    """
    try:
        with console.status("[bold green]Escaneando o projeto e mapeando dependências AST...[/bold green]"):
            # 1. Escaneia o código do projeto e extrai dependências por AST
            project_map = scan_project(project_root)

            # 2. Constrói o Grafo Dirigido
            graph = build_graph(project_map)

            # 3. Persiste o Grafo no arquivo de cache .impact/cache.json
            cache_path = save_graph_cache(graph, project_root)

        node_count = graph.number_of_nodes()
        edge_count = graph.number_of_edges()

        print("[bold green]✓[/bold green] Escaneamento concluído com sucesso!")
        print(f"  • [cyan]{node_count}[/cyan] arquivos Python mapeados")
        print(f"  • [cyan]{edge_count}[/cyan] relações de dependência identificadas")
        print(f"  • Cache salvo em: [dim]{cache_path}[/dim]")

    except Exception as e:
        print(f"[bold red]✗ Erro ao escanear o projeto:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def analyze() -> None:
    """
    Analisa os arquivos alterados (via Git Diff) e calcula o impacto das mudanças.
    """
    print("[yellow]ℹ Comando 'analyze' será implementado na Fase 4.[/yellow]")


if __name__ == "__main__":
    app()