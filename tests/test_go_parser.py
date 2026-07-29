from pathlib import Path
from impact.parsers.go_parser import GoLanguageParser


def test_go_parser_with_go_mod(temp_project: Path):
    parser = GoLanguageParser()

    # Arrange: Criar go.mod
    go_mod = temp_project / "go.mod"
    go_mod.write_text("module github.com/empresa/meu-app\n\ngo 1.22\n")

    # Criar subpacote pkg/auth
    auth_dir = temp_project / "pkg" / "auth"
    auth_dir.mkdir(parents=True)
    (auth_dir / "auth.go").write_text("package auth", encoding="utf-8")

    # Arquivo principal main.go
    main_file = temp_project / "main.go"
    main_file.write_text(
        """
        package main

        import (
            "fmt"
            "github.com/empresa/meu-app/pkg/auth"
        )

        func main() { fmt.Println("Go") }
        """,
        encoding="utf-8",
    )

    # Act
    _, file_data = parser.parse_file(main_file, temp_project)

    # Assert
    assert "pkg/auth" in file_data["runtime_imports"]