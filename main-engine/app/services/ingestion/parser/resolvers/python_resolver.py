from pathlib import Path
from .base_resolver import BaseResolver

from app.services.ingestion.models import (
    CodeUnit,
)

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
    ) -> Path | None:

        level = 0

        while module.startswith("."):
            level += 1
            module = module[1:]

        package_dir = current_file.parent

        for _ in range(level - 1):
            package_dir = package_dir.parent

        if module:
            relative = Path(*module.split("."))

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

    def resolve_calls(self, units: list[CodeUnit]) -> None:
        import re  # Ensure re is imported for type hint extraction

        unit_by_id = {u.id: u for u in units}

        # Pre-build a map of Class Units -> Class Field Types (self.attr = Class())
        class_attribute_types: dict[str, dict[str, str]] = {}
        for unit in units:
            if unit.symbol_kind == "class":
                attrs = {}
                for method in units:
                    if method.parent_symbol_id == unit.id:
                        for glob in method.metadata.globals:
                            if (
                                glob.name
                                and glob.name.startswith("self.")
                                and glob.value
                                and "(" in glob.value
                            ):
                                attr_name = glob.name.replace("self.", "").strip()
                                inferred_class = (
                                    glob.value.split("(")[0].strip().split(".")[-1]
                                )
                                attrs[attr_name] = inferred_class
                class_attribute_types[unit.id] = attrs

        for unit in units:
            # 1. Build Local Scope (symbols in same file)
            local_scope = {
                u.symbol_name: u.id
                for u in units
                if u.file_path == unit.file_path and u.id != unit.id
            }

            # 2. Build Import Scope
            # Check module unit for file or current file's parent module
            import_scope = {}
            module_id = f"{unit.file_path}::<module>"
            module_unit = unit_by_id.get(module_id)
            if module_unit:
                for imp in module_unit.metadata.imports:
                    name = imp.alias if imp.alias else imp.imported_name
                    if name and imp.target_unit_id:
                        import_scope[name] = imp.target_unit_id

            # 3. Variable Scope Tracker (Globals + Method-Local Instantiations + Type Hints)
            variable_types = {}

            # A) Module-level globals (e.g. unit = CodeUnit())
            for glob in unit.metadata.globals:
                if glob.name and glob.value and "(" in glob.value:
                    inferred = glob.value.split("(")[0].strip().split(".")[-1]
                    variable_types[glob.name] = inferred

            # B) Method-level local variables (e.g. unit = CodeUnit("test_unit"))
            # Scan calls inside this unit to catch local assignments
            for c in unit.metadata.calls:
                # If a call looks like a constructor call, map any variable used before '.' on subsequent calls
                if c.method in import_scope or c.method in local_scope:
                    # Check if target is a class
                    target_symbol_id = import_scope.get(c.method) or local_scope.get(
                        c.method
                    )
                    target_u = (
                        unit_by_id.get(target_symbol_id) if target_symbol_id else None
                    )
                    if (target_u and target_u.symbol_kind == "class") or c.method[
                        0
                    ].isupper():
                        # Extract left-hand side variable name if present in code content line
                        for line_str in unit.code_content.splitlines():
                            if f"{c.method}(" in line_str and "=" in line_str:
                                var_name = line_str.split("=")[0].strip()
                                variable_types[var_name] = c.method

            # C) Function Parameter Type Hints (e.g. unit: CodeUnit)
            if unit.symbol_kind in ("function", "method") and unit.code_content:
                sig_match = re.search(
                    r"def\s+\w+\s*\((.*?)\)", unit.code_content, re.DOTALL
                )
                if sig_match:
                    params_str = sig_match.group(1)
                    # Find patterns like "var_name: TypeName"
                    for match in re.finditer(r"(\w+)\s*:\s*([^,=\)]+)", params_str):
                        var_name = match.group(1).strip()
                        type_str = match.group(2).strip()

                        # Extract core class names (ignores wrappers like Optional, list)
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

            parent_class_id = unit.parent_symbol_id

            # 4. Resolve Calls
            valid_calls = []
            for call in unit.metadata.calls:
                # EARLY FILTER: Drop un-shadowed language built-ins (print, len, range, str, int, etc.)
                if not call.receiver and call.method in self.BUILTIN_FUNCTIONS:
                    if (
                        call.callee not in local_scope
                        and call.callee not in import_scope
                    ):
                        continue  # Completely skip built-ins—do NOT append to valid_calls

                target_id = None
                call_type = "FUNCTION_CALL"

                # Case A: Direct Function / Constructor Call (No receiver)
                if not call.receiver:
                    if call.callee in local_scope:
                        target_id = local_scope[call.callee]
                    elif call.callee in import_scope:
                        target_id = import_scope[call.callee]

                    if target_id:
                        target_u = unit_by_id.get(target_id)
                        if target_u and target_u.symbol_kind == "class":
                            call_type = "INSTANTIATION"

                # Case B: Method Call with Receiver
                else:
                    call_type = "METHOD_CALL"

                    # 1. Receiver is 'self' or 'cls'
                    if call.receiver in ("self", "cls") and parent_class_id:
                        target_id = f"{parent_class_id}::{call.method}"

                    # 2. Receiver is a class field (self.ast_parser.parse())
                    elif call.receiver.startswith("self.") and parent_class_id:
                        attr_name = call.receiver.replace("self.", "").strip()
                        parent_attrs = class_attribute_types.get(parent_class_id, {})
                        if attr_name in parent_attrs:
                            var_class = parent_attrs[attr_name]
                            if var_class in import_scope:
                                target_id = f"{import_scope[var_class]}::{call.method}"
                            elif var_class in local_scope:
                                target_id = f"{local_scope[var_class]}::{call.method}"

                    # 3. Receiver is an imported module/class
                    elif call.receiver in import_scope:
                        target_id = f"{import_scope[call.receiver]}::{call.method}"

                    # 4. Receiver is a local class
                    elif call.receiver in local_scope:
                        target_id = f"{local_scope[call.receiver]}::{call.method}"

                    # 5. Receiver is a tracked local or global variable (includes type hints)
                    elif call.receiver in variable_types:
                        var_class = variable_types[call.receiver]
                        if var_class in import_scope:
                            target_id = f"{import_scope[var_class]}::{call.method}"
                        elif var_class in local_scope:
                            target_id = f"{local_scope[var_class]}::{call.method}"

                # VALIDATION CHECK: Method must exist in target class!
                if target_id and call_type == "METHOD_CALL":
                    if target_id not in unit_by_id:
                        # Method does not exist (e.g. unit.temp())
                        target_id = None

                # Assign Metadata
                if target_id:
                    call.target_unit_id = target_id
                    call.confidence = "HIGH"
                else:
                    call.target_unit_id = None
                    call.confidence = "LOW"

                call.call_type = call_type
                valid_calls.append(call)

            unit.metadata.calls = valid_calls
