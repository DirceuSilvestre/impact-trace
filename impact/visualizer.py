import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import networkx as nx
from rich.console import Console
from rich.tree import Tree

try:
    from pyvis.network import Network
    PYVIS_AVAILABLE = True
except ImportError:
    PYVIS_AVAILABLE = False

console = Console()

# Paleta de Cores Semântica (Hexadecimal para Pyvis)
COLOR_CHANGED = "#f59e0b"     # Amarelo (Causa Raiz / Modificado)
COLOR_DIRECT = "#ef4444"      # Vermelho (Impacto Direto / Risco Alto)
COLOR_INDIRECT = "#c084fc"    # Magenta / Violeta (Impacto Indireto / Cascata)
COLOR_SAFE = "#22c55e"        # Verde (Íntegro / Seguro)
COLOR_BG = "#0f172a"          # Dark Slate (Fundo)
COLOR_EDGE = "#475569"        # Cinza Slate (Arestas)
COLOR_EDGE_ACTIVE = "#38bdf8" # Azul Claro (Highlight ao selecionar)


# ============================================================================
# 1. VISUALIZAÇÃO NO TERMINAL (RICH TREE)
# ============================================================================

def build_impact_tree(
    graph: nx.DiGraph,
    changed_files: List[str],
    unaffected_files: Optional[List[str]] = None,
    show_unaffected: bool = False,
) -> Tree:
    """
    Constrói uma árvore hierárquica usando Rich para exibição no terminal.
    """
    root_tree = Tree(
        "[bold cyan]🌳 Árvore de Propagação de Impacto (ImpactTrace)[/bold cyan]",
        guide_style="dim cyan",
    )

    if not changed_files:
        root_tree.add("[bold yellow]ℹ Nenhum arquivo alterado detectado.[/bold yellow]")
        return root_tree

    changed_branch = root_tree.add(
        "[bold yellow]📝 Arquivos Modificados no Git (Origem)[/bold yellow]"
    )

    for changed in changed_files:
        changed_node = changed_branch.add(f"[bold yellow]{changed}[/bold yellow]")

        if not graph.has_node(changed):
            changed_node.add(
                "[dim italic](Arquivo novo ou sem conexões no grafo)[/dim italic]"
            )
            continue

        _add_dependents_recursively(
            graph,
            parent_tree_node=changed_node,
            current_node=changed,
            visited={changed},
            depth=1,
        )

    if show_unaffected and unaffected_files:
        unaffected_branch = root_tree.add(
            f"[bold green]🛡️ Arquivos Íntegros e Seguros ({len(unaffected_files)})[/bold green]"
        )
        for safe_file in unaffected_files:
            unaffected_branch.add(f"[bold green]{safe_file}[/bold green]")

    return root_tree


def _add_dependents_recursively(
    graph: nx.DiGraph,
    parent_tree_node: Tree,
    current_node: str,
    visited: Set[str],
    depth: int,
) -> None:
    """
    Auxiliar recursivo que percorre os predecessores (módulos consumidores).
    """
    dependents = sorted(list(graph.predecessors(current_node)))

    if not dependents:
        if depth == 1:
            parent_tree_node.add(
                "[dim green]✓ Nenhuma dependência afetada (Mudança isolada)[/dim green]"
            )
        return

    for dep in dependents:
        if dep in visited:
            parent_tree_node.add(f"[dim red]🔄 {dep} (Ciclo de importação detectado)[/dim red]")
            continue

        new_visited = visited.copy()
        new_visited.add(dep)

        if depth == 1:
            label = f"[bold red]💥 {dep}[/bold red] [dim italic](Impacto Direto)[/dim italic]"
            child_node = parent_tree_node.add(label)
        else:
            label = f"[bold magenta]⚠️ {dep}[/bold magenta] [dim italic](Impacto Indireto - Nível {depth})[/dim italic]"
            child_node = parent_tree_node.add(label)

        _add_dependents_recursively(
            graph,
            parent_tree_node=child_node,
            current_node=dep,
            visited=new_visited,
            depth=depth + 1,
        )


def render_impact_tree(
    graph: nx.DiGraph,
    changed_files: List[str],
    unaffected_files: Optional[List[str]] = None,
    show_unaffected: bool = False,
) -> None:
    """
    Helper para renderizar a árvore no terminal.
    """
    tree = build_impact_tree(graph, changed_files, unaffected_files, show_unaffected)
    console.print()
    console.print(tree)
    console.print()


# ============================================================================
# 2. VISUALIZAÇÃO INTERATIVA WEB (PYVIS)
# ============================================================================

def generate_html_report(
    graph: nx.DiGraph,
    impact_result: Dict[str, Any],
    output_path: Optional[Path] = None,
    show_unaffected: bool = False,
    auto_open: bool = True,
) -> Path:
    """
    Gera um relatório interativo HTML do grafo de impacto usando Pyvis.
    """
    if not PYVIS_AVAILABLE:
        console.print(
            "[bold red]✗ A biblioteca 'pyvis' não está instalada.[/bold red] "
            "Instale com: [cyan]pip install pyvis[/cyan]"
        )
        raise RuntimeError("Biblioteca 'pyvis' não encontrada.")

    if output_path is None:
        output_path = Path(".impact/report.html")

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Normalização de caminhos (POSIX) para evitar inconsistência de barras no Windows/Git
    changed_set = {Path(f).as_posix() for f in impact_result.get("changed", [])}
    direct_set = {Path(f).as_posix() for f in impact_result.get("direct_impact", [])}
    indirect_set = {Path(f).as_posix() for f in impact_result.get("indirect_impact", [])}
    unaffected_set = {Path(f).as_posix() for f in impact_result.get("unaffected", [])}

    if show_unaffected:
        nodes_to_include = {Path(n).as_posix() for n in graph.nodes()}
    else:
        nodes_to_include = changed_set | direct_set | indirect_set

    # Garantia de resiliência: Assegura que todos os arquivos alterados estejam no conjunto
    nodes_to_include.update(changed_set)

    if not nodes_to_include:
        console.print("[yellow]ℹ Nenhum nó para exibir no grafo Web.[/yellow]")
        return output_path

    # Constrói o subgrafo garantindo a inclusão física dos nós
    subgraph = nx.DiGraph()
    for node in nodes_to_include:
        subgraph.add_node(node)

    for source, target in graph.edges():
        src_posix = Path(source).as_posix()
        tgt_posix = Path(target).as_posix()
        if src_posix in nodes_to_include and tgt_posix in nodes_to_include:
            subgraph.add_edge(src_posix, tgt_posix)

    # Inicializa a rede Pyvis
    net = Network(
        height="850px",
        width="100%",
        bgcolor=COLOR_BG,
        font_color="#f8fafc",
        directed=True,
    )

    # Adiciona os nós estilizados
    for node in subgraph.nodes():
        node_str = str(node)
        in_degree = graph.in_degree(node_str) if graph.has_node(node_str) else 0
        out_degree = graph.out_degree(node_str) if graph.has_node(node_str) else 0

        if node_str in changed_set:
            color = COLOR_CHANGED
            size = 28
            shape = "dot"
            status = "📝 Causa Raiz (Modificado no Git)"
        elif node_str in direct_set:
            color = COLOR_DIRECT
            size = 22
            shape = "dot"
            status = "💥 Impacto Direto (Risco Alto)"
        elif node_str in indirect_set:
            color = COLOR_INDIRECT
            size = 18
            shape = "dot"
            status = "⚠️ Impacto Indireto (Cascata)"
        else:
            color = COLOR_SAFE
            size = 12
            shape = "dot"
            status = "🛡️ Íntegro / Seguro"

        tooltip_html = (
            f"<b>Arquivo:</b> {node_str}<br/>"
            f"<b>Status:</b> {status}<br/>"
            f"<b>Consumidores (In-Degree):</b> {in_degree}<br/>"
            f"<b>Dependências (Out-Degree):</b> {out_degree}"
        )

        net.add_node(
            node_str,
            label=Path(node_str).name,
            title=tooltip_html,
            color=color,
            size=size,
            shape=shape,
            borderWidth=2,
            font={"size": 14, "face": "monospace", "color": "#f8fafc"},
        )

    # Adiciona as arestas (Relações de Dependência)
    for source, target in subgraph.edges():
        net.add_edge(
            str(source),
            str(target),
            color={"color": COLOR_EDGE, "highlight": COLOR_EDGE_ACTIVE},
            arrows={"to": {"enabled": True, "scaleFactor": 0.8}},
            title=f"{source} ➜ importa ➜ {target}",
        )

    # Configuração detalhada da física e do layout
    net.set_options(f"""
    {{
      "nodes": {{
        "borderWidthSelected": 4
      }},
      "edges": {{
        "smooth": {{
          "type": "cubicBezier",
          "forceDirection": "horizontal",
          "roundness": 0.4
        }}
      }},
      "physics": {{
        "solver": "forceAtlas2Based",
        "forceAtlas2Based": {{
          "gravitationalConstant": -60,
          "centralGravity": 0.01,
          "springLength": 120,
          "springConstant": 0.08,
          "damping": 0.4
        }},
        "maxVelocity": 50,
        "minVelocity": 0.75,
        "timestep": 0.5
      }},
      "interaction": {{
        "hover": true,
        "tooltipDelay": 100,
        "navigationButtons": true,
        "keyboard": true,
        "zoomView": true
      }}
    }}
    """)

    net.save_graph(str(output_path))
    console.print(f"[bold green]✓ Relatório Web interativo gerado:[/bold green] [cyan]{output_path}[/cyan]")

    if auto_open:
        webbrowser.open(output_path.as_uri())

    return output_path