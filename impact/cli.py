import json
import sys
from pathlib import Path
from typing import Optional
import typer
from rich import print
from rich.console import Console
from rich.panel import Panel

from impact.ast_parser import scan_project_incremental
from impact.browser import open_in_browser
from impact.config import find_project_root, init_config, load_config
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


def resolve_root(project_root: Optional[Path]) -> Path:
    """
    Resolve o caminho raiz do projeto.
    Se o usuário passou --root explicitamente, usa o caminho fornecido diretamente.
    Se omitido (None), executa a auto-descoberta subindo a árvore de diretórios.
    """
    if project_root is not None:
        return project_root.resolve()
    return find_project_root(Path(".")).resolve()


@app.command()
def init(
    project_root: Optional[Path] = typer.Option(
        None,
        "--root",
        "-r",
        help="Caminho do diretório raiz do projeto (autodetectado se omitido).",
    )
) -> None:
    """
    Inicializa o ImpactTrace no projeto atual.
    """
    try:
        root = resolve_root(project_root)
        config_path = init_config(root)
        print("[bold green]✓[/bold green] ImpactTrace inicializado com sucesso!")
        print(f"  • [bold dim]Raiz do Projeto:[/bold dim] [cyan]{root}[/cyan]")
        print(f"  • [bold dim]Configuração:[/bold dim] [cyan]{config_path}[/cyan]")
    except Exception as e:
        print(f"[bold red]✗ Erro ao inicializar o ImpactTrace:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def scan(
    project_root: Optional[Path] = typer.Option(
        None,
        "--root",
        "-r",
        help="Caminho do diretório raiz do projeto (autodetectado se omitido).",
    )
) -> None:
    """
    Mapeia todo o projeto a partir da Raiz e constrói o grafo incremental.
    """
    try:
        root = resolve_root(project_root)
        config = load_config(root)
        ignore_dirs = set(config.get("ignore_dirs", []))

        _, existing_cache = load_graph_cache(root)

        with console.status(
            "[bold green]Escaneamento incremental AST a partir da Raiz...[/bold green]"
        ):
            project_map, stats = scan_project_incremental(
                root, existing_cache, ignore_dirs=ignore_dirs
            )
            graph = build_graph(project_map)
            cache_path = save_graph_cache(project_map, graph, root)

        node_count = graph.number_of_nodes()
        edge_count = graph.number_of_edges()

        dir_summary = {}
        for file_path in project_map.keys():
            top_dir = file_path.split("/")[0] if "/" in file_path else "."
            dir_summary[top_dir] = dir_summary.get(top_dir, 0) + 1

        breakdown = ", ".join(
            [f"[yellow]{d}/[/yellow]: {c}" for d, c in sorted(dir_summary.items())]
        )

        print("[bold green]✓[/bold green] Escaneamento incremental concluído!")
        print(f"  • [bold dim]Raiz Mapeada:[/bold dim] [cyan]{root}[/cyan]")
        print(f"  • [cyan]{node_count}[/cyan] arquivos Python mapeados ({breakdown})")
        print(f"  • [cyan]{edge_count}[/cyan] relações de dependência mapeadas")
        print(
            f"  • [green]⚡ Cache:[/green] {stats['cache_hits']}/{stats['total_files']} "
            f"arquivos inalterados ({stats['reparsed']} re-parseados)"
        )
        print(f"  • Cache salvo em: [dim]{cache_path}[/dim]")

    except Exception as e:
        print(f"[bold red]✗ Erro ao escanear o projeto:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def graph(
    project_root: Optional[Path] = typer.Option(
        None,
        "--root",
        "-r",
        help="Caminho do diretório raiz do projeto (autodetectado se omitido).",
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
    Gera a visualização interativa do Grafo Arquitetural Completo de todo o projeto.
    """
    try:
        root = resolve_root(project_root)
        config = load_config(root)
        ignore_dirs = set(config.get("ignore_dirs", []))

        output_file = output if output.is_absolute() else root / output

        graph_obj, existing_cache = load_graph_cache(root)

        if not graph_obj or not existing_cache:
            with console.status("[bold green]Gerando mapeamento completo do projeto...[/bold green]"):
                project_map, _ = scan_project_incremental(
                    root, existing_cache, ignore_dirs=ignore_dirs
                )
                graph_obj = build_graph(project_map)
                save_graph_cache(project_map, graph_obj, root)

        html_file = generate_full_architectural_graph(
            graph=graph_obj,
            output_path=output_file,
            initial_layout=layout,
        )

        print("[bold green]✓[/bold green] Grafo Arquitetural Completo gerado com sucesso!")
        print(f"  • Raiz: [cyan]{root}[/cyan]")
        print(f"  • Arquivo: [cyan]{html_file}[/cyan]")
        print(f"  • Layout: [magenta]{layout.capitalize()}[/magenta]")

        if open_browser:
            used_browser = open_in_browser(html_file, browser_name=browser)
            print(f"  • Abriu no navegador: [yellow]{used_browser}[/yellow]")

    except Exception as e:
        stderr_console.print(f"[bold red]✗ Erro ao gerar o grafo arquitetural:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def analyze(
    project_root: Optional[Path] = typer.Option(
        None,
        "--root",
        "-r",
        help="Caminho do diretório raiz do projeto (autodetectado se omitido).",
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
    Analisa os arquivos alterados no Git e calcula a propagação do impacto.
    """
    try:
        root = resolve_root(project_root)
        config = load_config(root)
        ignore_dirs = set(config.get("ignore_dirs", []))

        changed_files = get_changed_files(root)

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

        graph_obj, existing_cache = load_graph_cache(root)

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
            project_map, _ = scan_project_incremental(root, existing_cache, ignore_dirs=ignore_dirs)
            graph_obj = build_graph(project_map)
            save_graph_cache(project_map, graph_obj, root)

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
                f"[bold]Raiz do Projeto:[/bold] {root}\n"
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