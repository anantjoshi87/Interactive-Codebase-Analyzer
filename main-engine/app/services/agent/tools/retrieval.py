from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from app.db.neo4j.neo4j_repository import CodebaseRepository
from app.services.agent.retrival.hybrid_search import HybridCodeSearch
from app.services.agent.retrival.symbol_resolver import SymbolResolver


class RetrievalTools:
    """
    Agent-facing retrieval tools.

    These wrap deterministic repository operations.
    """

    def __init__(self, repository: CodebaseRepository):
        self.repository = repository
        self.search_engine = HybridCodeSearch(repository)
        self._resolver: Optional[SymbolResolver] = None

    # =========================================================
    # Semantic / keyword search
    # =========================================================

    async def search_codebase(
        self,
        query: str,
        top_k: int = 8,
    ) -> List[Dict[str, Any]]:
        """
        Search the repository using semantic + keyword retrieval.

        NOTE:
        This is the interface the agent sees.

        The actual hybrid retrieval implementation can later combine:
        - Neo4j vector search
        - full-text search
        - exact matches
        - reranking

        For now this method can be wired to your vector index.
        """

        top_k = min(max(top_k, 1), 20)

        return await self.search_engine.search(
            query=query,
            top_k=top_k,
        )

    # =========================================================
    # Exact symbol lookup
    # =========================================================

    def _get_resolver(self) -> SymbolResolver:
        """Lazy loads the in-memory symbol cache once."""
        if self._resolver is None:
            symbols = self.repository.get_all_symbol_names()
            self._resolver = SymbolResolver(symbols)
        return self._resolver

    def get_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Retrieves a symbol from Neo4j, transparently auto-correcting
        typos, casing, and spacing before querying.
        """
        resolver = self._get_resolver()

        # 1. Resolve typos / casing / 'class ' prefix
        corrected_symbol, match = resolver.resolve(symbol)

        # 2. Query Neo4j with the corrected identifier
        results = self.repository.get_symbol(corrected_symbol)

        # 3. If still empty and input contained dots (e.g. UserService.register), try leaf
        if not results and "." in corrected_symbol:
            leaf = corrected_symbol.split(".")[-1]
            results = self.repository.get_symbol(leaf)

        return results

    # =========================================================
    # File lookup
    # =========================================================

    def get_file(
        self,
        file_path: str,
    ) -> List[Dict[str, Any]]:
        """
        Return all code units contained in a file.
        """

        nodes = self.repository.get_file(file_path)

        return [self._serialize_node(node) for node in nodes]

    # =========================================================
    # Serialization
    # =========================================================

    @staticmethod
    def _serialize_node(
        node: Dict[str, Any],
    ) -> Dict[str, Any]:

        return {
            "id": node.get("id"),
            "qualified_name": node.get("qualified_name"),
            "symbol_name": node.get("symbol_name"),
            "file_path": node.get("file_path"),
            "symbol_kind": node.get("symbol_kind"),
            "summary": node.get("summary"),
            "start_line": node.get("start_line"),
            "end_line": node.get("end_line"),
        }


def build_retrieval_tools(
    repository: CodebaseRepository,
):
    """
    Creates LangChain tools bound to the repository.
    """
    service = RetrievalTools(repository)

    return [
        tool(
            "search_codebase",
            description=(
                "Search the codebase using semantic and keyword retrieval. "
                "Use this when the question describes behavior, functionality, "
                "or concepts rather than an exact symbol or file."
            ),
        )(service.search_codebase),
        tool(
            "get_symbol",
            description=(
                "Find an exact code symbol by qualified name, symbol name, "
                "or node id. Prefer this tool when the user explicitly mentions a known symbol."
            ),
        )(service.get_symbol),
        tool(
            "get_file",
            description=(
                "Find all code units contained in a repository file. "
                "Use when the user mentions a specific file or module path."
            ),
        )(service.get_file),
    ]
