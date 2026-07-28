import json
import webbrowser
from enum import Enum
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
stderr_console = Console(stderr=True)

# Paleta de Cores Semântica (Hexadecimal para Pyvis)
COLOR_CHANGED = "#f59e0b"     # Amarelo (Causa Raiz / Modificado)
COLOR_DIRECT = "#ef4444"      # Vermelho (Impacto Direto / Risco Alto)
COLOR_INDIRECT = "#c084fc"    # Magenta / Violeta (Impacto Indireto / Cascata)
COLOR_SAFE = "#22c55e"        # Verde (Íntegro / Seguro)
COLOR_BG = "#0f172a"          # Dark Slate (Fundo)
COLOR_EDGE = "#475569"        # Cinza Slate (Arestas)
COLOR_EDGE_ACTIVE = "#38bdf8" # Azul Claro (Highlight ao selecionar)


class OutputFormat(str, Enum):
    TEXT = "text"
    AI_JSON = "ai-json"


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
        stderr_console.print(
            "[bold red]✗ A biblioteca 'pyvis' não está instalada.[/bold red] "
            "Instale com: [cyan]pip install pyvis[/cyan]"
        )
        raise RuntimeError("Biblioteca 'pyvis' não encontrada.")

    if output_path is None:
        output_path = Path(".impact/report.html")

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    changed_set = {Path(f).as_posix() for f in impact_result.get("changed", [])}
    direct_set = {Path(f).as_posix() for f in impact_result.get("direct_impact", [])}
    indirect_set = {Path(f).as_posix() for f in impact_result.get("indirect_impact", [])}

    if show_unaffected:
        nodes_to_include = {Path(n).as_posix() for n in graph.nodes()}
    else:
        nodes_to_include = changed_set | direct_set | indirect_set

    nodes_to_include.update(changed_set)

    if not nodes_to_include:
        stderr_console.print("[yellow]ℹ Nenhum nó para exibir no grafo Web.[/yellow]")
        return output_path

    subgraph = nx.DiGraph()
    for node in nodes_to_include:
        subgraph.add_node(node)

    for source, target in graph.edges():
        src_posix = Path(source).as_posix()
        tgt_posix = Path(target).as_posix()
        if src_posix in nodes_to_include and tgt_posix in nodes_to_include:
            subgraph.add_edge(src_posix, tgt_posix)

    net = Network(
        height="850px",
        width="100%",
        bgcolor=COLOR_BG,
        font_color="#f8fafc",
        directed=True,
    )

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

    for source, target in subgraph.edges():
        net.add_edge(
            str(source),
            str(target),
            color={"color": COLOR_EDGE, "highlight": COLOR_EDGE_ACTIVE},
            arrows={"to": {"enabled": True, "scaleFactor": 0.8}},
            title=f"{source} ➜ importa ➜ {target}",
        )

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
    stderr_console.print(f"[bold green]✓ Relatório Web interativo gerado:[/bold green] [cyan]{output_path}[/cyan]")

    if auto_open:
        webbrowser.open(output_path.as_uri())

    return output_path


# ============================================================================
# 3. FORMATO PARA AGENTES DE IA (AI-JSON)
# ============================================================================

def generate_ai_json_report(
    graph: nx.DiGraph,
    impact_result: Dict[str, Any],
    pretty: bool = True,
) -> str:
    """
    Gera uma estrutura JSON otimizada para ser consumida por Agentes de IA
    (Cursor, GitHub Copilot, Claude Dev/Cline).

    Args:
        graph (nx.DiGraph): O grafo de dependências do projeto.
        impact_result (Dict[str, Any]): Resultado do cálculo de impacto.
        pretty (bool): Se True, formata com indentação de 2 espaços.

    Returns:
        str: Payload JSON codificado em string.
    """
    changed = impact_result.get("changed", [])
    direct = impact_result.get("direct_impact", [])
    indirect = impact_result.get("indirect_impact", [])
    unaffected = impact_result.get("unaffected", [])
    total_affected = impact_result.get("total_affected_count", 0)

    # Cálculo Heurístico do Nível de Risco
    if total_affected == 0:
        risk_level = "LOW"
    elif total_affected <= 2:
        risk_level = "MEDIUM"
    elif total_affected <= 6:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"

    # Mapeamento de arestas do subgrafo afetado (Rota de dependência)
    affected_nodes = set(changed) | set(direct) | set(indirect)
    active_edges = []
    for u, v in graph.edges():
        u_posix = Path(u).as_posix()
        v_posix = Path(v).as_posix()
        if u_posix in affected_nodes and v_posix in affected_nodes:
            active_edges.append({
                "importer": u_posix,
                "imported_module": v_posix
            })

    # Instrução pré-construída para o Agente de IA
    prompt_instruction = (
        f"Análise de Impacto (Risco: {risk_level}): Os arquivos em 'changed_files' foram modificados no Git. "
        f"Você DEVE revisar prioritariamente os arquivos em 'direct_impact' para garantir que refatorações ou "
        f"quebras de contrato de API/função não causem quebras. Em seguida, valide a cadeia em 'indirect_impact'. "
        f"Gere testes unitários focados nas áreas afetadas se necessário."
    )

    payload = {
        "version": "1.0.0",
        "tool": "ImpactTrace",
        "assessment": {
            "risk_level": risk_level,
            "total_project_files": impact_result.get("total_project_files", 0),
            "changed_files_count": len(changed),
            "direct_impact_count": len(direct),
            "indirect_impact_count": len(indirect),
            "total_affected_count": total_affected,
        },
        "impact_graph": {
            "changed_files": changed,
            "direct_impact": direct,
            "indirect_impact": indirect,
            "unaffected_files_count": len(unaffected),
            "dependency_routes": active_edges,
        },
        "ai_prompt_instruction": prompt_instruction,
    }

    indent = 2 if pretty else None
    return json.dumps(payload, indent=indent, ensure_ascii=False)