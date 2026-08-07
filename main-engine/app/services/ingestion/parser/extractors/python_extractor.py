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
        imports = []

        if node.type == "import_statement":
            # Handles: import os, sys
            for child in node.children:
                if child.type == "dotted_name":
                    name = child.text.decode("utf-8")
                    imports.append(
                        ImportReference(module=name, imported_name=name, alias=None)
                    )
                elif child.type == "aliased_import":
                    # Handles: import numpy as np
                    name = child.child_by_field_name("name").text.decode("utf-8")
                    alias = child.child_by_field_name("alias").text.decode("utf-8")
                    imports.append(
                        ImportReference(module=name, imported_name=name, alias=alias)
                    )

        elif node.type == "import_from_statement":
            # Handles: from app.models import CodeUnit
            module_node = node.child_by_field_name("module_name")
            module_name = module_node.text.decode("utf-8") if module_node else ""

            for child in node.children:
                # --- THE FIX: Skip the module_node so it isn't treated as an imported symbol ---
                if module_node and child.id == module_node.id:
                    continue
                # -------------------------------------------------------------------------------

                if child.type == "dotted_name":
                    name = child.text.decode("utf-8")
                    imports.append(
                        ImportReference(
                            module=module_name, imported_name=name, alias=None
                        )
                    )
                elif child.type == "aliased_import":
                    name = child.child_by_field_name("name").text.decode("utf-8")
                    alias = child.child_by_field_name("alias").text.decode("utf-8")
                    imports.append(
                        ImportReference(
                            module=module_name, imported_name=name, alias=alias
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
