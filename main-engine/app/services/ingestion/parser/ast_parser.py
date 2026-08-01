from tree_sitter import Parser, Node
from app.services.ingestion.models import (
    CodeUnit,
    UnitType,
    LanguageConfig,
    CodeMetadata,
)
from .extractors.extractor_factory import ExtractorFactory
from .extractors.base_extractor import BaseExtractor
from app.services.ingestion.specs.constants import SYMBOL_KIND_MAP


class TreeSitterParser:

    @staticmethod
    def parse(
        file_path: str, code_bytes: bytes, lang_config: LanguageConfig
    ) -> list[CodeUnit]:
        parser = Parser()
        parser.language = lang_config.language
        tree = parser.parse(code_bytes)
        extractor = ExtractorFactory.get_extractor(code_bytes, lang_config)

        return TreeSitterParser._extract_symbols(
            tree=tree,
            file_path=file_path,
            code_bytes=code_bytes,
            lang_config=lang_config,
            extractor=extractor,
        )

    @staticmethod
    def _extract_symbols(
        tree,
        file_path: str,
        code_bytes: bytes,
        lang_config: LanguageConfig,
        extractor: BaseExtractor,
    ) -> list[CodeUnit]:

        units: dict[str, CodeUnit] = {}

        # 1. Initialize the Base Module (Top of the file)
        module_id = f"{file_path}::<module>"
        module_unit = CodeUnit(
            id=module_id,
            file_path=file_path,
            unit_type=UnitType.CODE,
            symbol_name="<module>",
            symbol_kind="module",
            ast_node_type="module",
            start_line=1,
            end_line=tree.root_node.end_point[0] + 1,
            start_byte=tree.root_node.start_byte,
            end_byte=tree.root_node.end_byte,
            code_content=code_bytes.decode("utf-8", errors="ignore"),
            is_ast_parsed=True,
            metadata=CodeMetadata(),
        )
        units[module_id] = module_unit

        # 2. The Scope Stack
        scope_stack = [module_id]

        # 3. The AST Visitor
        def walk(node: Node):
            current_scope_id = scope_stack[-1]
            current_unit = units[current_scope_id]

            # --- A. Structural Nodes (Classes, Functions) ---
            if node.type in ("class_definition", "function_definition"):
                # Use the extractor to get the actual identifier node
                name = extractor.get_node_name(node)
                if not name:
                    return

                new_id = f"{current_scope_id}::{name}"
                symbol_kind = "class" if node.type == "class_definition" else "function"

                # Check if it's a method (function inside a class)
                if (
                    symbol_kind == "function"
                    and units[current_scope_id].symbol_kind == "class"
                ):
                    symbol_kind = "method"

                new_unit = CodeUnit(
                    id=new_id,
                    parent_symbol_id=current_scope_id,
                    file_path=file_path,
                    unit_type=UnitType.CODE,
                    symbol_name=name,
                    symbol_kind=symbol_kind,
                    ast_node_type=node.type,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    start_byte=node.start_byte,
                    end_byte=node.end_byte,
                    code_content=code_bytes[node.start_byte : node.end_byte].decode(
                        "utf-8", errors="ignore"
                    ),
                    is_ast_parsed=True,
                    metadata=CodeMetadata(
                        docstring=extractor.extract_docstring(node),
                        decorators=extractor.extract_decorators(node),
                        # Extract other structural metadata here
                    ),
                )
                units[new_id] = new_unit

                # Push to stack, process children, then pop
                scope_stack.append(new_id)
                for child in node.children:
                    walk(child)
                scope_stack.pop()

            # --- B. Scoped Metadata Nodes (Imports, Globals, Calls) ---
            elif node.type in ("import_statement", "import_from_statement"):
                imports = extractor.parse_import_node(node)
                current_unit.metadata.imports.extend(imports)

            elif node.type == "assignment":
                if len(scope_stack) == 1:
                    # We are at the module level, so this is a global variable
                    global_vars = extractor.parse_assignment_node(node)
                    current_unit.metadata.globals.extend(global_vars)

                # We MUST walk the children to catch calls like `unit.process()`
                # that exist on the right side of the equals sign!
                for child in node.children:
                    walk(child)

            elif node.type == "call":
                call_ref = extractor.parse_call_node(node)
                if call_ref:
                    current_unit.metadata.calls.append(call_ref)
                # Ensure we walk children of calls in case of nested calls ( e.g., foo(bar()) )
                for child in node.children:
                    walk(child)

            else:
                # Keep traversing down the tree
                for child in node.children:
                    walk(child)

        # 4. Start the traversal
        for child in tree.root_node.children:
            walk(child)

        return list(units.values())
