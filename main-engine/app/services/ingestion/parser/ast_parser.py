from tree_sitter import Parser, Query, QueryCursor
from .models import (
    CodeUnit,
    UnitType,
    LanguageConfig,
    CodeMetadata,
    Reference,
    ImportReference,
    GlobalVariable,
)
from .constants import SYMBOL_KIND_MAP


class TreeSitterParser:
    @staticmethod
    def parse(
        file_path: str,
        code_bytes: bytes,
        lang_config: LanguageConfig,
    ) -> list[CodeUnit]:

        parser = Parser()
        parser.language = lang_config.language

        tree = parser.parse(code_bytes)

        return TreeSitterParser._extract_symbols(
            tree=tree,
            file_path=file_path,
            code_bytes=code_bytes,
            lang_config=lang_config,
        )

    @staticmethod
    def _extract_symbols(
        tree,
        file_path: str,
        code_bytes: bytes,
        lang_config: LanguageConfig,
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
                    id=f"{file_path}::{name}",
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
                    metadata=CodeMetadata(
                        imports=TreeSitterParser._extract_imports(
                            tree,
                            code_bytes,
                            lang_config,
                        ),
                        globals=TreeSitterParser._extract_globals(
                            tree,
                            code_bytes,
                            lang_config,
                        ),
                        decorators=TreeSitterParser._extract_decorators(
                            node,
                            code_bytes,
                        ),
                        parent_class=TreeSitterParser._extract_parent_class(
                            node,
                            code_bytes,
                        ),
                        docstring=TreeSitterParser._extract_docstring(
                            node,
                            code_bytes,
                        ),
                        references=TreeSitterParser._extract_references(
                            node,
                            code_bytes,
                        ),
                        calls=[],
                        inheritance=[],
                        overrides=[],
                        annotations=[],
                        exceptions=[],
                        returns=None,
                    ),
                    is_ast_parsed=True,
                )
            )

        return units

    @staticmethod
    def _extract_imports(
        tree,
        code_bytes: bytes,
        lang_config: LanguageConfig,
    ) -> list[ImportReference]:

        if not lang_config.import_query.strip():
            return []

        query = Query(lang_config.language, lang_config.import_query)
        cursor = QueryCursor(query)

        imports: list[ImportReference] = []

        for _, captures in cursor.matches(tree.root_node):

            node = captures.get("import", [None])[0]

            if node is None:
                continue

            raw = code_bytes[node.start_byte : node.end_byte].decode(
                "utf-8",
                errors="ignore",
            )

            # Python: import os
            if raw.startswith("import "):
                modules = raw.replace("import ", "").split(",")

                for module in modules:
                    imports.append(
                        ImportReference(
                            module=module.strip(),
                            imported_name=None,
                            alias=None,
                            target_unit_id=None,
                        )
                    )

            # Python: from x import y,z
            elif raw.startswith("from "):

                left, right = raw.split(" import ", 1)

                module = left.replace("from ", "").strip()

                for symbol in right.split(","):

                    imports.append(
                        ImportReference(
                            module=module,
                            imported_name=symbol.strip(),
                            alias=None,
                            target_unit_id=None,
                        )
                    )

        return imports

    @staticmethod
    def _extract_globals(
        tree,
        code_bytes: bytes,
        lang_config: LanguageConfig,
    ) -> list[GlobalVariable]:

        if not lang_config.global_query.strip():
            return []

        query = Query(lang_config.language, lang_config.global_query)
        cursor = QueryCursor(query)

        globals_: list[GlobalVariable] = []

        for _, captures in cursor.matches(tree.root_node):

            node = captures.get("global", [None])[0]

            if node is None:
                continue

            text = code_bytes[node.start_byte : node.end_byte].decode(
                "utf-8",
                errors="ignore",
            )

            name = text.split("=")[0].strip() if "=" in text else text.strip()

            globals_.append(
                GlobalVariable(
                    name=name,
                    value=text,
                    line=node.start_point[0] + 1,
                )
            )

        return globals_

    @staticmethod
    def _extract_decorators(node, code_bytes):

        decorators = []

        for child in node.children:

            if child.type == "decorated_definition":

                for c in child.children:

                    if c.type == "decorator":

                        decorators.append(
                            code_bytes[c.start_byte : c.end_byte].decode(
                                "utf-8",
                                errors="ignore",
                            )
                        )

        return decorators

    @staticmethod
    def _extract_parent_class(node, code_bytes):

        parent = node.parent

        while parent is not None:

            if parent.type == "class_definition":

                for child in parent.children:

                    if child.type == "identifier":

                        return code_bytes[child.start_byte : child.end_byte].decode(
                            "utf-8", errors="ignore"
                        )

            parent = parent.parent

        return None

    @staticmethod
    def _extract_docstring(node, code_bytes):

        body = None

        for child in node.children:

            if child.type == "block":
                body = child
                break

        if body is None:
            return None

        for child in body.children:

            if child.type == "expression_statement":

                for grand in child.children:

                    if grand.type == "string":

                        return code_bytes[grand.start_byte : grand.end_byte].decode(
                            "utf-8",
                            errors="ignore",
                        )

                break

        return None

    @staticmethod
    def _extract_references(node, code_bytes):

        references = []

        # def dfs(n):

        #     if n.type == "identifier":

        #         references.append(
        #             Reference(
        #                 name=code_bytes[n.start_byte : n.end_byte].decode(
        #                     "utf-8",
        #                     errors="ignore",
        #                 )
        #             )
        #         )

        #     for child in n.children:
        #         dfs(child)

        # dfs(node)

        return references
