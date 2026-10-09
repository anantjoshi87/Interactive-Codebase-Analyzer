from typing import Any, Dict, List, Optional

from app.db.neo4j.neo4j_client import Neo4jClient


class CodebaseRepository:
    """
    Repository containing Neo4j queries required by the
    Codebase Understanding Agent.

    This class does not manage Neo4j connections.
    Neo4jClient handles that responsibility.
    """

    def __init__(self, client: Neo4jClient):
        self.client = client

    # =========================================================
    # Vector search
    # =========================================================

    def vector_search(
        self,
        embedding: List[float],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:

        query = """
        CALL db.index.vector.queryNodes(
            'codeunit_embedding',
            $top_k,
            $embedding
        )
        YIELD node, score

        RETURN
            node,
            score

        ORDER BY score DESC
        """

        return self.client.execute_query(
            query,
            {
                "embedding": embedding,
                "top_k": top_k,
            },
        )

    # =========================================================
    # Full-text search
    # =========================================================

    def keyword_search(
        self,
        query_text: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:

        query = """
        CALL db.index.fulltext.queryNodes(
            'codeunit_fulltext',
            $query
        )
        YIELD node, score

        RETURN
            node,
            score

        ORDER BY score DESC
        LIMIT $top_k
        """

        return self.client.execute_query(
            query,
            {
                "query": query_text,
                "top_k": top_k,
            },
        )

    # =========================================================
    # Generic node lookup
    # =========================================================

    def get_node_by_id(
        self,
        node_id: str,
    ) -> Optional[Dict[str, Any]]:

        query = """
        MATCH (n {id: $node_id})
        RETURN n
        LIMIT 1
        """

        results = self.client.execute_query(
            query,
            {"node_id": node_id},
        )

        if not results:
            return None

        return dict(results[0]["n"])

    # =========================================================
    # Exact symbol lookup
    # =========================================================

    def get_symbol(
        self,
        symbol: str,
    ) -> List[Dict[str, Any]]:

        query = """
        MATCH (n)
        WHERE
            n.qualified_name = $symbol
            OR n.symbol_name = $symbol
            OR n.id = $symbol

        RETURN n

        ORDER BY
            CASE
                WHEN n.qualified_name = $symbol THEN 0
                WHEN n.symbol_name = $symbol THEN 1
                WHEN n.id = $symbol THEN 2
                ELSE 3
            END
        """

        results = self.client.execute_query(
            query,
            {"symbol": symbol},
        )

        return [dict(record["n"]) for record in results]

    # =========================================================
    # File lookup
    # =========================================================

    def get_file(
        self,
        file_path: str,
    ) -> List[Dict[str, Any]]:

        query = """
        MATCH (n)
        WHERE n.file_path = $file_path

        RETURN n
        ORDER BY coalesce(n.start_line, 0)
        """

        results = self.client.execute_query(
            query,
            {"file_path": file_path},
        )

        return [dict(record["n"]) for record in results]

    # =========================================================
    # Neighbors
    # =========================================================

    def get_neighbors(
        self,
        node_id: str,
        relationship_types: Optional[List[str]] = None,
        direction: str = "outgoing",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        if direction not in {"outgoing", "incoming", "both"}:
            raise ValueError("direction must be one of: outgoing, incoming, both")

        rel_filter = self._build_relationship_pattern(relationship_types)
        # Ensure 'r' is always bound so type(r) works!
        rel_decl = f"r{rel_filter}"

        if direction == "outgoing":
            pattern = f"-[{rel_decl}]->"
        elif direction == "incoming":
            pattern = f"<-[{rel_decl}]-"
        else:
            pattern = f"-[{rel_decl}]-"

        query = f"""
        MATCH (source {{id: $node_id}}){pattern}(target)
        RETURN
            target,
            type(r) AS relationship,
            source.id AS source_id
        LIMIT $limit
        """

        results = self.client.execute_query(
            query,
            {
                "node_id": node_id,
                "limit": limit,
            },
        )

        return [
            {
                "node": dict(record["target"]),
                "relationship": record["relationship"],
                "source_id": record["source_id"],
            }
            for record in results
        ]

    # =========================================================
    # Callers
    # =========================================================

    def find_callers(
        self,
        node_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:

        query = """
        MATCH (caller)-[:CALLS]->(target {id: $node_id})
        RETURN caller
        LIMIT $limit
        """

        results = self.client.execute_query(
            query,
            {
                "node_id": node_id,
                "limit": limit,
            },
        )

        return [dict(record["caller"]) for record in results]

    # =========================================================
    # Callees
    # =========================================================

    def find_callees(
        self,
        node_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:

        query = """
        MATCH (caller {id: $node_id})-[:CALLS]->(callee)
        RETURN callee
        LIMIT $limit
        """

        results = self.client.execute_query(
            query,
            {
                "node_id": node_id,
                "limit": limit,
            },
        )

        return [dict(record["callee"]) for record in results]

    # =========================================================
    # Paths
    # =========================================================

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        relationship_types: Optional[List[str]] = None,
        max_depth: int = 5,
        limit: int = 5,
    ) -> List[List[Dict[str, Any]]]:

        max_depth = min(max_depth, 8)

        relationship_pattern = self._build_relationship_pattern(relationship_types)

        query = f"""
        MATCH path =
            (source {{id: $source_id}})
            -[{relationship_pattern}*1..{max_depth}]->
            (target {{id: $target_id}})

        RETURN path
        LIMIT $limit
        """

        results = self.client.execute_query(
            query,
            {
                "source_id": source_id,
                "target_id": target_id,
                "limit": limit,
            },
        )

        paths = []

        for record in results:
            path = record["path"]

            paths.append([dict(node) for node in path.nodes])

        return paths

    # =========================================================
    # Relationship validation
    # =========================================================

    @staticmethod
    def _build_relationship_pattern(
        relationship_types: Optional[List[str]],
    ) -> str:

        if not relationship_types:
            return ""

        allowed = {
            "CALLS",
            "IMPORTS",
            "INHERITS",
            "CONTAINS",
        }

        invalid = set(relationship_types) - allowed

        if invalid:
            raise ValueError(f"Unsupported relationship types: {invalid}")

        return ":" + "|".join(relationship_types)
