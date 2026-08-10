from pathlib import Path
from .base_resolver import BaseResolver
import os
import re
from pathlib import Path
from .base_resolver import BaseResolver
from app.services.ingestion.models import CodeUnit

from ...specs.constants import BUILTIN_FUNCTIONS


class PythonResolver(BaseResolver):
    def __init__(self):
        # Frozen set of Python standard built-ins to ignore

        self.BUILTIN_FUNCTIONS = BUILTIN_FUNCTIONS

    def resolve_imports(
        self,
        units: list[CodeUnit],
    ) -> None:

        # Fast lookup for Phase 2
        unit_by_id = {u.id: u for u in units}

        # -----------------------------
        # Build file lookup
        # -----------------------------
        file_index: dict[str, list[CodeUnit]] = {}

        for unit in units:
            file_index.setdefault(
                str(Path(unit.file_path).resolve()),
                [],
            ).append(unit)

        # -----------------------------
        # PHASE 1: Base Resolution
        # -----------------------------
        for unit in units:
            current_file = Path(unit.file_path).resolve()

            for imp in unit.metadata.imports:
                module_path = imp.module if imp.module else imp.imported_name
                if not module_path:
                    continue

                target_file = self._resolve_import_file(current_file, module_path)
                if target_file is None:
                    continue

                candidates = file_index.get(str(target_file))
                if not candidates:
                    continue

                resolved_id = None
                module_candidate_id = None

                for candidate in candidates:
                    if candidate.symbol_name == imp.imported_name:
                        resolved_id = candidate.id
                        break
                    if candidate.symbol_kind == "module":
                        module_candidate_id = candidate.id

                imp.target_unit_id = resolved_id or module_candidate_id

        # -----------------------------
        # PHASE 2: Deep Resolution (Pointer Chasing)
        # -----------------------------
        # We loop until no more pointers can be chased, capping at depth=5
        # to prevent infinite loops in the case of circular module imports.
        changed = True
        max_depth = 5
        depth = 0

        while changed and depth < max_depth:
            changed = False
            depth += 1

            for unit in units:
                for imp in unit.metadata.imports:
                    # If we don't have a target, or we don't have a specific symbol name, skip
                    if not imp.target_unit_id or not imp.imported_name:
                        continue

                    # If our target points to a module (like __init__.py), it might be a barrel file
                    if imp.target_unit_id.endswith("::<module>"):
                        target_module = unit_by_id.get(imp.target_unit_id)

                        if target_module:
                            # Look inside the barrel file's imports
                            for barrel_imp in target_module.metadata.imports:
                                # What name does the barrel file expose it as?
                                barrel_export_name = (
                                    barrel_imp.alias
                                    if barrel_imp.alias
                                    else barrel_imp.imported_name
                                )

                                # If the barrel file exports the thing we are looking for...
                                if barrel_export_name == imp.imported_name:
                                    # ...and it points somewhere deeper than our current pointer
                                    if (
                                        barrel_imp.target_unit_id
                                        and imp.target_unit_id
                                        != barrel_imp.target_unit_id
                                    ):
                                        # Steal the deeper pointer!
                                        imp.target_unit_id = barrel_imp.target_unit_id
                                        changed = True
                                    break

    def _resolve_import_file(
        self,
        current_file: Path,
        module: str,
        repo_root: Path | None = None,  # Optional repo_root parameter
    ) -> Path | None:

        level = 0
        clean_module = module

        while clean_module.startswith("."):
            level += 1
            clean_module = clean_module[1:]

        # -------------------------------------------------------------
        # 1. Relative Import Handling (e.g. from .base import X)
        # -------------------------------------------------------------
        if level > 0:
            package_dir = current_file.parent
            for _ in range(level - 1):
                package_dir = package_dir.parent

            if clean_module:
                relative = Path(*clean_module.split("."))
                file_candidate = package_dir / f"{relative}.py"
                if file_candidate.exists():
                    return file_candidate.resolve()

                init_candidate = package_dir / relative / "__init__.py"
                if init_candidate.exists():
                    return init_candidate.resolve()
            else:
                init_candidate = package_dir / "__init__.py"
                if init_candidate.exists():
                    return init_candidate.resolve()

            return None

        # -------------------------------------------------------------
        # 2. Absolute Import Handling (e.g. from app.config import Settings)
        # -------------------------------------------------------------
        relative = Path(*clean_module.split("."))

        # Search location candidates: current directory AND parent roots
        search_dirs = []

        # Add current package directory first
        search_dirs.append(current_file.parent)

        # Walk up parent directories to find repository root containing 'app/'
        curr = current_file.parent
        while curr != curr.parent:
            search_dirs.append(curr)
            curr = curr.parent

        for base_dir in search_dirs:
            # Check direct module file: e.g. GraphRAG / app / config.py
            file_candidate = base_dir / f"{relative}.py"
            if file_candidate.exists():
                return file_candidate.resolve()

            # Check package init: e.g. GraphRAG / app / config / __init__.py
            init_candidate = base_dir / relative / "__init__.py"
            if init_candidate.exists():
                return init_candidate.resolve()

        return None

    @staticmethod
    def _normalize_id(symbol_id: str | None) -> str | None:
        """Ensures consistent path formatting across OS platforms."""
        if not symbol_id:
            return None
        if "::<module>" in symbol_id:
            file_part, symbol_part = symbol_id.split("::<module>", 1)
            return f"{os.path.normpath(file_part)}::<module>{symbol_part}"
        return os.path.normpath(symbol_id)

    def resolve_calls(self, units: list[CodeUnit]) -> None:
        unit_by_id = {self._normalize_id(u.id): u for u in units}

        # ------------------------------------------------------------------
        # 1. Pre-build Map of Class Units -> Class Field Types
        # ------------------------------------------------------------------
        class_attribute_types: dict[str, dict[str, str]] = {}
        for unit in units:
            if unit.symbol_kind == "class":
                attrs = {}
                for method in units:
                    if method.parent_symbol_id == unit.id:
                        for glob in method.metadata.globals:
                            if glob.name and glob.value:
                                # Clean 'self.' or 'cls.' prefixes safely
                                clean_name = glob.name
                                if clean_name.startswith(("self.", "cls.")):
                                    clean_name = clean_name.split(".", 1)[1]

                                val = glob.value.strip()

                                # Handle pipe chain assignments: self.chain = prompt | llm | parser
                                if "|" in val:
                                    last_expr = val.split("|")[-1].strip()
                                    inferred_class = (
                                        last_expr.split("(")[0].strip().split(".")[-1]
                                    )
                                    if inferred_class:
                                        attrs[clean_name] = inferred_class

                                # Handle standard constructor instantiations: self.vector = VectorRetriever()
                                elif "(" in val:
                                    inferred_class = (
                                        val.split("(")[0].strip().split(".")[-1]
                                    )
                                    if inferred_class:
                                        attrs[clean_name] = inferred_class

                class_attribute_types[self._normalize_id(unit.id)] = attrs

        for unit in units:
            # 1. Local scope (symbols in same file)
            local_scope = {
                u.symbol_name: self._normalize_id(u.id)
                for u in units
                if u.file_path == unit.file_path and u.id != unit.id
            }

            # 2. Import scope
            import_scope = {}
            module_id = self._normalize_id(f"{unit.file_path}::<module>")
            module_unit = unit_by_id.get(module_id)
            if module_unit:
                for imp in module_unit.metadata.imports:
                    name = imp.alias if imp.alias else imp.imported_name
                    if name and imp.target_unit_id:
                        import_scope[name] = self._normalize_id(imp.target_unit_id)

            # 3. Variable Scope Tracker
            variable_types = {}

            # Inherit module-level script globals
            if module_unit and module_unit.metadata.globals:
                for glob in module_unit.metadata.globals:
                    if glob.name and glob.value and "(" in glob.value:
                        inferred = glob.value.split("(")[0].strip().split(".")[-1]
                        variable_types[glob.name] = inferred

            for glob in unit.metadata.globals:
                if glob.name and glob.value and "(" in glob.value:
                    inferred = glob.value.split("(")[0].strip().split(".")[-1]
                    variable_types[glob.name] = inferred

            # Method-level local assignments
            for c in unit.metadata.calls:
                if c.method in import_scope or c.method in local_scope:
                    target_symbol_id = import_scope.get(c.method) or local_scope.get(
                        c.method
                    )
                    target_u = (
                        unit_by_id.get(self._normalize_id(target_symbol_id))
                        if target_symbol_id
                        else None
                    )

                    if (target_u and target_u.symbol_kind == "class") or (
                        c.method and c.method[0].isupper()
                    ):
                        for line_str in unit.code_content.splitlines():
                            if f"{c.method}(" in line_str and "=" in line_str:
                                var_name = line_str.split("=")[0].strip()
                                variable_types[var_name] = c.method

            # Function Parameter Type Hints
            if unit.symbol_kind in ("function", "method") and unit.code_content:
                sig_match = re.search(
                    r"def\s+\w+\s*\((.*?)\)", unit.code_content, re.DOTALL
                )
                if sig_match:
                    params_str = sig_match.group(1)
                    for match in re.finditer(r"(\w+)\s*:\s*([^,=\)]+)", params_str):
                        var_name = match.group(1).strip()
                        type_str = match.group(2).strip()

                        type_words = re.findall(r"[a-zA-Z_]\w*", type_str)
                        ignored_typing = {
                            "Optional",
                            "Union",
                            "list",
                            "dict",
                            "set",
                            "tuple",
                            "Any",
                            "str",
                            "int",
                            "bool",
                            "float",
                            "bytes",
                            "Sequence",
                            "Mapping",
                        }
                        valid_types = [w for w in type_words if w not in ignored_typing]
                        if valid_types:
                            variable_types[var_name] = valid_types[-1]

            parent_class_id = self._normalize_id(unit.parent_symbol_id)

            # ------------------------------------------------------------------
            # 4. Resolve Calls
            # ------------------------------------------------------------------
            valid_calls = []
            for call in unit.metadata.calls:
                # Early Filter for Language Built-ins
                if not call.receiver and call.method in self.BUILTIN_FUNCTIONS:
                    if (
                        call.callee not in local_scope
                        and call.callee not in import_scope
                    ):
                        continue

                target_id = None
                call_type = "FUNCTION_CALL"

                # Case A: Direct Function / Constructor Call
                if not call.receiver:
                    if call.callee in local_scope:
                        target_id = local_scope[call.callee]
                    elif call.callee in import_scope:
                        target_id = import_scope[call.callee]

                    if target_id:
                        target_u = unit_by_id.get(self._normalize_id(target_id))
                        if target_u and target_u.symbol_kind == "class":
                            call_type = "INSTANTIATION"

                # Case B: Method Call with Receiver
                else:
                    call_type = "METHOD_CALL"

                    # 1. Receiver is 'self' or 'cls'
                    if call.receiver in ("self", "cls") and parent_class_id:
                        target_id = f"{parent_class_id}::{call.method}"

                    # 2. Receiver is an Instance Attribute (e.g. self.vector.retrieve)
                    elif (
                        call.receiver.startswith(("self.", "cls.")) and parent_class_id
                    ):
                        attr_parts = call.receiver.split(".")
                        if len(attr_parts) >= 2:
                            attr_name = attr_parts[1].strip()
                            parent_attrs = class_attribute_types.get(
                                parent_class_id, {}
                            )
                            if attr_name in parent_attrs:
                                var_class = parent_attrs[attr_name]
                                if var_class in import_scope:
                                    target_id = (
                                        f"{import_scope[var_class]}::{call.method}"
                                    )
                                elif var_class in local_scope:
                                    target_id = (
                                        f"{local_scope[var_class]}::{call.method}"
                                    )

                    # 3. Receiver is an imported module/class
                    elif call.receiver in import_scope:
                        target_id = f"{import_scope[call.receiver]}::{call.method}"

                    # 4. Receiver is a local class
                    elif call.receiver in local_scope:
                        target_id = f"{local_scope[call.receiver]}::{call.method}"

                    # 5. Receiver is a tracked local or global variable
                    elif call.receiver in variable_types:
                        var_class = variable_types[call.receiver]
                        if var_class in import_scope:
                            target_id = f"{import_scope[var_class]}::{call.method}"
                        elif var_class in local_scope:
                            target_id = f"{local_scope[var_class]}::{call.method}"

                # Normalize and validate constructed target_ids
                normalized_target = self._normalize_id(target_id)

                if normalized_target and normalized_target in unit_by_id:
                    call.target_unit_id = normalized_target
                    call.confidence = "HIGH"
                else:
                    call.target_unit_id = None
                    call.confidence = "LOW"

                call.call_type = call_type
                valid_calls.append(call)

            unit.metadata.calls = valid_calls
