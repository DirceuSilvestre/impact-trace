import sys
from pathlib import Path
import typer
from rich import print
from rich.console import Console
from rich.panel import Panel

from impact.ast_parser import scan_project_incremental
from impact.browser import open_in_browser
from impact.config import init_config
from impact.git_service import GitServiceError, get_changed_files
from impact.graph_engine import (
    build_graph,
    calculate_impact,
    load_graph_cache,
    save_graph_cache,
)
from impact.visualizer import (
    OutputFormat,
    generate_ai_json_report,
    generate_full_architectural_graph,
    generate_html_report,
    render_impact_tree,
)

app = typer.Typer(
    name="impact",
    help="ImpactTrace: Ferramenta de Análise de Impacto e Grafo Arquitetural de Código.",
    add_completion=False,
)

console = Console()
stderr_console = Console(stderr=True)


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
    Mapeia todo o projeto e constrói o grafo local de forma incremental ($O(1)$).
    """
    try:
        project_root = project_root.resolve()
        _, existing_cache = load_graph_cache(project_root)

        with console.status(
            "[bold green]Escaneamento incremental AST via SHA-256...[/bold green]"
        ):
            project_map, stats = scan_project_incremental(project_root, existing_cache)
            graph = build_graph(project_map)
            cache_path = save_graph_cache(project_map, graph, project_root)

        node_count = graph.number_of_nodes()
        edge_count = graph.number_of_edges()

        print("[bold green]✓[/bold green] Escaneamento incremental concluído!")
        print(f"  • [cyan]{node_count}[/cyan] arquivos Python no projeto")
        print(f"  • [cyan]{edge_count}[/cyan] relações de dependência mapeadas")
        print(
            f"  • [green]⚡ Performance:[/green] {stats['cache_hits']}/{stats['total_files']} "
            f"arquivos no cache ({stats['reparsed']} re-parseados)"
        )
        print(f"  • Cache salvo em: [dim]{cache_path}[/dim]")

    except Exception as e:
        print(f"[bold red]✗ Erro ao escanear o projeto:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def graph(
    project_root: Path = typer.Option(
        Path("."),
        "--root",
        "-r",
        help="Caminho do diretório raiz do projeto.",
    ),
    output: Path = typer.Option(
        Path(".impact/graph.html"),
        "--output",
        "-o",
        help="Caminho do arquivo HTML de saída para o grafo.",
    ),
    layout: str = typer.Option(
        "hierarchical",
        "--layout",
        "-l",
        help="Layout inicial: 'hierarchical' (Top-Down Raiz-Folha) ou 'force' (Dynamic Physics).",
    ),
    browser: str = typer.Option(
        "default",
        "--browser",
        "-b",
        help="Navegador para abrir o relatório ('default', 'chrome', 'firefox', 'safari', 'edge', 'brave').",
    ),
    open_browser: bool = typer.Option(
        True,
        "--open/--no-open",
        help="Abre automaticamente o navegador após gerar o arquivo.",
    ),
) -> None:
    """
    Gera a visualização interativa do Grafo Arquitetural Completo com layout Hierárquico.
    """
    try:
        project_root = project_root.resolve()
        graph_obj, existing_cache = load_graph_cache(project_root)

        # Se o cache não existir, executa um scan automático
        if not graph_obj or not existing_cache:
            with console.status("[bold green]Gerando mapeamento do projeto...[/bold green]"):
                project_map, _ = scan_project_incremental(project_root, existing_cache)
                graph_obj = build_graph(project_map)
                save_graph_cache(project_map, graph_obj, project_root)

        # Gera o HTML do Grafo Completo
        html_file = generate_full_architectural_graph(
            graph=graph_obj,
            output_path=output,
            initial_layout=layout,
        )

        print("[bold green]✓[/bold green] Grafo Arquitetural Completo gerado com sucesso!")
        print(f"  • Arquivo: [cyan]{html_file}[/cyan]")
        print(f"  • Layout: [magenta]{layout.capitalize()}[/magenta]")

        # Abertura do Navegador
        if open_browser:
            used_browser = open_in_browser(html_file, browser_name=browser)
            print(f"  • Abriu no navegador: [yellow]{used_browser}[/yellow]")

    except Exception as e:
        stderr_console.print(f"[bold red]✗ Erro ao gerar o grafo arquitetural:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def analyze(
    project_root: Path = typer.Option(
        Path("."),
        "--root",
        "-r",
        help="Caminho do diretório raiz do projeto.",
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.TEXT,
        "--format",
        "-f",
        help="Formato de saída: 'text' (padrão) ou 'ai-json' (para LLMs/Agentes).",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Exibe arquivos seguros no terminal.",
    ),
    web: bool = typer.Option(
        False,
        "--web",
        "-w",
        help="Gera e abre o relatório interativo HTML no navegador.",
    ),
    browser: str = typer.Option(
        "default",
        "--browser",
        "-b",
        help="Navegador para abrir o relatório ('default', 'chrome', 'firefox', 'safari', 'edge').",
    ),
) -> None:
    """
    Analisa os arquivos alterados e calcula o impacto direto/indireto.
    """
    try:
        project_root = project_root.resolve()
        changed_files = get_changed_files(project_root)

        if not changed_files:
            if format == OutputFormat.AI_JSON:
                empty_payload = generate_ai_json_report(
                    build_graph({}),
                    {
                        "changed": [],
                        "direct_impact": [],
                        "indirect_impact": [],
                        "unaffected": [],
                        "total_affected_count": 0,
                        "total_project_files": 0,
                    },
                )
                sys.stdout.write(empty_payload + "\n")
            else:
                print("[bold yellow]ℹ Nenhum arquivo Python com alterações detectado no Git.[/bold yellow]")
            return

        graph_obj, existing_cache = load_graph_cache(project_root)

        missing_or_changed = False
        if not graph_obj or not existing_cache:
            missing_or_changed = True
        else:
            cached_files = existing_cache.get("files", {})
            for changed in changed_files:
                if changed not in cached_files:
                    missing_or_changed = True
                    break

        if missing_or_changed:
            project_map, _ = scan_project_incremental(project_root, existing_cache)
            graph_obj = build_graph(project_map)
            save_graph_cache(project_map, graph_obj, project_root)

        impact_result = calculate_impact(graph_obj, changed_files)

        if format == OutputFormat.AI_JSON:
            json_output = generate_ai_json_report(graph_obj, impact_result, pretty=True)
            sys.stdout.write(json_output + "\n")

        else:
            render_impact_tree(
                graph=graph_obj,
                changed_files=changed_files,
                unaffected_files=impact_result["unaffected"],
                show_unaffected=verbose,
            )

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

        if web:
            html_path = generate_html_report(
                graph=graph_obj,
                impact_result=impact_result,
                show_unaffected=verbose,
                auto_open=False,
            )
            used_browser = open_in_browser(html_path, browser_name=browser)
            print(f"  • Relatório aberto no navegador: [yellow]{used_browser}[/yellow]")

    except GitServiceError as e:
        stderr_console.print(f"[bold red]✗ Erro no serviço de Git:[/bold red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        stderr_console.print(f"[bold red]✗ Erro ao executar a análise:[/bold red] {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()