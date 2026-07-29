import json
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import networkx as nx
from rich import print
from rich.console import Console
from rich.tree import Tree

console = Console()


class OutputFormat(str, Enum):
    TEXT = "text"
    AI_JSON = "ai-json"


def render_impact_tree(
    graph: nx.DiGraph,
    changed_files: List[str],
    unaffected_files: List[str],
    show_unaffected: bool = False,
) -> None:
    """
    Renderiza a árvore de impacto no terminal usando Rich.
    """
    tree = Tree("🔍 [bold cyan]Análise de Impacto de Código[/bold cyan]")

    changed_branch = tree.add("✏️ [bold yellow]Arquivos Alterados (Git)[/bold yellow]")
    for file in changed_files:
        changed_branch.add(f"[yellow]{file}[/yellow]")

    direct_branch = tree.add("💥 [bold red]Impacto Direto (Consumidores Imediatos)[/bold red]")
    direct_nodes = set()
    for changed in changed_files:
        if graph.has_node(changed):
            direct_nodes.update(set(graph.predecessors(changed)) - set(changed_files))

    for direct in sorted(list(direct_nodes)):
        direct_branch.add(f"[red]{direct}[/red]")

    indirect_branch = tree.add("🌊 [bold magenta]Impacto Indireto (Efeito Cascata)[/bold magenta]")
    indirect_nodes = set()
    for changed in changed_files:
        if graph.has_node(changed):
            ancestors = set(nx.ancestors(graph, changed)) - set(changed_files) - direct_nodes
            indirect_nodes.update(ancestors)

    for indirect in sorted(list(indirect_nodes)):
        indirect_branch.add(f"[magenta]{indirect}[/magenta]")

    if show_unaffected:
        safe_branch = tree.add("🛡️ [bold green]Arquivos Seguros (Sem Impacto)[/bold green]")
        for safe in unaffected_files:
            safe_branch.add(f"[dim green]{safe}[/dim green]")

    console.print(tree)


def generate_ai_json_report(
    graph: nx.DiGraph,
    impact_result: Dict[str, Any],
    pretty: bool = True,
) -> str:
    """
    Gera um relatório estruturado em JSON otimizado para agentes de IA / LLMs.
    """
    payload = {
        "summary": {
            "total_files": impact_result.get("total_project_files", 0),
            "changed_files_count": len(impact_result.get("changed", [])),
            "direct_impact_count": len(impact_result.get("direct_impact", [])),
            "indirect_impact_count": len(impact_result.get("indirect_impact", [])),
            "unaffected_count": len(impact_result.get("unaffected", [])),
        },
        "changed_files": impact_result.get("changed", []),
        "impact_analysis": {
            "direct_impact": impact_result.get("direct_impact", []),
            "indirect_impact": impact_result.get("indirect_impact", []),
        },
        "unaffected_files": impact_result.get("unaffected", []),
    }
    return json.dumps(payload, indent=2 if pretty else None, ensure_ascii=False)


def generate_full_architectural_graph(
    graph: nx.DiGraph,
    output_path: Path,
    initial_layout: str = "hierarchical",
) -> Path:
    """
    Gera um relatório interativo em HTML de alta performance com layout Hierárquico
    (Raiz-Folha / Top-Down) e alternância dinâmica para Force-Directed.
    """
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Classificação dos nós por nível hierárquico (In-Degree vs Out-Degree)
    nodes_data = []
    for node in graph.nodes():
        in_degree = graph.in_degree(node)    # Quantos arquivos importam este
        out_degree = graph.out_degree(node)  # Quantos arquivos este importa

        # Determina o nível arquitetural
        if out_degree == 0 and in_degree > 0:
            level_group = "leaf"        # Utilitários / Camada Base
            color = "#10B981"          # Verde
        elif in_degree == 0 and out_degree > 0:
            level_group = "root"        # Entrypoints / CLI / Visão Externa
            color = "#3B82F6"          # Azul
        else:
            level_group = "intermediate"# Camada de Serviço / Regra de Negócio
            color = "#8B5CF6"          # Roxo

        nodes_data.append({
            "id": node,
            "label": node.split("/")[-1],
            "title": f"<b>{node}</b><br/>Entradas (Importado por): {in_degree}<br/>Saídas (Importa): {out_degree}",
            "group": level_group,
            "color": {"background": color, "border": "#1E293B"},
            "shape": "box",
            "margin": 10,
            "font": {"color": "#FFFFFF", "face": "Inter, system-ui, sans-serif"},
        })

    # 2. Processamento das Arestas (adicionando ID único para controle visual dinâmico)
    edges_data = []
    for idx, (u, v, data) in enumerate(graph.edges(data=True)):
        edge_type = data.get("type", "runtime")
        is_type_checking = edge_type == "type_checking"

        edges_data.append({
            "id": f"edge_{idx}",
            "from": u,
            "to": v,
            "arrows": "to",
            "dashes": is_type_checking,
            "color": {"color": "#94A3B8" if not is_type_checking else "#CBD5E1", "opacity": 0.6},
            "title": f"{u} ➔ {v} ({'Type Checking' if is_type_checking else 'Runtime'})",
        })

    # 3. Renderização da Template HTML5 com VisNetwork
    html_template = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Grafo Arquitetural Completo - ImpactTrace</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background-color: #0F172A;
            color: #F8FAFC;
            overflow: hidden;
            display: flex;
            height: 100vh;
        }}
        #sidebar {{
            width: 320px;
            background: #1E293B;
            border-right: 1px solid #334155;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            z-index: 10;
        }}
        #network-container {{
            flex: 1;
            height: 100%;
            background: radial-gradient(circle, #1e293b 1px, transparent 1px);
            background-size: 24px 24px;
        }}
        h1 {{ font-size: 1.25rem; font-weight: 700; color: #38BDF8; }}
        .section {{ background: #0F172A; padding: 12px; border-radius: 8px; border: 1px solid #334155; }}
        label {{ font-size: 0.85rem; color: #94A3B8; display: block; margin-bottom: 6px; }}
        select, input {{
            width: 100%;
            padding: 8px 12px;
            background: #1E293B;
            border: 1px solid #475569;
            color: #FFF;
            border-radius: 6px;
            outline: none;
        }}
        .legend-item {{ display: flex; align-items: center; gap: 8px; margin-top: 6px; font-size: 0.85rem; }}
        .dot {{ width: 12px; height: 12px; border-radius: 3px; display: inline-block; }}
        .stat-box {{ display: flex; justify-content: space-between; font-size: 0.85rem; margin-top: 4px; }}
    </style>
</head>
<body>

    <div id="sidebar">
        <div>
            <h1>🌌 Grafo Arquitetural</h1>
            <p style="font-size: 0.75rem; color: #64748B; margin-top: 4px;">ImpactTrace Architecture Mapper</p>
        </div>

        <div class="section">
            <label for="layout-select">Layout Visual:</label>
            <select id="layout-select" onchange="toggleLayout(this.value)">
                <option value="hierarchical" {'selected' if initial_layout == 'hierarchical' else ''}>Hierárquico (Raiz-Folha / Top-Down)</option>
                <option value="force" {'selected' if initial_layout == 'force' else ''}>Força-Dirigida (Physics Dynamic)</option>
            </select>
        </div>

        <div class="section">
            <label for="search-input">Buscar Módulo:</label>
            <input type="text" id="search-input" placeholder="Ex: cli.py, parser..." oninput="filterNodes(this.value)">
        </div>

        <div class="section">
            <label>Legenda Arquitetural:</label>
            <div class="legend-item"><span class="dot" style="background:#3B82F6;"></span> Raiz / Entrypoints (Topo)</div>
            <div class="legend-item"><span class="dot" style="background:#8B5CF6;"></span> Camada Intermediária</div>
            <div class="legend-item"><span class="dot" style="background:#10B981;"></span> Folha / Utilitários (Base)</div>
        </div>

        <div class="section">
            <label>Estatísticas do Grafo:</label>
            <div class="stat-box"><span>Total de Módulos:</span><b>{len(nodes_data)}</b></div>
            <div class="stat-box"><span>Relações de Dep.:</span><b>{len(edges_data)}</b></div>
        </div>
    </div>

    <div id="network-container"></div>

    <script type="text/javascript">
        const rawNodes = {json.dumps(nodes_data)};
        const rawEdges = {json.dumps(edges_data)};

        const nodes = new vis.DataSet(rawNodes);
        const edges = new vis.DataSet(rawEdges);

        const container = document.getElementById('network-container');
        const data = {{ nodes: nodes, edges: edges }};

        const hierarchicalOptions = {{
            layout: {{
                hierarchical: {{
                    enabled: true,
                    direction: 'UD',
                    sortMethod: 'directed',
                    nodeSpacing: 180,
                    levelSeparation: 150
                }}
            }},
            physics: false,
            interaction: {{ hover: true, tooltipDelay: 100 }}
        }};

        const forceOptions = {{
            layout: {{ hierarchical: {{ enabled: false }} }},
            physics: {{
                enabled: true,
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {{ gravitationalConstant: -50, centralGravity: 0.01, springLength: 100 }}
            }},
            interaction: {{ hover: true, tooltipDelay: 100 }}
        }};

        let network = new vis.Network(container, data, '{initial_layout}' === 'hierarchical' ? hierarchicalOptions : forceOptions);

        // Destaca as arestas conectadas ao nó clicado
        network.on("click", function (params) {{
            if (params.nodes.length > 0) {{
                const selectedNode = params.nodes[0];
                const connectedEdgeIds = network.getConnectedEdges(selectedNode);

                const updates = rawEdges.map(edge => {{
                    const isConnected = connectedEdgeIds.includes(edge.id);
                    return {{
                        id: edge.id,
                        color: isConnected 
                            ? {{ color: '#EF4444', highlight: '#EF4444', opacity: 1.0 }} 
                            : {{ color: '#334155', opacity: 0.15 }},
                        width: isConnected ? 3 : 1
                    }};
                }});

                edges.update(updates);
            }} else {{
                // Reseta todas as arestas ao clicar fora
                const resetUpdates = rawEdges.map(edge => ({{
                    id: edge.id,
                    color: edge.color,
                    width: 1
                }}));
                edges.update(resetUpdates);
            }}
        }});

        function toggleLayout(type) {{
            if (type === 'hierarchical') {{
                network.setOptions(hierarchicalOptions);
            }} else {{
                network.setOptions(forceOptions);
            }}
        }}

        function filterNodes(query) {{
            const q = query.toLowerCase().strip ? query.toLowerCase().strip() : query.toLowerCase();
            if (!q) {{
                nodes.forEach(node => nodes.update({{ id: node.id, hidden: false }}));
                return;
            }}
            nodes.forEach(node => {{
                const match = node.id.toLowerCase().includes(q);
                nodes.update({{ id: node.id, hidden: !match }});
            }});
        }}
    </script>
</body>
</html>
"""

    output_path.write_text(html_template, encoding="utf-8")
    return output_path


def generate_html_report(
    graph: nx.DiGraph,
    impact_result: Dict[str, Any],
    show_unaffected: bool = False,
    auto_open: bool = True,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Gera o relatório de impacto de alterações específicas.
    """
    if output_path is None:
        output_path = Path(".impact/impact_report.html")

    return generate_full_architectural_graph(graph, output_path, initial_layout="hierarchical")