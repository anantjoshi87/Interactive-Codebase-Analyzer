# Language bindings
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript
import tree_sitter_html as tshtml
import tree_sitter_css as tscss

from tree_sitter import Language

from app.services.ingestion.models import LanguageConfig
from ..parser.extractors.base_extractor import BaseExtractor
from .queries import (
    PY_SYMBOL_QUERY,
    PY_IMPORT_QUERY,
    PY_GLOBAL_QUERY,
)

from ..parser.extractors.python_extractor import PythonExtractor

class LanguageRegistry:
    """Stores all supported Tree-sitter grammars and queries."""

    _registry: dict[str, LanguageConfig] | None = None

    @classmethod
    def get(cls) -> dict[str, LanguageConfig]:

        if cls._registry is not None:
            return cls._registry

        # Resolve the forward reference in LanguageConfig.extractor before
        # we instantiate any Pydantic models.
        LanguageConfig.model_rebuild()

        # ---------------- Python ---------------- #

        py_config = LanguageConfig(
            language=Language(tspython.language()),
            symbol_query=PY_SYMBOL_QUERY,
            import_query=PY_IMPORT_QUERY,
            global_query=PY_GLOBAL_QUERY,
            extractor=PythonExtractor,
        )

        # ---------------- Registry ---------------- #

        cls._registry = {
            ".py": py_config,
        }

        return cls._registry
