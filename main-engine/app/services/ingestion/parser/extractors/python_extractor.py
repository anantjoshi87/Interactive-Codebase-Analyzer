from typing import List, Optional
from tree_sitter import Node
from app.services.ingestion.models import (
    ImportReference,
    GlobalVariable,
    CallReference,
    LanguageConfig,
)
from .base_extractor import BaseExtractor
from ...specs.constants import PYTHON_BUILTINS


class PythonExtractor(BaseExtractor):
    def __init__(self, code_bytes: bytes, lang_config: LanguageConfig):
        super().__init__(code_bytes, lang_config)

    def get_node_name(self, node: Node) -> Optional[str]:
        """
        Works for 'class_definition', 'function_definition',
        and 'async_function_definition'.
        """
        name_node = node.child_by_field_name("name")
        if name_node:
            return self._node_text(name_node)
        return None

    def extract_imports(self, node: Node) -> List[ImportReference]:
        results: List[ImportReference] = []
        line_num = node.start_point[0]

        if node.type == "import_statement":
            for child in node.children:
                if child.type == "dotted_name":
                    results.append(
                        ImportReference(
                            module=self._node_text(child),
                            imported_name=None,
                            alias=None,
                            line=line_num,
                        )
                    )
                elif child.type == "aliased_import":
                    name_child = child.child_by_field_name("name")
                    alias_child = child.child_by_field_name("alias")
                    if name_child and alias_child:
                        results.append(
                            ImportReference(
                                module=self._node_text(name_child),
                                imported_name=None,
                                alias=self._node_text(alias_child),
                                line=line_num,
                            )
                        )

        elif node.type == "import_from_statement":
            module_name = ""
            module_node = node.child_by_field_name("module_name")
            if module_node:
                module_name = self._node_text(module_node)

            dots = ""
            for child in node.children:
                if child.type == "import_prefix":
                    dots = self._node_text(child)
                    break
                if child.type == ".":
                    dots += "."

            full_module = f"{dots}{module_name}" if dots else module_name

            for child in node.children:
                if child.type == "dotted_name" and child != module_node:
                    results.append(
                        ImportReference(
                            module=full_module,
                            imported_name=self._node_text(child),
                            alias=None,
                            line=line_num,
                        )
                    )
                elif child.type == "aliased_import":
                    name_child = child.child_by_field_name("name")
                    alias_child = child.child_by_field_name("alias")
                    if name_child and alias_child:
                        results.append(
                            ImportReference(
                                module=full_module,
                                imported_name=self._node_text(name_child),
                                alias=self._node_text(alias_child),
                                line=line_num,
                            )
                        )
                elif child.type == "wildcard_import":
                    results.append(
                        ImportReference(
                            module=full_module,
                            imported_name="*",
                            alias=None,
                            line=line_num,
                        )
                    )

        return results

    def extract_globals(self, node: Node) -> List[GlobalVariable]:
        results: List[GlobalVariable] = []
        line_num = node.start_point[0]

        left_node = node.child_by_field_name("left")
        right_node = node.child_by_field_name("right")
        type_node = node.child_by_field_name("type")

        val_repr = self._node_text(right_node) if right_node else None
        type_repr = self._node_text(type_node) if type_node else None

        if not left_node:
            return results

        if left_node.type == "identifier":
            results.append(
                GlobalVariable(
                    name=self._node_text(left_node),
                    declaration_type=type_repr,
                    value=val_repr,
                    line=line_num,
                )
            )
        elif left_node.type in ("pattern_list", "tuple_pattern", "list_pattern"):
            for elem in left_node.children:
                if elem.type == "identifier":
                    results.append(
                        GlobalVariable(
                            name=self._node_text(elem),
                            declaration_type=None,
                            value=None,
                            line=line_num,
                        )
                    )

        return results

    def extract_calls(
        self, node: Node, filter_builtins: bool = True
    ) -> Optional[CallReference]:
        if node.type != "call":
            return None

        function_node = node.child_by_field_name("function")
        if not function_node:
            return None

        line = node.start_point[0]
        callee_text = self._node_text(function_node)

        # 1. Simple function call: func(...)
        if function_node.type == "identifier":
            method_name = callee_text

            if filter_builtins and method_name in PYTHON_BUILTINS:
                return None

            return CallReference(
                receiver=None,
                method=method_name,
                callee=callee_text,
                call_type="FUNCTION_CALL",
                line=line,
                column=function_node.start_point[1],
            )

        # 2. Attribute / Method call: receiver.method(...) or complex.receiver().method(...)
        if function_node.type == "attribute":
            obj_node = function_node.child_by_field_name("object")
            attr_node = function_node.child_by_field_name("attribute")

            receiver_str = self._node_text(obj_node) if obj_node else None
            method_str = self._node_text(attr_node) if attr_node else callee_text
            col = (
                attr_node.start_point[1] if attr_node else function_node.start_point[1]
            )

            call_type = "METHOD_CALL"
            if receiver_str in ("self", "cls"):
                call_type = "INTERNAL_METHOD_CALL"
            elif obj_node and obj_node.type == "call":
                call_type = "CHAINED_METHOD_CALL"

            return CallReference(
                receiver=receiver_str,
                method=method_str,
                callee=callee_text,
                call_type=call_type,
                line=line,
                column=col,
            )

        # 3. Fallback for nested or computed function calls
        return CallReference(
            receiver=callee_text.rpartition(".")[0] if "." in callee_text else None,
            method=(
                callee_text.rpartition(".")[2] if "." in callee_text else callee_text
            ),
            callee=callee_text,
            call_type="DYNAMIC_OR_COMPUTED_CALL",
            line=line,
            column=function_node.start_point[1],
        )
