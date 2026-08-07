from tree_sitter import Parser, Node
from app.services.ingestion.models import (
    CodeUnit,
    UnitType,
    LanguageConfig,
    CodeMetadata,
)
from .extractors.extractor_factory import ExtractorFactory
from .extractors.base_extractor import BaseExtractor

# from app.services.ingestion.specs.constants import SYMBOL_KIND_MAP
from typing import List, Tuple
from collections import defaultdict


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
    def _generate_skeleton(
        raw_module_bytes: bytes, child_body_ranges: List[Tuple[int, int]]
    ) -> str:
        """
        Replaces the bodies of child nodes with a placeholder to save LLM tokens.
        """
        child_body_ranges.sort(key=lambda x: x[0])

        skeleton = bytearray()
        current_idx = 0

        for body_start, end_byte in child_body_ranges:
            if body_start < current_idx:
                continue

            skeleton.extend(raw_module_bytes[current_idx:body_start])
            skeleton.extend(b"\n        # ... code omitted ...\n")
            current_idx = end_byte

        skeleton.extend(raw_module_bytes[current_idx:])
        return skeleton.decode("utf-8")

    @staticmethod
    def _extract_symbols(
        tree,
        file_path: str,
        code_bytes: bytes,
        lang_config: LanguageConfig,
        extractor: BaseExtractor,
    ) -> list[CodeUnit]:

        units: dict[str, CodeUnit] = {}

        # Dictionary to store the (body_start_byte, end_byte) for skeletonization
        body_ranges: dict[str, Tuple[int, int]] = {}

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

                # --- INTEGRATION 1: Ignore Nested Functions ---
                if node.type == "function_definition" and current_unit.symbol_kind in [
                    "function",
                    "method",
                ]:
                    # We are inside a function already. Don't create a CodeUnit for this nested function.
                    # Just walk its children to capture assignments or API calls it makes.
                    for child in node.children:
                        walk(child)
                    return
                # ----------------------------------------------

                name = extractor.get_node_name(node)
                if not name:
                    return

                new_id = f"{current_scope_id}::{name}"
                symbol_kind = "class" if node.type == "class_definition" else "function"

                if symbol_kind == "function" and current_unit.symbol_kind == "class":
                    symbol_kind = "method"

                # --- INTEGRATION 2: Track Body Start Bytes ---
                # Tree-sitter Python groups the body inside a "block" node.
                # If absent (e.g. one-liners), fallback to node.end_byte safely.
                block_node = next((c for c in node.children if c.type == "block"), None)
                body_start = block_node.start_byte if block_node else node.end_byte
                body_ranges[new_id] = (body_start, node.end_byte)
                # ---------------------------------------------

                # --- INTEGRATION: Extract Decorators, Inheritance, and Returns ---
                decorators = []
                inheritance = []

                # 1. Extract Decorators (Check parent for 'decorated_definition')
                if node.parent and node.parent.type == "decorated_definition":
                    for sibling in node.parent.children:
                        if sibling.type == "decorator":
                            decorators.append(sibling.text.decode("utf-8").strip())

                # 2. Extract Inheritance (Base Classes)
                if node.type == "class_definition":
                    for child in node.children:
                        if child.type == "argument_list":
                            for arg in child.children:
                                if arg.type == "identifier":
                                    inheritance.append(arg.text.decode("utf-8").strip())

                # -----------------------------------------------------------------

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
                        decorators=decorators,
                        inheritance=inheritance,
                    ),
                )
                units[new_id] = new_unit

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
                    global_vars = extractor.parse_assignment_node(node)
                    current_unit.metadata.globals.extend(global_vars)
                for child in node.children:
                    walk(child)

            elif node.type == "call":
                call_ref = extractor.parse_call_node(node)
                if call_ref:
                    current_unit.metadata.calls.append(call_ref)
                for child in node.children:
                    walk(child)
            else:
                for child in node.children:
                    walk(child)

        # 4. Start the traversal
        for child in tree.root_node.children:
            walk(child)

        # --- INTEGRATION 3: Apply Skeletonization to Parents ---
        # Map children to their parent unit to easily process skeletons
        children_by_parent = defaultdict(list)
        for unit_id, unit in units.items():
            if unit.parent_symbol_id:
                children_by_parent[unit.parent_symbol_id].append(unit_id)

        for parent_id, parent_unit in units.items():
            child_ids = children_by_parent.get(parent_id, [])

            # If the node has no children (e.g. leaf functions), it needs no skeleton
            if not child_ids:
                continue

            child_body_ranges = []
            for cid in child_ids:
                if cid in body_ranges:
                    absolute_body_start, absolute_end = body_ranges[cid]

                    # Convert absolute bytes (file level) to relative bytes (parent slice level)
                    rel_start = absolute_body_start - parent_unit.start_byte
                    rel_end = absolute_end - parent_unit.start_byte
                    child_body_ranges.append((rel_start, rel_end))

            # Slice the raw bytes for just this parent node
            parent_raw_bytes = code_bytes[parent_unit.start_byte : parent_unit.end_byte]

            # Generate the skeleton and overwrite the code_content
            # The LLM will now read this skeletonized version!
            skeleton_string = TreeSitterParser._generate_skeleton(
                parent_raw_bytes, child_body_ranges
            )
            parent_unit.code_content = skeleton_string
        # -------------------------------------------------------

        return list(units.values())
