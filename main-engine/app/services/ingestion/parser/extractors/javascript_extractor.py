from tree_sitter import Node, Query, QueryCursor

from .base_extractor import BaseExtractor
from app.services.ingestion.models import (
    ImportReference,
    GlobalVariable,
    CallReference,
    Reference,
    LanguageConfig,
)


class JavascriptExtractor(BaseExtractor):
    """
    Extract metadata from JavaScript / JSX files.
    """

    def __init__(self, code_bytes: bytes, lang_config: LanguageConfig):
        super().__init__(code_bytes, lang_config)

    def extract_imports(self, root: Node) -> list[ImportReference]:
        if not self.config.import_query.strip():
            return []

        query = Query(self.language, self.config.import_query)
        cursor = QueryCursor(query)
        imports: list[ImportReference] = []

        for _, captures in cursor.matches(root):
            node = captures.get("import", [None])[0]
            if node is None:
                continue

            raw = self.node_text(node).strip()

            # import "./globals.css";
            if " from " not in raw:
                module = raw.replace("import", "").replace(";", "").strip().strip("'\"")
                imports.append(ImportReference(module=module))
                continue

            # import { useState, useEffect } from "react";
            left, right = raw.split(" from ", 1)
            module = right.replace(";", "").strip().strip("'\"")
            left = left.replace("import", "").strip()

            if left.startswith("{"):
                names = left.strip("{}").split(",")
                for name in names:
                    imports.append(
                        ImportReference(
                            module=module,
                            imported_name=name.strip(),
                        )
                    )
                continue

            # import * as React from "react"
            if left.startswith("* as"):
                alias = left.replace("* as", "").strip()
                imports.append(
                    ImportReference(
                        module=module,
                        alias=alias,
                    )
                )
                continue

            # import Header from "./Header"
            imports.append(
                ImportReference(
                    module=module,
                    imported_name=left,
                )
            )

        return imports

    def extract_globals(self, root: Node) -> list[GlobalVariable]:
        if not self.config.global_query.strip():
            return []

        query = Query(self.language, self.config.global_query)
        cursor = QueryCursor(query)
        globals_: list[GlobalVariable] = []

        for _, captures in cursor.matches(root):
            node = captures.get("global", [None])[0]
            if node is None:
                continue

            declaration_type = None
            name = None
            value = None

            if node.children:
                declaration_type = self.node_text(node.children[0])

            for child in node.children:
                if child.type != "variable_declarator":
                    continue

                for grand in child.children:
                    if grand.type == "identifier":
                        name = self.node_text(grand)
                        break

                if len(child.children) >= 3:
                    value = self.node_text(child.children[-1])

                break

            if name is None:
                continue

            globals_.append(
                GlobalVariable(
                    name=name,
                    declaration_type=declaration_type,
                    value=value,
                    line=node.start_point[0] + 1,
                )
            )

        return globals_

    def extract_calls(self, node: Node) -> list[CallReference]:
        calls: list[CallReference] = []
        seen = set()

        def dfs(n: Node):
            if n.type == "call_expression":
                function_node = n.child_by_field_name("function")
                if function_node is not None:
                    callee = self.node_text(function_node)

                    # Split callee into receiver and method
                    receiver = None
                    method = callee

                    if "." in callee:
                        parts = callee.rsplit(".", 1)
                        receiver = parts[0]  # e.g., "JSON" or "client.models"
                        method = parts[1]  # e.g., "stringify" or "generate_content"

                    key = (
                        callee,
                        function_node.start_point[0],
                        function_node.start_point[1],
                    )

                    if key not in seen:
                        seen.add(key)
                        calls.append(
                            CallReference(
                                receiver=receiver,
                                method=method,
                                callee=callee,
                                target_unit_id=None,
                                line=function_node.start_point[0] + 1,
                                column=function_node.start_point[1] + 1,
                            )
                        )

            for child in n.children:
                dfs(child)

        dfs(node)
        return calls

    def extract_parent_class(self, node: Node) -> str | None:
        parent = node.parent
        while parent is not None:
            if parent.type == "class_declaration":
                name_node = parent.child_by_field_name("name")
                if name_node is not None:
                    return self.node_text(name_node)
            parent = parent.parent
        return None

    def extract_references(self, node: Node) -> list[Reference]:
        references = []
        ignored_parents = {
            "call",
            "import_statement",
            "import_from_statement",
            "function_definition",
            "class_definition",
            "parameters",
            "decorator",
        }
        visited = set()

        def walk(n: Node):
            if n.type == "identifier":
                parent_type = n.parent.type if n.parent else ""
                if parent_type not in ignored_parents:
                    name = self.node_text(n)
                    if name not in visited:
                        visited.add(name)
                        references.append(Reference(name=name))

            for child in n.children:
                walk(child)

        walk(node)
        return references
