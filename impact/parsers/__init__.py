from impact.parsers.csharp_parser import CSharpLanguageParser
from impact.parsers.go_parser import GoLanguageParser
from impact.parsers.java_kotlin_parser import JavaKotlinLanguageParser
from impact.parsers.php_parser import PHPLanguageParser
from impact.parsers.python_parser import PythonLanguageParser
from impact.parsers.registry import registry
from impact.parsers.rust_parser import RustLanguageParser
from impact.parsers.ts_js_parser import TSJSModuleParser

# Autoregistro automático dos parsers de todas as linguagens suportadas
registry.register(PythonLanguageParser())
registry.register(TSJSModuleParser())
registry.register(GoLanguageParser())
registry.register(JavaKotlinLanguageParser())
registry.register(CSharpLanguageParser())
registry.register(RustLanguageParser())
registry.register(PHPLanguageParser())

__all__ = ["registry"]