from pathlib import Path
from impact.parsers.java_kotlin_parser import JavaKotlinLanguageParser


def test_java_kotlin_package_resolution(temp_project: Path):
    parser = JavaKotlinLanguageParser()

    # Arrange
    java_dir = temp_project / "src" / "main" / "java" / "com" / "empresa" / "services"
    java_dir.mkdir(parents=True)

    user_service = java_dir / "UserService.java"
    user_service.write_text("package com.empresa.services; public class UserService {}", encoding="utf-8")

    controller_dir = temp_project / "src" / "main" / "kotlin" / "com" / "empresa" / "controllers"
    controller_dir.mkdir(parents=True)

    controller = controller_dir / "UserController.kt"
    controller.write_text(
        """
        package com.empresa.controllers
        import com.empresa.services.UserService

        class UserController
        """,
        encoding="utf-8",
    )

    # Act
    _, file_data = parser.parse_file(controller, temp_project)

    # Assert
    assert "src/main/java/com/empresa/services/UserService.java" in file_data["runtime_imports"]