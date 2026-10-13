from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from app.db.neo4j.neo4j_repository import CodebaseRepository
from app.db.neo4j.neo4j_client import neo4j_client


class GraphTools:

    def __init__(self, repository: CodebaseRepository):
        self.repository = repository

    # =========================================================
    # Generic neighbors
    # =========================================================

    def get_neighbors(
        self,
        node_id: str,
        relationship_types: Optional[List[str]] = None,
        direction: str = "outgoing",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Return neighboring nodes connected to the given node.

        The agent controls:
        - relationship types
        - direction
        - result limit

        This is the primary adaptive traversal primitive.
        """

        neighbors = self.repository.get_neighbors(
            node_id=node_id,
            relationship_types=relationship_types,
            direction=direction,
            limit=min(limit, 20),
        )

        return [
            {
                "node": self._serialize_node(item["node"]),
                "relationship": item["relationship"],
                "source_id": item["source_id"],
            }
            for item in neighbors
        ]

    # =========================================================
    # Find callers
    # =========================================================

    def find_callers(
        self,
        node_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Find functions/classes that call the specified node.
        """

        nodes = self.repository.find_callers(
            node_id=node_id,
            limit=min(limit, 20),
        )

        return [self._serialize_node(node) for node in nodes]

    # =========================================================
    # Find callees
    # =========================================================

    def find_callees(
        self,
        node_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Find functions/classes called by the specified node.
        """

        nodes = self.repository.find_callees(
            node_id=node_id,
            limit=min(limit, 20),
        )

        return [self._serialize_node(node) for node in nodes]

    # =========================================================
    # Find paths
    # =========================================================

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        relationship_types: Optional[List[str]] = None,
        max_depth: int = 5,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Find candidate graph paths between two known nodes.

        This is useful when both endpoints are already known and
        the agent wants to understand how they are connected.
        """

        max_depth = min(max_depth, 8)
        limit = min(limit, 10)

        paths = self.repository.find_paths(
            source_id=source_id,
            target_id=target_id,
            relationship_types=relationship_types,
            max_depth=max_depth,
            limit=limit,
        )

        return [
            {
                "path": [self._serialize_node(node) for node in path],
                "length": len(path) - 1,
            }
            for path in paths
        ]

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

    def trace_execution_flow(
        self,
        source_symbol: str,
        candidate_target_symbols: List[str],
        max_depth: int = 6,
    ) -> List[Dict[str, Any]]:
        """
        Finds verified execution call paths from a starting symbol to any reachable
        candidate target symbols up to max_depth.
        Filters out any target symbols that have no valid topological call chain from the source.
        """
        bounded_depth = min(max(1, max_depth), 8)

        cypher = f"""
        MATCH (start:CodeUnit)
        WHERE start.id = $source_symbol 
        OR start.qualified_name = $source_symbol 
        OR start.symbol_name = $source_symbol
        WITH start LIMIT 1

        MATCH (target:CodeUnit)
        WHERE (target.id IN $target_symbols 
            OR target.qualified_name IN $target_symbols 
            OR target.symbol_name IN $target_symbols)
        AND start <> target

        MATCH path = shortestPath((start)-[:CALLS*1..{bounded_depth}]->(target))
        RETURN 
            target.qualified_name AS target_name,
            target.file_path AS target_file,
            [n IN nodes(path) | n.qualified_name] AS call_chain,
            length(path) AS depth
        ORDER BY depth ASC
        LIMIT 3
        """

        results = neo4j_client.execute_query(
            cypher,
            {
                "source_symbol": source_symbol,
                "target_symbols": candidate_target_symbols,
            },
        )

        return [
            {
                "target": r["target_name"],
                "file": r["target_file"],
                "call_chain": " -> ".join(r["call_chain"]),
                "depth": r["depth"],
            }
            for r in results
        ]


def build_graph_tools(
    repository: CodebaseRepository,
):
    """
    Creates LangChain tools for graph traversal.
    """

    service = GraphTools(repository)

    return [
        tool(
            "get_neighbors",
            description=(
                "Explore nodes connected to a code node. "
                "Use relationship types and direction to perform "
                "targeted graph traversal. This is the main tool "
                "for investigating code relationships."
            ),
        )(service.get_neighbors),
        tool(
            "find_callers",
            description=(
                "Find code units that call the specified node. "
                "Use for questions such as 'who calls this function?'"
            ),
        )(service.find_callers),
        tool(
            "find_callees",
            description=(
                "Find code units called by the specified node. "
                "Use for questions such as 'what does this function call?'"
            ),
        )(service.find_callees),
        tool(
            "find_paths",
            description=(
                "Find candidate paths between two known nodes. "
                "Use when both endpoints are known and the agent "
                "needs to understand how they are connected."
            ),
        )(service.find_paths),
        tool(
            "trace_execution_flow",
            description=(
                "Find verified execution call paths from a starting symbol to any reachable "
                "candidate target symbols up to max_depth. Filters out any target symbols that "
                "have no valid topological call chain from the source."
            ),
        )(service.trace_execution_flow),
    ]
