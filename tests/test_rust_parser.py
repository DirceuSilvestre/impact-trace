from pathlib import Path
from impact.parsers.rust_parser import RustLanguageParser


def test_rust_parser_resolves_crate_and_submodules(temp_project: Path):
    parser = RustLanguageParser()

    # Arrange
    src = temp_project / "src"
    src.mkdir()

    # src/auth.rs
    (src / "auth.rs").write_text("pub fn login() {}", encoding="utf-8")

    # src/models/mod.rs
    models_dir = src / "models"
    models_dir.mkdir()
    (models_dir / "mod.rs").write_text("pub struct User;", encoding="utf-8")

    # src/main.rs
    main_rs = src / "main.rs"
    main_rs.write_text(
        """
        mod auth;
        use crate::models::User;

        fn main() {}
        """,
        encoding="utf-8",
    )

    # Act
    _, file_data = parser.parse_file(main_rs, temp_project)

    # Assert
    assert "src/auth.rs" in file_data["runtime_imports"]
    assert "src/models/mod.rs" in file_data["runtime_imports"]