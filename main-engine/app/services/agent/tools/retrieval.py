from typing import Any, Dict, List

from langchain_core.tools import tool

from app.db.neo4j.neo4j_repository import CodebaseRepository
from app.services.agent.retrival.hybrid_search import HybridCodeSearch


class RetrievalTools:
    """
    Agent-facing retrieval tools.

    These wrap deterministic repository operations.
    """

    def __init__(self, repository: CodebaseRepository):
        self.repository = repository
        self.search_engine = HybridCodeSearch(repository)

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

    def get_symbol(
        self,
        symbol: str,
    ) -> List[Dict[str, Any]]:
        """
        Find a symbol by:
        - qualified_name
        - symbol_name
        - node id
        """

        nodes = self.repository.get_symbol(symbol)

        return [self._serialize_node(node) for node in nodes]

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
            service.search_codebase,
            name="search_codebase",
            description=(
                "Search the codebase using semantic and keyword retrieval. "
                "Use this when the question describes behavior, functionality, "
                "or concepts rather than an exact symbol or file."
            ),
        ),
        tool(
            service.get_symbol,
            name="get_symbol",
            description=(
                "Find an exact code symbol by qualified name, symbol name, "
                "or node id. Prefer this tool when the user explicitly mentions a known symbol."
            ),
        ),
        tool(
            service.get_file,
            name="get_file",
            description=(
                "Find all code units contained in a repository file. "
                "Use when the user mentions a specific file or module path."
            ),
        ),
    ]
