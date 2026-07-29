from pathlib import Path
import pytest
from impact.parsers.base import BaseLanguageParser
from impact.parsers.registry import ParserRegistry


class MockParser(BaseLanguageParser):
    @property
    def supported_extensions(self):
        return {".mock", ".dummy"}

    def parse_file(self, file_path: Path, project_root: Path):
        return file_path.as_posix(), {"hash": "123", "runtime_imports": []}


def test_registry_registration_and_lookup():
    reg = ParserRegistry()
    parser = MockParser()

    reg.register(parser)

    # Asserção de busca por extensão (Case Insensitive)
    assert reg.get_parser_for_file(Path("file.mock")) == parser
    assert reg.get_parser_for_file(Path("FILE.MOCK")) == parser
    assert reg.get_parser_for_file(Path("file.dummy")) == parser
    assert reg.get_parser_for_file(Path("file.unknown")) is None


def test_registry_all_supported_extensions():
    reg = ParserRegistry()
    reg.register(MockParser())

    exts = reg.get_all_supported_extensions()
    assert ".mock" in exts
    assert ".dummy" in exts