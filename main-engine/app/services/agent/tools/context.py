import os
from typing import Any, Dict, List, Optional
from langchain_core.tools import tool

from app.core.config import settings
from app.db.neo4j.neo4j_repository import CodebaseRepository


class ContextTools:

    def __init__(
        self,
        repository: CodebaseRepository,
        repo_root: Optional[str] = None,
    ):
        self.repository = repository
        # Base directory where repository files exist on your machine
        self.repo_root = (
            repo_root
            or getattr(settings, "ACTIVE_REPO_PATH", None)
            or getattr(settings, "REPO_PATH", None)
            or os.getcwd()
        )

    def _read_disk_slice(
        self, file_path: str, start_line: Optional[int], end_line: Optional[int]
    ) -> Optional[str]:
        """
        Helper to read lines from disk using 1-based indexing.
        """
        if not file_path:
            return None

        # Clean relative path prefixes
        clean_path = file_path.lstrip("./")
        full_path = (
            file_path
            if os.path.isabs(file_path)
            else os.path.join(self.repo_root, clean_path)
        )

        if not os.path.exists(full_path):
            return f"[Error: File not found on disk at '{full_path}']"

        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            # If no line bounds provided, return the whole file capped at 400 lines
            if start_line is None or end_line is None:
                return "".join(lines[:400])

            # Convert 1-based line numbers to 0-based slice indices
            start_idx = max(0, start_line - 1)
            end_idx = min(len(lines), end_line)

            if start_idx >= len(lines):
                return "[Error: start_line is beyond the end of file]"

            return "".join(lines[start_idx:end_idx])

        except Exception as e:
            return f"[Error reading file: {str(e)}]"

    def read_code_snippet(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
    ) -> Dict[str, Any]:
        """
        Reads raw source code lines from a local file between start_line and end_line.
        Use this tool when you know the file path and line coordinates and need
        to inspect exact method logic, queries, or constructor implementations.
        """
        code = self._read_disk_slice(file_path, start_line, end_line)
        return {
            "file_path": file_path,
            "start_line": start_line,
            "end_line": end_line,
            "code": code,
        }

    def get_node_context(
        self,
        node_ids: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Fetch detailed information about selected code nodes.
        If source_code is not stored in Neo4j, it will be automatically
        read from the local file using start_line and end_line.
        """
        if not node_ids:
            return []

        # Prevent accidental huge context requests
        node_ids = node_ids[:20]
        results = []

        for node_id in node_ids:
            node = self.repository.get_node_by_id(node_id)
            if not node:
                continue

            file_path = node.get("file_path")
            st_line = node.get("start_line")
            end_line = node.get("end_line")

            # Use Neo4j source_code if present, otherwise fetch slice from disk
            source_code = node.get("source_code")
            if not source_code and file_path and st_line and end_line:
                source_code = self._read_disk_slice(file_path, st_line, end_line)

            results.append(
                {
                    "id": node.get("id"),
                    "qualified_name": node.get("qualified_name"),
                    "symbol_name": node.get("symbol_name"),
                    "file_path": file_path,
                    "symbol_kind": node.get("symbol_kind"),
                    "start_line": st_line,
                    "end_line": end_line,
                    "summary": node.get("summary"),
                    "imports": node.get("imports"),
                    "calls": node.get("calls"),
                    "external_calls": node.get("external_calls"),
                    "raw_inheritance": node.get("raw_inheritance"),
                    "source_code": source_code,
                }
            )

        return results


def build_context_tools(
    repository: CodebaseRepository,
):
    service = ContextTools(repository)

    return [
        tool(
            "get_node_context",
            description=(
                "Inspect detailed information about selected code nodes, "
                "including their summary, dependencies, calls, inheritance, "
                "and source code sliced directly from the file."
            ),
        )(service.get_node_context),
        tool(
            "read_code_snippet",
            description=(
                "Read raw source code lines from a file path on disk between "
                "start_line and end_line. Use this when inspecting method implementations, "
                "queries, or class constructors."
            ),
        )(service.read_code_snippet),
    ]
