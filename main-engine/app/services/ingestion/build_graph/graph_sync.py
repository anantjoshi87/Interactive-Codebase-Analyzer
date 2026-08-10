import json
import logging
from typing import List, Dict, Any
from app.db.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)


class GraphSync:
    """
    Handles the batched ingestion of enriched CodeUnit payloads into Neo4j
    using high-performance Cypher UNWIND queries.
    """

    @staticmethod
    def _prepare_payloads(payloads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepares the payloads for Neo4j. Serializes the 'globals' array
        into a JSON string so it can be stored as a scalar node property.
        """
        prepared = []
        for payload in payloads:
            p = payload.copy()

            # Convert globals list to JSON string
            if "globals" in p and isinstance(p["globals"], list):
                p["globals_json"] = json.dumps(p["globals"])
            else:
                p["globals_json"] = "[]"

            # Ensure safe empty lists for relationship loops to prevent Cypher UNWIND errors
            p["calls"] = p.get("calls") or []
            p["imports"] = p.get("imports") or []
            p["inheritance"] = p.get("inheritance") or []
            p["overrides"] = p.get("overrides") or []

            prepared.append(p)
        return prepared

    def sync_batch(self, payloads: List[Dict[str, Any]]):
        """
        Executes the two-pass batch insertion for a chunk of CodeUnits.
        """
        if not payloads:
            return

        prepared_batch = self._prepare_payloads(payloads)

        try:
            # Pass 1: Upsert all nodes
            self._sync_nodes(prepared_batch)

            # Pass 2: Draw all relationships (Edges)
            self._sync_relationships(prepared_batch)

            logger.info(
                f"✓ Successfully synced batch of {len(prepared_batch)} CodeUnits to Neo4j."
            )
        except Exception as e:
            logger.error(f"Failed to sync batch to Neo4j: {e}", exc_info=True)
            raise

    def _sync_nodes(self, batch: List[Dict[str, Any]]):
        """
        Pass 1: MERGE all CodeUnit nodes and SET their scalar properties.
        """
        query = """
        UNWIND $batch AS unit
        
        // MERGE matches exactly on the unique ID
        MERGE (n:CodeUnit {id: unit.id})
        
        // SET all metadata properties from your payload
        SET n.unit_type = unit.unit_type,
            n.file_path = unit.file_path,
            n.symbol_name = unit.symbol_name,
            n.symbol_kind = unit.symbol_kind,
            n.ast_node_type = unit.ast_node_type,
            n.start_line = unit.start_line,
            n.end_line = unit.end_line,
            n.summary = unit.summary,
            n.embedding = unit.embedding,
            n.globals = unit.globals_json
        """
        neo4j_client.execute_query(query, {"batch": batch})

    def _sync_relationships(self, batch: List[Dict[str, Any]]):
        """
        Pass 2: Draw CONTAINS, CALLS, IMPORTS, INHERITS, and OVERRIDES edges.
        """

        # 1. CONTAINS Relationships (Parent-Child Hierarchy)
        contains_query = """
        UNWIND $batch AS unit
        WITH unit WHERE unit.parent_symbol_id IS NOT NULL AND unit.parent_symbol_id <> ""
        MATCH (child:CodeUnit {id: unit.id})
        MATCH (parent:CodeUnit {id: unit.parent_symbol_id})
        MERGE (parent)-[:CONTAINS]->(child)
        """
        neo4j_client.execute_query(contains_query, {"batch": batch})

        # 2. CALLS Relationships
        calls_query = """
        UNWIND $batch AS unit
        UNWIND unit.calls AS call
        MATCH (caller:CodeUnit {id: unit.id})
        MATCH (callee:CodeUnit {id: call.target_id})
        // MERGE without properties ensures only ONE line is drawn per function pair
        MERGE (caller)-[:CALLS]->(callee)
        """
        neo4j_client.execute_query(calls_query, {"batch": batch})

        # 3. IMPORTS Relationships
        imports_query = """
        UNWIND $batch AS unit
        UNWIND unit.imports AS imp
        MATCH (importer:CodeUnit {id: unit.id})
        MATCH (imported:CodeUnit {id: imp.target_id})
        MERGE (importer)-[:IMPORTS]->(imported)
        """
        neo4j_client.execute_query(imports_query, {"batch": batch})

        # 4. INHERITS Relationships (Class to Class)
        inherits_query = """
        UNWIND $batch AS unit
        UNWIND unit.inheritance AS base_id
        MATCH (child_class:CodeUnit {id: unit.id})
        MATCH (parent_class:CodeUnit {id: base_id})
        MERGE (child_class)-[:INHERITS]->(parent_class)
        """
        neo4j_client.execute_query(inherits_query, {"batch": batch})

        # 5. OVERRIDES Relationships (Method to Method)
        overrides_query = """
        UNWIND $batch AS unit
        UNWIND unit.overrides AS override_id
        MATCH (child_method:CodeUnit {id: unit.id})
        MATCH (parent_method:CodeUnit {id: override_id})
        MERGE (child_method)-[:OVERRIDES]->(parent_method)
        """
        neo4j_client.execute_query(overrides_query, {"batch": batch})
