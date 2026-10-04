from pathlib import Path
from typing import List, Dict, Optional, Tuple
from app.services.ingestion.models import CodeUnit


class RepoResolver:
    """
    Binds SCIP semantic resolution indices to Tree-sitter CodeUnits.
    Resolves CallReferences, ImportReferences, and establishes cross-unit links.
    """

    def __init__(self, scip_index_path: str | Path):
        self.scip_index_path = Path(scip_index_path)

    @staticmethod
    def _parse_scip_range(r: list[int]) -> Tuple[int, int, int, int]:
        """
        Normalizes SCIP range format to (start_line, start_col, end_line, end_col).
        SCIP format:
          - 3 elements: [line, start_col, end_col]
          - 4 elements: [start_line, start_col, end_line, end_col]
        """
        if len(r) == 3:
            return r[0], r[1], r[0], r[2]
        return r[0], r[1], r[2], r[3]

    def resolve(self, units: List[CodeUnit]) -> List[CodeUnit]:
        if not self.scip_index_path.exists():
            print(f"[RepoResolver] Index file not found at {self.scip_index_path}")
            return units

        from app.services.ingestion.proto import scip_pb2

        index = scip_pb2.Index()
        with open(self.scip_index_path, "rb") as f:
            index.ParseFromString(f.read())

        # 1. Map files to their CodeUnits for fast lookup
        units_by_file: Dict[str, List[CodeUnit]] = {}
        for unit in units:
            norm_path = Path(unit.file_path).as_posix().lstrip("./")
            units_by_file.setdefault(norm_path, []).append(unit)

        # 2. Pass 1: Map SCIP symbol strings to target CodeUnit IDs
        scip_symbol_to_unit_id: Dict[str, str] = {}

        for doc in index.documents:
            matched_file = self._find_matching_file(doc.relative_path, units_by_file)
            if not matched_file:
                continue

            file_units = units_by_file[matched_file]

            for occ in doc.occurrences:
                # Role 1 is Definition
                if occ.symbol_roles & 1:
                    s_line, s_col, e_line, e_col = self._parse_scip_range(
                        list(occ.range)
                    )

                    enclosing_unit = self._find_innermost_unit(
                        file_units, s_line, s_col
                    )
                    if enclosing_unit:
                        scip_symbol_to_unit_id[occ.symbol] = enclosing_unit.id

        # 3. Pass 2: Resolve references (calls and imports)
        for doc in index.documents:
            matched_file = self._find_matching_file(doc.relative_path, units_by_file)
            if not matched_file:
                continue

            file_units = units_by_file[matched_file]

            for occ in doc.occurrences:
                # Role 8 is Read / Reference
                if occ.symbol_roles & 8:
                    s_line, s_col, e_line, e_col = self._parse_scip_range(
                        list(occ.range)
                    )
                    target_unit_id = scip_symbol_to_unit_id.get(occ.symbol)

                    caller_unit = self._find_innermost_unit(file_units, s_line, s_col)
                    if not caller_unit:
                        continue

                    # Match CallReferences
                    is_callable_sym = "()." in occ.symbol or occ.symbol.endswith("#")

                    for call in caller_unit.metadata.calls:
                        if call.line == s_line and call.column is not None:
                            # Verify call column matches within token span
                            if s_col <= call.column <= e_col or call.column == s_col:
                                if (
                                    call.resolution_status == "UNRESOLVED"
                                    or is_callable_sym
                                ):
                                    if target_unit_id:
                                        call.target_symbol_id = target_unit_id
                                        call.resolution_status = "RESOLVED"
                                    else:
                                        call.target_symbol_id = occ.symbol
                                        call.resolution_status = "EXTERNAL"
                                    call.resolver = "scip-python"
                                    break  # Matched this call, don't reassign

                    # Match ImportReferences
                    for imp in caller_unit.metadata.imports:
                        if imp.line == s_line:
                            if imp.imported_name and imp.imported_name in occ.symbol:
                                imp.target_unit_id = target_unit_id or occ.symbol

        return units

    @staticmethod
    def _find_matching_file(
        scip_rel_path: str, units_by_file: Dict[str, List[CodeUnit]]
    ) -> Optional[str]:
        scip_p = Path(scip_rel_path).as_posix().lstrip("./")

        for indexed_file in units_by_file.keys():
            idx_p = Path(indexed_file).as_posix().lstrip("./")
            if (
                idx_p == scip_p
                or idx_p.endswith(f"/{scip_p}")
                or scip_p.endswith(f"/{idx_p}")
            ):
                return indexed_file

        return None

    @staticmethod
    def _find_innermost_unit(
        units: List[CodeUnit], line: int, col: int
    ) -> Optional[CodeUnit]:
        """Finds the smallest AST node enclosing (line, col) by byte-span."""
        candidates = []
        for u in units:
            # Check line bounds
            if u.start_line <= line <= u.end_line:
                # If on boundary lines, ensure col doesn't fall outside
                if u.start_line == line and col < u.start_col:
                    continue
                if u.end_line == line and col > u.end_col:
                    continue
                candidates.append(u)

        if not candidates:
            return None

        # Sort by smallest byte-span (most localized unit), preferring non-modules
        candidates.sort(
            key=lambda u: (
                0 if u.symbol_kind != "module" else 1,
                (u.end_byte - u.start_byte),
            )
        )
        return candidates[0]
