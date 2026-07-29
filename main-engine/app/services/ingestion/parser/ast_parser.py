from tree_sitter import Parser, Query, QueryCursor
from .models import CodeUnit, UnitType, LanguageConfig
from .constants import SYMBOL_KIND_MAP


class TreeSitterParser:
    @staticmethod
    @staticmethod
    def parse(
        file_path: str,
        code_bytes: bytes,
        lang_config: LanguageConfig,
    ) -> list[CodeUnit]:

        parser = Parser()
        parser.language = lang_config.language

        tree = parser.parse(code_bytes)

        imports = TreeSitterParser._extract_imports(
            tree,
            code_bytes,
            lang_config,
        )

        globals_ = TreeSitterParser._extract_globals(
            tree,
            code_bytes,
            lang_config,
        )

        metadata = {
            "imports": imports,
            "globals": globals_,
        }

        return TreeSitterParser._extract_symbols(
            tree=tree,
            file_path=file_path,
            code_bytes=code_bytes,
            lang_config=lang_config,
            metadata=metadata,
        )

    @staticmethod
    def _extract_symbols(
        tree,
        file_path: str,
        code_bytes: bytes,
        lang_config: LanguageConfig,
        metadata: dict = None,
    ) -> list[CodeUnit]:

        query = Query(
            lang_config.language,
            lang_config.symbol_query,
        )

        cursor = QueryCursor(query)

        units: list[CodeUnit] = []

        for _, captures in cursor.matches(tree.root_node):

            node = captures.get("symbol.node", [None])[0]

            if node is None:
                continue

            name_node = captures.get("symbol.name", [None])[0]

            name = None
            if name_node is not None:
                name = code_bytes[name_node.start_byte : name_node.end_byte].decode(
                    "utf-8",
                    errors="ignore",
                )

            symbol_code = code_bytes[node.start_byte : node.end_byte].decode(
                "utf-8",
                errors="ignore",
            )

            symbol_kind = SYMBOL_KIND_MAP.get(
                node.type,
                "unknown",
            )

            units.append(
                CodeUnit(
                    file_path=file_path,
                    unit_type=UnitType.CODE,
                    symbol_name=name,
                    symbol_kind=symbol_kind,
                    ast_node_type=node.type,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    start_byte=node.start_byte,
                    end_byte=node.end_byte,
                    code_content=symbol_code,
                    metadata=metadata,
                    is_ast_parsed=True,
                )
            )

        return units

    @staticmethod
    def _extract_imports(
        tree,
        code_bytes: bytes,
        lang_config: LanguageConfig,
    ) -> list[str]:

        if not lang_config.import_query.strip():
            return []

        query = Query(
            lang_config.language,
            lang_config.import_query,
        )

        cursor = QueryCursor(query)

        imports = []

        for _, captures in cursor.matches(tree.root_node):

            node = captures.get("import", [None])[0]

            if node is None:
                continue

            imports.append(
                code_bytes[node.start_byte : node.end_byte].decode(
                    "utf-8",
                    errors="ignore",
                )
            )

        return imports

    @staticmethod
    def _extract_globals(
        tree,
        code_bytes: bytes,
        lang_config: LanguageConfig,
    ) -> list[str]:

        if not lang_config.global_query.strip():
            return []

        query = Query(
            lang_config.language,
            lang_config.global_query,
        )

        cursor = QueryCursor(query)

        globals_ = []

        for _, captures in cursor.matches(tree.root_node):

            node = captures.get("global", [None])[0]

            if node is None:
                continue

            globals_.append(
                code_bytes[node.start_byte : node.end_byte].decode(
                    "utf-8",
                    errors="ignore",
                )
            )

        return globals_
