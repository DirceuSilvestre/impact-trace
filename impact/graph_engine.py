import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx

CACHE_FILE_VERSION = "2.0.0"


def build_graph(project_map: Dict[str, Any], include_type_checking: bool = False) -> nx.DiGraph:
    """
    Constrói um Grafo Direcionado (DiGraph) do NetworkX a partir do mapa do projeto.
    
    Convenção do Grafo:
    Aresta (A -> B) significa: A importa B (A depende de B).
    Predecessores de B (predecessors): Módulos que importam B (Consumidores/Afetados).
    """
    graph = nx.DiGraph()

    # Adiciona todos os arquivos mapeados como nós
    for file_path in project_map.keys():
        graph.add_node(file_path)

    # Conecta as arestas de dependência
    for source_file, data in project_map.items():
        # Arestas de Runtime (Uso Real)
        for target_file in data.get("runtime_imports", []):
            if graph.has_node(target_file):
                graph.add_edge(source_file, target_file, type="runtime")

        # Arestas de Type Checking (Opcional)
        if include_type_checking:
            for target_file in data.get("type_checking_imports", []):
                if graph.has_node(target_file):
                    graph.add_edge(source_file, target_file, type="type_checking")

    return graph


def calculate_impact(graph: nx.DiGraph, changed_files: List[str]) -> Dict[str, Any]:
    """
    Calcula a propagação do impacto a partir dos arquivos alterados no Git.
    """
    changed_set = set(changed_files)
    direct_impact: Set[str] = set()
    indirect_impact: Set[str] = set()

    all_project_nodes = set(graph.nodes())

    for changed in changed_files:
        if not graph.has_node(changed):
            continue

        # Impacto Direto: Módulos que importam diretamente o arquivo alterado
        direct_consumers = set(graph.predecessors(changed)) - changed_set
        direct_impact.update(direct_consumers)

        # Impacto Indireto: Cascata em todos os níveis acima
        all_ancestors = set(nx.ancestors(graph, changed)) - changed_set - direct_consumers
        indirect_impact.update(all_ancestors)

    unaffected = sorted(list(all_project_nodes - changed_set - direct_impact - indirect_impact))

    return {
        "changed": sorted(list(changed_set)),
        "direct_impact": sorted(list(direct_impact)),
        "indirect_impact": sorted(list(indirect_impact)),
        "unaffected": unaffected,
        "total_affected_count": len(direct_impact) + len(indirect_impact),
        "total_project_files": len(all_project_nodes),
    }


def save_graph_cache(
    project_map: Dict[str, Any],
    graph: nx.DiGraph,
    project_root: Path,
    cache_rel_path: str = ".impact/cache.json",
) -> Path:
    """
    Salva o cache consolidado com metadados de Hash SHA-256 e estrutura do grafo.
    """
    cache_path = project_root.resolve() / cache_rel_path
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": CACHE_FILE_VERSION,
        "files": project_map,
        "graph_nodes": list(graph.nodes()),
        "graph_edges": [
            {
                "source": u,
                "target": v,
                "type": graph.edges[u, v].get("type", "runtime"),
            }
            for u, v in graph.edges()
        ],
    }

    cache_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return cache_path


def load_graph_cache(
    project_root: Path, cache_rel_path: str = ".impact/cache.json"
) -> Tuple[Optional[nx.DiGraph], Optional[Dict[str, Any]]]:
    """
    Carrega o grafo e os metadados do arquivo de cache JSON.
    """
    cache_path = project_root.resolve() / cache_rel_path

    if not cache_path.is_file():
        return None, None

    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        if data.get("version") != CACHE_FILE_VERSION:
            return None, None

        graph = nx.DiGraph()
        for node in data.get("graph_nodes", []):
            graph.add_node(node)

        for edge in data.get("graph_edges", []):
            graph.add_edge(edge["source"], edge["target"], type=edge.get("type", "runtime"))

        return graph, data
    except (json.JSONDecodeError, KeyError, OSError):
        return None, None