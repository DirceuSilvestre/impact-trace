from pathlib import Path
from impact.parsers.php_parser import PHPLanguageParser


def test_php_parser_psr4_and_includes(temp_project: Path):
    parser = PHPLanguageParser()

    # Arrange
    app_dir = temp_project / "app" / "Services"
    app_dir.mkdir(parents=True)

    service_file = app_dir / "PaymentService.php"
    service_file.write_text("<?php namespace App\\Services; class PaymentService {}", encoding="utf-8")

    index_file = temp_project / "index.php"
    index_file.write_text(
        """<?php
        use App\\Services\\PaymentService;
        require_once 'app/Services/PaymentService.php';
        """,
        encoding="utf-8",
    )

    # Act
    _, file_data = parser.parse_file(index_file, temp_project)

    # Assert
    assert "app/Services/PaymentService.php" in file_data["runtime_imports"]