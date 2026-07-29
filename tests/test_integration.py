from pathlib import Path
from impact.ast_parser import scan_project_incremental


def test_incremental_scan_multi_language_monorepo(temp_project: Path):
    # 1. ARRANGE: Criar Monorepo com arquivos em várias linguagens
    py_file = temp_project / "main.py"
    py_file.write_text("import os", encoding="utf-8")

    ts_file = temp_project / "index.ts"
    ts_file.write_text("console.log('TS');", encoding="utf-8")

    go_file = temp_project / "main.go"
    go_file.write_text("package main", encoding="utf-8")

    # 2. ACT: Primeira Varredura (Sem Cache)
    project_map_1, stats_1 = scan_project_incremental(temp_project)

    # 3. ASSERT: Primeira Varredura
    assert stats_1["total_files"] == 3
    assert stats_1["reparsed"] == 3
    assert stats_1["cache_hits"] == 0
    assert "main.py" in project_map_1
    assert "index.ts" in project_map_1
    assert "main.go" in project_map_1

    # 4. ACT: Segunda Varredura (Com Cache / Sem alterações)
    cache_payload = {"files": project_map_1}
    project_map_2, stats_2 = scan_project_incremental(
        temp_project, existing_cache=cache_payload
    )

    # 5. ASSERT: Segunda Varredura (100% Cache Hits em O(N))
    assert stats_2["total_files"] == 3
    assert stats_2["reparsed"] == 0
    assert stats_2["cache_hits"] == 3

    # 6. ACT: Modificar apenas o arquivo TypeScript
    ts_file.write_text("console.log('TS Updated');", encoding="utf-8")
    project_map_3, stats_3 = scan_project_incremental(
        temp_project, existing_cache={"files": project_map_2}
    )

    # 7. ASSERT: Apenas o arquivo alterado foi re-analisado!
    assert stats_3["total_files"] == 3
    assert stats_3["reparsed"] == 1
    assert stats_3["cache_hits"] == 2