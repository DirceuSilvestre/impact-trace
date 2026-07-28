from pathlib import Path
import typer
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from impact.visualizer import render_impact_tree
from impact.ast_parser import scan_project
from impact.config import init_config
from impact.git_service import GitServiceError, get_changed_files
from impact.graph_engine import (
    build_graph,
    calculate_impact,
    load_graph_cache,
    save_graph_cache,
)

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
        help="Caminho do diretório raiz do projeto a ser escaneado.",
    )
) -> None:
    """
    Mapeia todo o projeto, constrói o grafo de dependências e atualiza o cache local.
    """
    try:
        with console.status(
            "[bold green]Escaneando o projeto e mapeando dependências AST...[/bold green]"
        ):
            project_map = scan_project(project_root)
            graph = build_graph(project_map)
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
def analyze(
    project_root: Path = typer.Option(
        Path("."),
        "--root",
        "-r",
        help="Caminho do diretório raiz do projeto a ser analisado.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Exibe a lista detalhada de arquivos seguros/não afetados em verde.",
    ),
) -> None:
    """
    Analisa os arquivos alterados no Git e calcula o impacto direto e indireto no projeto.
    """
    try:
        project_root = project_root.resolve()

        # 1. Carrega o grafo do cache
        graph = load_graph_cache(project_root)

        if graph is None:
            print(
                "[yellow]ℹ Cache de dependências não encontrado. Executando scan inicial...[/yellow]"
            )
            project_map = scan_project(project_root)
            graph = build_graph(project_map)
            save_graph_cache(graph, project_root)

        # 2. Identifica arquivos alterados
        changed_files = get_changed_files(project_root)

        if not changed_files:
            print(
                "[bold yellow]ℹ Nenhum arquivo Python com alterações detectado no Git.[/bold yellow]"
            )
            print("[dim]Altere algum arquivo .py para analisar o impacto.[/dim]")
            return

        # 3. Calcula o impacto
        impact_result = calculate_impact(graph, changed_files)

        # 4. Renderiza o relatório visual
        _render_impact_report(impact_result, show_unaffected=verbose)

    except GitServiceError as e:
        print(f"[bold red]✗ Erro no serviço de Git:[/bold red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        print(f"[bold red]✗ Erro ao executar a análise de impacto:[/bold red] {e}")
        raise typer.Exit(code=1)


def _render_impact_report(impact: dict, show_unaffected: bool = False) -> None:
    """
    Renderiza o relatório visual usando a árvore hierárquica do Rich.
    """
    changed = impact["changed"]
    unaffected = impact["unaffected"]
    total_affected = impact["total_affected_count"]
    total_files = impact["total_project_files"]

    # 1. Carrega e exibe o grafo do cache para passar ao visualizer
    project_root = Path(".")
    graph = load_graph_cache(project_root)

    if graph:
        render_impact_tree(
            graph=graph,
            changed_files=changed,
            unaffected_files=unaffected,
            show_unaffected=show_unaffected,
        )

    # 2. Painel Resumo no final
    status_color = "green" if total_affected == 0 else "cyan"
    summary_msg = (
        f"[bold]Total de arquivos no projeto:[/bold] {total_files}\n"
        f"[bold]Modificados no Git:[/bold] [yellow]{len(changed)}[/yellow]\n"
        f"[bold]Impacto Direto/Indireto Total:[/bold] [red]{total_affected}[/red]\n"
        f"[bold]Arquivos Seguros (Intactos):[/bold] [green]{len(unaffected)}[/green]"
    )

    console.print(
        Panel(
            summary_msg,
            title="📊 Resumo Geral do Projeto",
            border_style=status_color,
        )
    )

if __name__ == "__main__":
    app()