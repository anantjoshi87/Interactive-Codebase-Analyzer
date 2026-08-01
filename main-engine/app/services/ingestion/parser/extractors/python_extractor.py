from tree_sitter import Node
from app.services.ingestion.models import ImportReference, GlobalVariable, CallReference
from .base_extractor import BaseExtractor


class PythonExtractor(BaseExtractor):

    def get_node_name(self, node: Node) -> str | None:
        """Helper to get the name of a class or function."""
        # Tree-sitter python grammar usually names the identifier field "name"
        name_node = node.child_by_field_name("name")
        if name_node:
            return self.node_text(name_node)
        return None

    def parse_import_node(self, node: Node) -> list[ImportReference]:
        """Parses a single import_statement or import_from_statement node."""
        imports = []

        if node.type == "import_statement":
            # Handles: import os, sys
            for child in node.children:
                if child.type == "dotted_name":
                    imports.append(ImportReference(module=self.node_text(child)))
                elif child.type == "aliased_import":
                    # Handles: import numpy as np
                    orig = child.child_by_field_name("name")
                    alias = child.child_by_field_name("alias")
                    if orig and alias:
                        imports.append(
                            ImportReference(
                                module=self.node_text(orig), alias=self.node_text(alias)
                            )
                        )

        elif node.type == "import_from_statement":
            # Handles: from typing import List, Dict
            module_node = node.child_by_field_name("module_name")
            module_name = self.node_text(module_node) if module_node else ""

            for child in node.children:
                if child.type == "dotted_name":
                    imports.append(
                        ImportReference(
                            module=module_name, imported_name=self.node_text(child)
                        )
                    )
                elif child.type == "aliased_import":
                    # Handles: from bs4 import BeautifulSoup as bs
                    orig = child.child_by_field_name("name")
                    alias = child.child_by_field_name("alias")
                    if orig and alias:
                        imports.append(
                            ImportReference(
                                module=module_name,
                                imported_name=self.node_text(orig),
                                alias=self.node_text(alias),
                            )
                        )

        return imports

    def parse_assignment_node(self, node: Node) -> list[GlobalVariable]:
        """Parses an assignment to extract global variables."""
        globals_ = []
        # The left side of an assignment can be multiple targets (e.g., a, b = 1, 2)
        left_node = node.child_by_field_name("left")

        if left_node and left_node.type == "identifier":
            name = self.node_text(left_node)
            # You can also extract the 'right' field to get the value
            right_node = node.child_by_field_name("right")
            val = self.node_text(right_node) if right_node else None

            globals_.append(
                GlobalVariable(name=name, value=val, line=node.start_point[0] + 1)
            )
        return globals_

    def parse_call_node(self, node: Node) -> CallReference | None:
        """Extracts function/method calls."""
        func_node = node.child_by_field_name("function")
        if not func_node:
            return None

        # If it's a method call: self.db.insert
        if func_node.type == "attribute":
            receiver = func_node.child_by_field_name("object")
            method = func_node.child_by_field_name("attribute")
            if receiver and method:
                return CallReference(
                    receiver=self.node_text(receiver),
                    method=self.node_text(method),
                    callee=self.node_text(func_node),
                    line=node.start_point[0] + 1,
                )

        # If it's a standard function call: print("hello")
        elif func_node.type == "identifier":
            return CallReference(
                method=self.node_text(func_node),
                callee=self.node_text(func_node),
                line=node.start_point[0] + 1,
            )

        return None
