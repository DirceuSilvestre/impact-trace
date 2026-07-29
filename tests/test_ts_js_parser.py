from pathlib import Path
from impact.parsers.ts_js_parser import TSJSModuleParser


def test_ts_js_parser_resolves_relative_and_aliases(temp_project: Path):
    parser = TSJSModuleParser()

    # Arrange
    src = temp_project / "src"
    src.mkdir()

    button_file = src / "Button.tsx"
    button_file.write_text("export const Button = () => null;", encoding="utf-8")

    utils_file = src / "utils.ts"
    utils_file.write_text("export const help = () => {};", encoding="utf-8")

    main_file = src / "App.tsx"
    main_file.write_text(
        """
        import { Button } from './Button';
        import { help } from '@/utils';
        import lodash from 'lodash'; // Deve ignorar (node_modules)
        """,
        encoding="utf-8",
    )

    # Act
    rel_path, file_data = parser.parse_file(main_file, temp_project)

    # Assert
    assert rel_path == "src/App.tsx"
    assert "src/Button.tsx" in file_data["runtime_imports"]
    assert "src/utils.ts" in file_data["runtime_imports"]
    assert "lodash" not in file_data["runtime_imports"]