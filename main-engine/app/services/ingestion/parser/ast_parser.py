from tree_sitter import Parser, Query, QueryCursor
from .models import CodeUnit, UnitType, LanguageConfig
from .constants import SYMBOL_KIND_MAP


class TreeSitterParser:
    @staticmethod
    def parse(
        file_path: str,
        code_bytes: bytes,
        lang_config: LanguageConfig,
    ) -> list[CodeUnit]:
        """Parse a source file using Tree-sitter."""

        parser = Parser()
        parser.language = lang_config.language

        tree = parser.parse(code_bytes)

        query = Query(
            lang_config.language,
            lang_config.query,
        )

        cursor = QueryCursor(query)

        units: list[CodeUnit] = []

        # matches = list(cursor.matches(tree.root_node))
        # print(type(matches))
        # print(matches)

        for _, captures in cursor.matches(tree.root_node):

            node = captures.get("symbol.node", [None])[0]

            if node is None:
                continue

            name_node = captures.get("symbol.name", [None])[0]

            name = None
            if name_node is not None:
                name = code_bytes[name_node.start_byte : name_node.end_byte].decode(
                    "utf-8"
                )

            name = code_bytes[name_node.start_byte : name_node.end_byte].decode(
                "utf-8", errors="ignore"
            )

            symbol_code = code_bytes[node.start_byte : node.end_byte].decode(
                "utf-8", errors="ignore"
            )

            symbol_kind = SYMBOL_KIND_MAP.get(node.type, "unknown")

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
                    is_ast_parsed=True,
                )
            )

        return units
