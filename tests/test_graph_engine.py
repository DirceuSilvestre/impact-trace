from pathlib import Path
from impact.graph_engine import (
    build_graph,
    calculate_impact,
    load_graph_cache,
    save_graph_cache,
)


def test_build_graph_and_calculate_upstream_impact():
    # Estrutura: main.py -> services.py -> db.py
    project_map = {
        "db.py": {"runtime_imports": []},
        "services.py": {"runtime_imports": ["db.py"]},
        "main.py": {"runtime_imports": ["services.py"]},
        "utils.py": {"runtime_imports": []},
    }

    graph = build_graph(project_map)

    # Se db.py mudar, deve impactar services.py (direto) e main.py (indireto/cascata)
    impact = calculate_impact(graph, changed_files=["db.py"])

    assert impact["changed"] == ["db.py"]
    assert impact["direct_impact"] == ["services.py"]
    assert impact["indirect_impact"] == ["main.py"]
    assert "utils.py" in impact["unaffected"]
    assert impact["total_affected_count"] == 2


def test_save_and_load_graph_cache(tmp_path: Path):
    project_map = {"main.py": {"hash": "abc", "runtime_imports": []}}
    graph = build_graph(project_map)

    cache_file = save_graph_cache(project_map, graph, tmp_path)
    assert cache_file.is_file()

    loaded_graph, loaded_data = load_graph_cache(tmp_path)
    assert loaded_graph is not None
    assert "main.py" in loaded_graph.nodes()
    assert loaded_data["files"]["main.py"]["hash"] == "abc"