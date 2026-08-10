# app/db/neo4j_client.py
from typing import Any, Dict, List, Optional
from langchain_neo4j import Neo4jGraph
from app.core.config import Settings


class Neo4jClient:
    """
    A singleton wrapper around LangChain's Neo4jGraph to manage database
    connections and execute Cypher queries.
    """

    def __init__(self):
        self._graph: Optional[Neo4jGraph] = None

    def get_graph(self) -> Neo4jGraph:
        """
        Initializes and returns the LangChain Neo4jGraph instance.
        Connection pooling is handled automatically under the hood.
        """
        if self._graph is None:
            self._graph = Neo4jGraph(
                url=Settings.NEO4J_URI,
                username=Settings.NEO4J_USERNAME,
                password=Settings.NEO4J_PASSWORD,
            )
        return self._graph

    def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes a raw Cypher query using the underlying graph instance.
        Perfect for batched ingestion via UNWIND.
        """
        graph = self.get_graph()
        return graph.query(query, params=parameters or {})

    def close(self):
        """Gracefully close the underlying Neo4j driver connection."""
        if self._graph and getattr(self._graph, "_driver", None):
            self._graph._driver.close()
            self._graph = None

    def init_schema(self):
        """
        Initializes constraints and structural indexes in Neo4j.
        (Vector indexes will be handled separately by LangChain's Neo4jVector).
        """
        graph = self.get_graph()

        schema_queries = [
            # 1. Makes MERGE during batch ingestion $O(1)$ fast; prevents duplicate nodes.
            """
            CREATE CONSTRAINT codeunit_id_unique IF NOT EXISTS
            FOR (c:CodeUnit) REQUIRE c.id IS UNIQUE;
            """,
            # 2. Instant lookup when user/LLM searches for a specific function name.
            """
            CREATE INDEX codeunit_symbol_name IF NOT EXISTS
            FOR (c:CodeUnit) ON (c.symbol_name);
            """,
            # 3. Fast filtering to retrieve all code blocks sitting inside a single file.
            """
            CREATE INDEX codeunit_file_path IF NOT EXISTS
            FOR (c:CodeUnit) ON (c.file_path);
            """,
            # 4. Quick categorization between function, class, method, and import.
            """
            CREATE INDEX codeunit_symbol_kind IF NOT EXISTS
            FOR (c:CodeUnit) ON (c.symbol_kind);
            """,
        ]

        for query in schema_queries:
            self.execute_query(query)

        print("✓ Neo4j constraints and structural indexes initialized successfully.")


# Global singleton instance to be imported across the application
neo4j_client = Neo4jClient()
