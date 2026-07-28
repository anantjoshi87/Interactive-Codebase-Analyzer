# Language bindings
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript
import tree_sitter_html as tshtml
import tree_sitter_css as tscss

from tree_sitter import Language

from .models import LanguageConfig
from .queries import (
    COMMON_JS_TS_QUERY,
    COMMON_PY_QUERY,
    HTML_QUERY,
    CSS_QUERY,
)


class LanguageRegistry:
    """Stores all Tree-sitter grammars and queries."""

    _registry: dict[str, LanguageConfig] | None = None

    @classmethod
    def get(cls) -> dict[str, LanguageConfig]:
        if cls._registry is not None:
            return cls._registry

        registry: dict[str, LanguageConfig] = {
            ".py": LanguageConfig(
                language=Language(tspython.language()),
                query=COMMON_PY_QUERY,
            ),
            ".js": LanguageConfig(
                language=Language(tsjavascript.language()),
                query=COMMON_JS_TS_QUERY,
            ),
            ".ts": LanguageConfig(
                language=Language(tstypescript.language_typescript()),
                query=COMMON_JS_TS_QUERY,
            ),
            ".tsx": LanguageConfig(
                language=Language(tstypescript.language_tsx()),
                query=COMMON_JS_TS_QUERY,
            ),
            ".html": LanguageConfig(
                language=Language(tshtml.language()),
                query=HTML_QUERY,
            ),
            ".css": LanguageConfig(
                language=Language(tscss.language()),
                query=CSS_QUERY,
            ),
        }

        # Add JSX support if the installed package exposes it
        if hasattr(tsjavascript, "language_jsx"):
            registry[".jsx"] = LanguageConfig(
                language=Language(tsjavascript.language_jsx()),
                query=COMMON_JS_TS_QUERY,
            )
        else:
            # Fallback to the normal JavaScript grammar
            registry[".jsx"] = LanguageConfig(
                language=Language(tsjavascript.language()),
                query=COMMON_JS_TS_QUERY,
            )

        cls._registry = registry
        return cls._registry
