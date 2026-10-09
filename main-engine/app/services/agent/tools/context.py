from typing import Any, Dict, List

from langchain_core.tools import tool

from app.db.neo4j.neo4j_repository import CodebaseRepository


class ContextTools:

    def __init__(self, repository: CodebaseRepository):
        self.repository = repository

    def get_node_context(
        self,
        node_ids: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Fetch detailed information about selected code nodes.

        This is the tool the agent uses when a candidate node
        has been identified and needs to be inspected.
        """

        if not node_ids:
            return []

        # Prevent accidental huge context requests.
        node_ids = node_ids[:20]

        results = []

        for node_id in node_ids:
            node = self.repository.get_node_by_id(node_id)

            if not node:
                continue

            results.append(
                {
                    "id": node.get("id"),
                    "qualified_name": node.get("qualified_name"),
                    "symbol_name": node.get("symbol_name"),
                    "file_path": node.get("file_path"),
                    "symbol_kind": node.get("symbol_kind"),
                    "start_line": node.get("start_line"),
                    "end_line": node.get("end_line"),
                    "summary": node.get("summary"),
                    # These are included if your ingestion pipeline
                    # stores them on Neo4j.
                    "imports": node.get("imports"),
                    "calls": node.get("calls"),
                    "external_calls": node.get("external_calls"),
                    "raw_inheritance": node.get("raw_inheritance"),
                    # Your current graph may not have source_code.
                    # Keep it optional.
                    "source_code": node.get("source_code"),
                }
            )

        return results


def build_context_tools(
    repository: CodebaseRepository,
):

    service = ContextTools(repository)

    return [
        tool(
            service.get_node_context,
            name="get_node_context",
            description=(
                "Inspect detailed information about selected code "
                "nodes, including their summary, source code, "
                "dependencies, calls, inheritance and metadata."
            ),
        )
    ]
