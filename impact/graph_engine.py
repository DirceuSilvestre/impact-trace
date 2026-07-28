import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import networkx as nx

from impact.config import load_config


def build_graph(project_map: Dict[str, List[str]]) -> nx.DiGraph:
    """
    Recebe o mapa de dependências do scanner e constrói um Grafo Dirigido (DiGraph).

    Args:
        project_map (Dict[str, List[str]]): Dicionário { "arquivo.py": ["dependencia1.py"] }

    Returns:
        nx.DiGraph: Grafo dirigido do NetworkX onde cada nó é um arquivo do projeto.
    """
    graph = nx.DiGraph()

    # 1. Adiciona todos os arquivos como nós do grafo
    for file_path in project_map.keys():
        graph.add_node(file_path)

    # 2. Adiciona as conexões (Arestas/Edges)
    for source_file, dependencies in project_map.items():
        for dep_file in dependencies:
            graph.add_edge(source_file, dep_file)

    return graph


def calculate_impact(graph: nx.DiGraph, changed_files: List[str]) -> Dict[str, Any]:
    """
    Dado um grupo de arquivos alterados, calcula quais outros arquivos do projeto
    serão impactados diretamente ou indiretamente.

    Args:
        graph (nx.DiGraph): O grafo de dependências do projeto.
        changed_files (List[str]): Lista de caminhos relativos dos arquivos modificados.

    Returns:
        Dict[str, Any]: Dicionário com arquivos alterados, diretos e indiretamente afetados.
    """
    direct_impact: Set[str] = set()
    indirect_impact: Set[str] = set()

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

    return {
        "changed": changed_files,
        "direct_impact": sorted(list(direct_impact)),
        "indirect_impact": sorted(list(indirect_impact)),
        "total_affected_count": len(direct_impact) + len(indirect_impact),
    }


def save_graph_cache(graph: nx.DiGraph, root_dir: Path = Path(".")) -> Path:
    """
    Serializa o grafo do NetworkX no formato Node-Link e salva no arquivo .impact/cache.json.

    Args:
        graph (nx.DiGraph): O grafo a ser persistido.
        root_dir (Path): Diretório raiz do projeto.

    Returns:
        Path: O caminho do arquivo de cache onde os dados foram salvos.
    """
    root_dir = root_dir.resolve()
    config = load_config(root_dir)
    cache_rel_path = config.get("cache_file", ".impact/cache.json")
    cache_file_path = root_dir / cache_rel_path

    # Garante que a pasta do cache (ex: .impact/) existe antes de salvar
    cache_file_path.parent.mkdir(parents=True, exist_ok=True)

    # Converte a estrutura de dados do grafo em um dicionário compatível com JSON
    graph_data = nx.node_link_data(graph)

    with open(cache_file_path, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)

    return cache_file_path


def load_graph_cache(root_dir: Path = Path(".")) -> Optional[nx.DiGraph]:
    """
    Carrega e reconstrói o Grafo Dirigido do NetworkX a partir do arquivo .impact/cache.json.

    Args:
        root_dir (Path): Diretório raiz do projeto.

    Returns:
        Optional[nx.DiGraph]: Instância reconstruída do grafo ou None se não existir/estiver inválido.
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

        # Garante que o retorno seja explicitamente um Grafo Dirigido
        if not isinstance(graph, nx.DiGraph):
            graph = nx.DiGraph(graph)

        return graph

    except Exception:
        # Se o cache estiver corrompido ou num formato antigo, retorna None para forçar re-scan
        return None