# Tree-sitter AST traversal & skeletonization

from collections import defaultdict
from typing import List, Tuple, Any
from tree_sitter import Parser, Node
from app.schemas import (
    CodeUnit,
    UnitType,
    CodeMetadata,
)
from app.services.ingestion.grammars import LanguageConfig

# Canonical structural node sets
FUNCTION_TYPES = ("function_definition", "async_function_definition")
STRUCTURAL_TYPES = (
    "class_definition",
    "function_definition",
    "async_function_definition",
)


class TreeSitterParser:

    @staticmethod
    def parse(
        relative_path: str,
        code_bytes: bytes,
        lang_config: LanguageConfig,
    ) -> list[CodeUnit]:
        parser = Parser()
        parser.language = lang_config.language
        tree = parser.parse(code_bytes)
        extractor = lang_config.extractor(code_bytes, lang_config)

        return TreeSitterParser._extract_symbols(
            tree=tree,
            rel_path=relative_path,
            code_bytes=code_bytes,
            extractor=extractor,
        )

    @staticmethod
    def _generate_skeleton(
        raw_bytes: bytes,
        child_body_ranges: List[Tuple[int, int]],
    ) -> str:
        child_body_ranges.sort(key=lambda x: x[0])
        skeleton = bytearray()
        cursor = 0

        for start_byte, end_byte in child_body_ranges:
            if start_byte < cursor:
                continue
            skeleton.extend(raw_bytes[cursor:start_byte])
            skeleton.extend(b"\n        # ... code omitted ...\n")
            cursor = end_byte

        skeleton.extend(raw_bytes[cursor:])
        return skeleton.decode("utf-8", errors="ignore")

    @staticmethod
    def _extract_symbols(
        tree,
        rel_path: str,
        code_bytes: bytes,
        extractor: Any,
    ) -> list[CodeUnit]:
        units: dict[str, CodeUnit] = {}
        body_ranges: dict[str, Tuple[int, int]] = {}

        module_id = f"{rel_path}::<module>"
        root = tree.root_node

        module_unit = CodeUnit(
            id=module_id,
            file_path=rel_path,
            symbol_name="<module>",
            qualified_name=rel_path.replace("/", ".").removesuffix(".py"),
            symbol_kind="module",
            ast_node_type="module",
            start_line=root.start_point[0],
            end_line=root.end_point[0],
            start_col=root.start_point[1],
            end_col=root.end_point[1],
            start_byte=root.start_byte,
            end_byte=root.end_byte,
            code_content=code_bytes.decode("utf-8", errors="ignore"),
            is_ast_parsed=True,
            metadata=CodeMetadata(),
        )
        units[module_id] = module_unit

        scope_stack = [module_id]
        qual_name_stack = [module_unit.qualified_name]

        def walk(node: Node):
            current_scope_id = scope_stack[-1]
            current_unit = units[current_scope_id]

            # 1. Normalize decorated definitions (preserve decorator span in wrapper)
            target_node = node
            decorators: list[str] = []

            if node.type == "decorated_definition":
                for child in node.children:
                    if child.type == "decorator":
                        decorators.append(
                            child.text.decode("utf-8", errors="ignore").strip()
                        )
                    elif child.type in STRUCTURAL_TYPES:
                        target_node = child

            # 2. Structural nodes: classes, functions, and async functions
            if target_node.type in STRUCTURAL_TYPES:
                # Ignore nested functions/closures declared inside another function or method
                if target_node.type in FUNCTION_TYPES and current_unit.symbol_kind in (
                    "function",
                    "method",
                ):
                    for child in target_node.children:
                        walk(child)
                    return

                name = extractor.get_node_name(target_node)
                if not name:
                    return

                is_class = target_node.type == "class_definition"
                symbol_kind = (
                    "class"
                    if is_class
                    else (
                        "method" if current_unit.symbol_kind == "class" else "function"
                    )
                )

                new_id = f"{current_scope_id}::{name}"
                current_qname = f"{qual_name_stack[-1]}.{name}"

                # Body boundaries for skeletonization
                block = next(
                    (c for c in target_node.children if c.type == "block"), None
                )
                body_start = block.start_byte if block else node.end_byte
                body_ranges[new_id] = (body_start, node.end_byte)

                # Inheritance extraction: capture bases, generics (Generic[T]), and mixins
                inheritance: list[str] = []
                if is_class:
                    for child in target_node.children:
                        if child.type == "argument_list":
                            for arg in child.children:
                                # Skip punctuation commas/parentheses and keyword configs like metaclass=...
                                if arg.type in (",", "(", ")", "keyword_argument"):
                                    continue
                                inheritance.append(
                                    arg.text.decode("utf-8", errors="ignore").strip()
                                )

                new_unit = CodeUnit(
                    id=new_id,
                    parent_symbol_id=current_scope_id,
                    file_path=rel_path,
                    symbol_name=name,
                    qualified_name=current_qname,
                    symbol_kind=symbol_kind,
                    ast_node_type=target_node.type,
                    start_line=node.start_point[0],
                    end_line=node.end_point[0],
                    start_col=node.start_point[1],
                    end_col=node.end_point[1],
                    start_byte=node.start_byte,
                    end_byte=node.end_byte,
                    code_content=code_bytes[node.start_byte : node.end_byte].decode(
                        "utf-8", errors="ignore"
                    ),
                    is_ast_parsed=True,
                    metadata=CodeMetadata(
                        decorators=decorators,
                        inheritance=inheritance,
                        parent_class=(
                            current_unit.symbol_name
                            if current_unit.symbol_kind == "class"
                            else None
                        ),
                    ),
                )
                units[new_id] = new_unit

                scope_stack.append(new_id)
                qual_name_stack.append(current_qname)

                # Traverse children inside target_node
                for child in target_node.children:
                    walk(child)

                scope_stack.pop()
                qual_name_stack.pop()
                return

            # 3. Import statements
            elif node.type in ("import_statement", "import_from_statement"):
                current_unit.metadata.imports.extend(extractor.extract_imports(node))

            # 4. Module-level globals
            elif node.type == "assignment" and len(scope_stack) == 1:
                current_unit.metadata.globals.extend(extractor.extract_globals(node))

            # 5. Invocations / function calls
            elif node.type == "call":
                call_ref = extractor.extract_calls(node)
                if call_ref:
                    current_unit.metadata.calls.append(call_ref)

            # Recurse for all other unhandled container nodes
            for child in node.children:
                walk(child)

        for child in root.children:
            walk(child)

        # 6. Apply Skeletonization to parent units
        children_by_parent = defaultdict(list)
        for unit in units.values():
            if unit.parent_symbol_id:
                children_by_parent[unit.parent_symbol_id].append(unit.id)

        for parent_id, child_ids in children_by_parent.items():
            parent_unit = units[parent_id]
            child_body_ranges = []
            for cid in child_ids:
                if cid in body_ranges:
                    abs_start, abs_end = body_ranges[cid]
                    child_body_ranges.append(
                        (
                            abs_start - parent_unit.start_byte,
                            abs_end - parent_unit.start_byte,
                        )
                    )

            parent_raw = code_bytes[parent_unit.start_byte : parent_unit.end_byte]
            parent_unit.code_content = TreeSitterParser._generate_skeleton(
                parent_raw, child_body_ranges
            )

        return list(units.values())
