from pathlib import Path
import typer
from rich import print
from rich.console import Console
from rich.panel import Panel

from impact.ast_parser import scan_project
from impact.config import init_config
from impact.git_service import GitServiceError, get_changed_files
from impact.graph_engine import (
    build_graph,
    calculate_impact,
    load_graph_cache,
    save_graph_cache,
)
from impact.visualizer import generate_html_report, render_impact_tree

app = typer.Typer(
    name="impact",
    help="ImpactTrace: Ferramenta de Análise de Impacto de Mudanças no Código.",
    add_completion=False,
)

console = Console()


@app.command()
def init() -> None:
    """
    Inicializa o ImpactTrace no projeto atual.
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
        help="Caminho do diretório raiz do projeto.",
    )
) -> None:
    """
    Mapeia todo o projeto e constrói o grafo local.
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
        help="Caminho do diretório raiz do projeto.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Exibe arquivos seguros (em Verde) no terminal e no grafo.",
    ),
    web: bool = typer.Option(
        False,
        "--web",
        "-w",
        help="Gera e abre o relatório interativo HTML no navegador.",
    ),
) -> None:
    """
    Analisa os arquivos alterados e calcula o impacto direto/indireto.
    """
    try:
        project_root = project_root.resolve()
        graph = load_graph_cache(project_root)

        if graph is None:
            print("[yellow]ℹ Cache não encontrado. Executando scan inicial...[/yellow]")
            project_map = scan_project(project_root)
            graph = build_graph(project_map)
            save_graph_cache(graph, project_root)

        changed_files = get_changed_files(project_root)

        if not changed_files:
            print("[bold yellow]ℹ Nenhum arquivo Python com alterações detectado no Git.[/bold yellow]")
            return

        impact_result = calculate_impact(graph, changed_files)

        # 1. Renderiza no Terminal (Árvore Rich)
        render_impact_tree(
            graph=graph,
            changed_files=changed_files,
            unaffected_files=impact_result["unaffected"],
            show_unaffected=verbose,
        )

        # 2. Renderiza no Navegador se a flag --web / -w for informada
        if web:
            generate_html_report(
                graph=graph,
                impact_result=impact_result,
                show_unaffected=verbose,
                auto_open=True,
            )

        # 3. Painel do Resumo
        total_affected = impact_result["total_affected_count"]
        status_color = "green" if total_affected == 0 else "cyan"

        summary_msg = (
            f"[bold]Total de arquivos no projeto:[/bold] {impact_result['total_project_files']}\n"
            f"[bold]Modificados no Git:[/bold] [yellow]{len(impact_result['changed'])}[/yellow]\n"
            f"[bold]Impacto Direto (Crítico):[/bold] [red]{len(impact_result['direct_impact'])}[/red]\n"
            f"[bold]Impacto Indireto (Cascata):[/bold] [magenta]{len(impact_result['indirect_impact'])}[/magenta]\n"
            f"[bold]Arquivos Seguros (Intactos):[/bold] [green]{len(impact_result['unaffected'])}[/green]"
        )

        console.print(
            Panel(
                summary_msg,
                title="📊 Resumo Geral do Projeto",
                border_style=status_color,
            )
        )

    except GitServiceError as e:
        print(f"[bold red]✗ Erro no serviço de Git:[/bold red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        print(f"[bold red]✗ Erro ao executar a análise:[/bold red] {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()