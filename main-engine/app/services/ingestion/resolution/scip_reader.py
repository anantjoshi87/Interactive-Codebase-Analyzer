# Low-level SCIP protobuf reader 

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional, Tuple


@dataclass(slots=True)
class ScipOccurrence:
    symbol: str
    symbol_roles: int
    start_line: int
    start_col: int
    end_line: int
    end_col: int

    @property
    def is_definition(self) -> bool:
        return bool(self.symbol_roles & 1)

    @property
    def is_reference(self) -> bool:
        return bool(self.symbol_roles & 8)

    @property
    def is_callable_symbol(self) -> bool:
        return "()." in self.symbol or self.symbol.endswith("#")


@dataclass(slots=True)
class ScipDocument:
    relative_path: str
    occurrences: List[ScipOccurrence]


class ScipIndexReader:
    """Handles deserialization and parsing of SCIP index protobuf binaries."""

    def __init__(self, index_path: str | Path):
        self.index_path = Path(index_path)

    @staticmethod
    def parse_scip_range(r: list[int]) -> Tuple[int, int, int, int]:
        """Normalizes SCIP range format to (start_line, start_col, end_line, end_col)."""
        if len(r) == 3:
            return r[0], r[1], r[0], r[2]
        return r[0], r[1], r[2], r[3]

    def exists(self) -> bool:
        return self.index_path.exists()

    def iter_documents(self) -> Iterator[ScipDocument]:
        """Loads and yields parsed documents from the SCIP protobuf index."""
        if not self.exists():
            return

        from app.services.ingestion.resolution.proto import scip_pb2

        index = scip_pb2.Index()
        with open(self.index_path, "rb") as f:
            index.ParseFromString(f.read())

        for doc in index.documents:
            occurrences: List[ScipOccurrence] = []
            for occ in doc.occurrences:
                s_line, s_col, e_line, e_col = self.parse_scip_range(list(occ.range))
                occurrences.append(
                    ScipOccurrence(
                        symbol=occ.symbol,
                        symbol_roles=occ.symbol_roles,
                        start_line=s_line,
                        start_col=s_col,
                        end_line=e_line,
                        end_col=e_col,
                    )
                )

            yield ScipDocument(
                relative_path=doc.relative_path,
                occurrences=occurrences,
            )
