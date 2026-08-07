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
    JS_SYMBOL_QUERY,
    JS_IMPORT_QUERY,
    JS_GLOBAL_QUERY,
    TS_SYMBOL_QUERY,
    TS_IMPORT_QUERY,
    TS_GLOBAL_QUERY,
    HTML_SYMBOL_QUERY,
    HTML_IMPORT_QUERY,
    HTML_GLOBAL_QUERY,
    CSS_SYMBOL_QUERY,
    CSS_IMPORT_QUERY,
    CSS_GLOBAL_QUERY,
)

from ..parser.extractors.python_extractor import PythonExtractor
from ..parser.extractors.javascript_extractor import JavascriptExtractor

# from ..parser.extractors.jsx_extractor import JSXExtractor


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

        # ---------------- JavaScript / TypeScript ---------------- #

        # js_config = LanguageConfig(
        #     language=Language(tsjavascript.language()),
        #     symbol_query=JS_SYMBOL_QUERY,
        #     import_query=JS_IMPORT_QUERY,
        #     global_query=JS_GLOBAL_QUERY,
        #     extractor=JavascriptExtractor,
        # )

        # jsx_config = LanguageConfig(
        #     language=Language(
        #         tsjavascript.language_jsx()
        #         if hasattr(tsjavascript, "language_jsx")
        #         else tsjavascript.language()
        #     ),
        #     symbol_query=JS_SYMBOL_QUERY,
        #     import_query=JS_IMPORT_QUERY,
        #     global_query=JS_GLOBAL_QUERY,
        #     extractor=JavascriptExtractor,
        # )

        # ts_config = LanguageConfig(
        #     language=Language(tstypescript.language_typescript()),
        #     symbol_query=TS_SYMBOL_QUERY,
        #     import_query=TS_IMPORT_QUERY,
        #     global_query=TS_GLOBAL_QUERY,
        # )

        # tsx_config = LanguageConfig(
        #     language=Language(tstypescript.language_tsx()),
        #     symbol_query=TS_SYMBOL_QUERY,
        #     import_query=TS_IMPORT_QUERY,
        #     global_query=TS_GLOBAL_QUERY,
        # )

        # ---------------- HTML ---------------- #

        # html_config = LanguageConfig(
        #     language=Language(tshtml.language()),
        #     symbol_query=HTML_SYMBOL_QUERY,
        #     import_query=HTML_IMPORT_QUERY,
        #     global_query=HTML_GLOBAL_QUERY,
        # )

        # # ---------------- CSS ---------------- #

        # css_config = LanguageConfig(
        #     language=Language(tscss.language()),
        #     symbol_query=CSS_SYMBOL_QUERY,
        #     import_query=CSS_IMPORT_QUERY,
        #     global_query=CSS_GLOBAL_QUERY,
        # )

        # ---------------- Registry ---------------- #

        cls._registry = {
            ".py": py_config,
            # ".js": js_config,
            # ".jsx": jsx_config,
            # ".ts": ts_config,
            # ".tsx": tsx_config,
            # ".html": html_config,
            # ".css": css_config,
        }

        return cls._registry
