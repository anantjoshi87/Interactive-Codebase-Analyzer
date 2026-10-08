# RepoResolver (binds CodeUnits to targets)

from pathlib import Path
from typing import Dict, List, Optional
from app.schemas import CodeUnit
from app.services.ingestion.resolution import ScipIndexReader


class RepoResolver:
    """
    Binds SCIP semantic resolution indices to Tree-sitter CodeUnits.
    Resolves CallReferences, ImportReferences, and establishes cross-unit links.
    """

    def __init__(self, scip_index_path: str | Path):
        self.reader = ScipIndexReader(scip_index_path)

    def resolve(self, units: List[CodeUnit]) -> List[CodeUnit]:
        if not self.reader.exists():
            print(f"[RepoResolver] Index file not found at {self.reader.index_path}")
            return units

        # 1. Map files to their CodeUnits for fast lookup
        units_by_file: Dict[str, List[CodeUnit]] = {}
        for unit in units:
            norm_path = Path(unit.file_path).as_posix().lstrip("./")
            units_by_file.setdefault(norm_path, []).append(unit)

        # 2. Pass 1: Map SCIP symbol strings to target CodeUnit IDs
        scip_symbol_to_unit_id: Dict[str, str] = {}
        documents = list(self.reader.iter_documents())

        for doc in documents:
            matched_file = self._find_matching_file(doc.relative_path, units_by_file)
            if not matched_file:
                continue

            file_units = units_by_file[matched_file]

            for occ in doc.occurrences:
                if occ.is_definition:
                    enclosing_unit = self._find_innermost_unit(
                        file_units, occ.start_line, occ.start_col
                    )
                    if enclosing_unit:
                        scip_symbol_to_unit_id[occ.symbol] = enclosing_unit.id

        # 3. Pass 2: Resolve references (calls and imports)
        for doc in documents:
            matched_file = self._find_matching_file(doc.relative_path, units_by_file)
            if not matched_file:
                continue

            file_units = units_by_file[matched_file]

            for occ in doc.occurrences:
                if not occ.is_reference:
                    continue

                target_unit_id = scip_symbol_to_unit_id.get(occ.symbol)
                caller_unit = self._find_innermost_unit(
                    file_units, occ.start_line, occ.start_col
                )
                if not caller_unit:
                    continue

                # Match CallReferences
                for call in caller_unit.metadata.calls:
                    if call.line == occ.start_line and call.column is not None:
                        if (
                            occ.start_col <= call.column <= occ.end_col
                            or call.column == occ.start_col
                        ):
                            if (
                                call.resolution_status == "UNRESOLVED"
                                or occ.is_callable_symbol
                            ):
                                if target_unit_id:
                                    call.target_symbol_id = target_unit_id
                                    call.resolution_status = "RESOLVED"
                                else:
                                    call.target_symbol_id = occ.symbol
                                    call.resolution_status = "EXTERNAL"
                                call.resolver = "scip-python"
                                break

                # Match ImportReferences
                for imp in caller_unit.metadata.imports:
                    if imp.line == occ.start_line:
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
            if u.start_line <= line <= u.end_line:
                if u.start_line == line and col < u.start_col:
                    continue
                if u.end_line == line and col > u.end_col:
                    continue
                candidates.append(u)

        if not candidates:
            return None

        candidates.sort(
            key=lambda u: (
                0 if u.symbol_kind != "module" else 1,
                (u.end_byte - u.start_byte),
            )
        )
        return candidates[0]
