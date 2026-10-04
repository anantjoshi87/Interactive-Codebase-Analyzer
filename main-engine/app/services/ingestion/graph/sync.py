# Neo4j Cypher batch ingestion (GraphSync)

import json
import logging
from typing import List, Dict, Any
from app.db.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)


class GraphSync:
    """
    Batched ingestion of enriched Units (Code, Config, Document) into Neo4j
    using high-performance Cypher UNWIND queries.
    """

    @staticmethod
    def _prepare_payloads(
        payloads: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        categorized = {
            "code": [],
            "config": [],
            "document": [],
        }

        for payload in payloads:
            p = payload.copy()
            u_type = p.get("unit_type", "code")

            if u_type == "code":
                if "globals" in p and isinstance(p["globals"], list):
                    p["globals_json"] = json.dumps(p["globals"])
                else:
                    p["globals_json"] = "[]"

                p["calls"] = p.get("calls") or []
                p["imports"] = p.get("imports") or []
                p["raw_inheritance"] = p.get("raw_inheritance") or []
                p["overrides"] = p.get("overrides") or []
                categorized["code"].append(p)

            elif u_type == "config":
                p["metadata_json"] = json.dumps(p.get("metadata", {}))
                categorized["config"].append(p)

            elif u_type == "document":
                categorized["document"].append(p)

        return categorized

    def sync_batch(self, payloads: List[Dict[str, Any]]):
        if not payloads:
            return

        prepared = self._prepare_payloads(payloads)

        try:
            # 1. Upsert nodes
            if prepared["code"]:
                self._sync_code_nodes(prepared["code"])
            if prepared["config"]:
                self._sync_config_nodes(prepared["config"])
            if prepared["document"]:
                self._sync_document_nodes(prepared["document"])

            # 2. Wire relationships
            if prepared["code"]:
                self._sync_relationships(prepared["code"])

            logger.info("✓ Successfully synced units to Neo4j.")
        except Exception as e:
            logger.error(f"Failed to sync batch to Neo4j: {e}", exc_info=True)
            raise

    def _sync_code_nodes(self, batch: List[Dict[str, Any]]):
        query = """
        UNWIND $batch AS unit
        MERGE (n:CodeUnit:Unit {id: unit.id})
        SET n.unit_type = unit.unit_type,
            n.file_path = unit.file_path,
            n.symbol_name = unit.symbol_name,
            n.qualified_name = unit.qualified_name,
            n.symbol_kind = unit.symbol_kind,
            n.ast_node_type = unit.ast_node_type,
            n.start_line = unit.start_line,
            n.end_line = unit.end_line,
            n.summary = unit.summary,
            n.embedding = unit.embedding,
            n.globals = unit.globals_json
        """
        neo4j_client.execute_query(query, {"batch": batch})

    def _sync_config_nodes(self, batch: List[Dict[str, Any]]):
        query = """
        UNWIND $batch AS unit
        MERGE (n:ConfigUnit:Unit {id: unit.id})
        SET n.unit_type = unit.unit_type,
            n.file_path = unit.file_path,
            n.config_type = unit.config_type,
            n.summary = unit.summary,
            n.embedding = unit.embedding,
            n.metadata = unit.metadata_json
        """
        neo4j_client.execute_query(query, {"batch": batch})

    def _sync_document_nodes(self, batch: List[Dict[str, Any]]):
        query = """
        UNWIND $batch AS unit
        MERGE (n:DocumentUnit:Unit {id: unit.id})
        SET n.unit_type = unit.unit_type,
            n.file_path = unit.file_path,
            n.document_type = unit.document_type,
            n.title = unit.title,
            n.summary = unit.summary,
            n.embedding = unit.embedding
        """
        neo4j_client.execute_query(query, {"batch": batch})

    def _sync_relationships(self, batch: List[Dict[str, Any]]):
        # 1. CONTAINS (Structural AST hierarchy)
        contains_query = """
        UNWIND $batch AS unit
        WITH unit WHERE unit.parent_symbol_id IS NOT NULL AND unit.parent_symbol_id <> ""
        MATCH (child:CodeUnit {id: unit.id})
        MATCH (parent:CodeUnit {id: unit.parent_symbol_id})
        MERGE (parent)-[:CONTAINS]->(child)
        """
        neo4j_client.execute_query(contains_query, {"batch": batch})

        # 2. CALLS (Cross-function & method invocations)
        calls_query = """
        UNWIND $batch AS unit
        UNWIND unit.calls AS call
        MATCH (caller:CodeUnit {id: unit.id})
        MATCH (callee:CodeUnit {id: call.target_id})
        MERGE (caller)-[:CALLS]->(callee)
        """
        neo4j_client.execute_query(calls_query, {"batch": batch})

        # 3. IMPORTS (Module and symbol dependencies)
        imports_query = """
        UNWIND $batch AS unit
        UNWIND unit.imports AS imp
        MATCH (importer:CodeUnit {id: unit.id})
        MATCH (imported:CodeUnit {id: imp.target_id})
        MERGE (importer)-[:IMPORTS]->(imported)
        """
        neo4j_client.execute_query(imports_query, {"batch": batch})

        # 4. INHERITS (Class inheritance resolution)
        # Matches base classes defined in the same file or via an imported CodeUnit
        inherits_query = """
        UNWIND $batch AS unit
        UNWIND unit.raw_inheritance AS base_name
        MATCH (subclass:CodeUnit {id: unit.id, symbol_kind: 'class'})
        
        // Match 1: Base class is in the same file
        OPTIONAL MATCH (local_base:CodeUnit {
            file_path: unit.file_path, 
            symbol_name: base_name, 
            symbol_kind: 'class'
        })
        
        // Match 2: Base class is imported from another module
        OPTIONAL MATCH (subclass)-[:IMPORTS]->(imported_base:CodeUnit {
            symbol_name: base_name, 
            symbol_kind: 'class'
        })
        
        WITH subclass, coalesce(imported_base, local_base) AS base_class
        WHERE base_class IS NOT NULL
        MERGE (subclass)-[:INHERITS]->(base_class)
        """
        neo4j_client.execute_query(inherits_query, {"batch": batch})
