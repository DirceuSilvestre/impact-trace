import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import networkx as nx

from impact.config import load_config


def build_graph(project_map: Dict[str, List[str]]) -> nx.DiGraph:
    """
    Construi um Grafo Dirigido (DiGraph) do NetworkX a partir do mapa do scanner.
    """
    graph = nx.DiGraph()

    for file_path in project_map.keys():
        graph.add_node(file_path)

    for source_file, dependencies in project_map.items():
        for dep_file in dependencies:
            graph.add_edge(source_file, dep_file)

    return graph


def calculate_impact(graph: nx.DiGraph, changed_files: List[str]) -> Dict[str, Any]:
    """
    Calcula o impacto direto, indireto e identifica os arquivos 100% seguros/não afetados.
    """
    direct_impact: Set[str] = set()
    indirect_impact: Set[str] = set()
    all_nodes: Set[str] = set(graph.nodes())

    for changed_file in changed_files:
        if not graph.has_node(changed_file):
            continue

        all_affected = nx.ancestors(graph, changed_file)
        direct_predecessors = set(graph.predecessors(changed_file))

        for affected in all_affected:
            if affected in changed_files:
                continue

            if affected in direct_predecessors:
                direct_impact.add(affected)
            else:
                indirect_impact.add(affected)

    # Cálculo computacionalmente eficiente O(N) dos arquivos 100% seguros
    affected_or_changed = set(changed_files) | direct_impact | indirect_impact
    unaffected_files = sorted(list(all_nodes - affected_or_changed))

    return {
        "changed": changed_files,
        "direct_impact": sorted(list(direct_impact)),
        "indirect_impact": sorted(list(indirect_impact)),
        "unaffected": unaffected_files,
        "total_affected_count": len(direct_impact) + len(indirect_impact),
        "total_project_files": len(all_nodes),
    }


def save_graph_cache(graph: nx.DiGraph, root_dir: Path = Path(".")) -> Path:
    """
    Serializa o grafo no formato Node-Link e salva em .impact/cache.json.
    """
    root_dir = root_dir.resolve()
    config = load_config(root_dir)
    cache_rel_path = config.get("cache_file", ".impact/cache.json")
    cache_file_path = root_dir / cache_rel_path

    cache_file_path.parent.mkdir(parents=True, exist_ok=True)
    graph_data = nx.node_link_data(graph)

    with open(cache_file_path, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)

    return cache_file_path


def load_graph_cache(root_dir: Path = Path(".")) -> Optional[nx.DiGraph]:
    """
    Carrega o Grafo Dirigido do arquivo .impact/cache.json.
    """
    root_dir = root_dir.resolve()
    config = load_config(root_dir)
    cache_rel_path = config.get("cache_file", ".impact/cache.json")
    cache_file_path = root_dir / cache_rel_path

    if not cache_file_path.exists():
        return None

    try:
        with open(cache_file_path, "r", encoding="utf-8") as f:
            graph_data = json.load(f)

        graph = nx.node_link_graph(graph_data)
        if not isinstance(graph, nx.DiGraph):
            graph = nx.DiGraph(graph)

        return graph

    except Exception:
        return None