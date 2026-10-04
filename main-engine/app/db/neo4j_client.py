# app/db/neo4j_client.py
from typing import Any, Dict, List, Optional
from langchain_neo4j import Neo4jGraph
from app.core.config import settings


class Neo4jClient:
    """
    A singleton wrapper around LangChain's Neo4jGraph to manage database
    connections and execute Cypher queries.
    """

    def __init__(self):
        self._graph: Optional[Neo4jGraph] = None

    def get_graph(self) -> Neo4jGraph:
        if self._graph is None:
            self._graph = Neo4jGraph(
                url=settings.NEO4J_URI,
                username=settings.NEO4J_USERNAME,
                password=settings.NEO4J_PASSWORD,
            )
        return self._graph

    def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        graph = self.get_graph()
        return graph.query(query, params=parameters or {})

    def close(self):
        if self._graph and getattr(self._graph, "_driver", None):
            self._graph._driver.close()
            self._graph = None

    def init_schema(self):
        """Initializes unique constraints and lookup indexes."""
        schema_queries = [
            # 1. Unique Constraints (Automatic Backing Indexes)
            "CREATE CONSTRAINT unique_code_unit IF NOT EXISTS FOR (c:CodeUnit) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT unique_config_unit IF NOT EXISTS FOR (c:ConfigUnit) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT unique_doc_unit IF NOT EXISTS FOR (d:DocumentUnit) REQUIRE d.id IS UNIQUE",
            # 2. Lookup Indexes
            "CREATE INDEX codeunit_symbol_name IF NOT EXISTS FOR (c:CodeUnit) ON (c.symbol_name)",
            "CREATE INDEX codeunit_file_path IF NOT EXISTS FOR (c:CodeUnit) ON (c.file_path)",
            "CREATE INDEX codeunit_symbol_kind IF NOT EXISTS FOR (c:CodeUnit) ON (c.symbol_kind)",
            "CREATE INDEX code_unit_lookup IF NOT EXISTS FOR (c:CodeUnit) ON (c.file_path, c.symbol_name)",
        ]

        for query in schema_queries:
            self.execute_query(query)

        print("✓ Neo4j constraints and structural indexes initialized successfully.")


# Global singleton instance
neo4j_client = Neo4jClient()
