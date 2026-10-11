# app/services/agent/tools/__init__.py
from typing import Dict
from langchain_core.tools import BaseTool

from .context import build_context_tools
from .graph import build_graph_tools
from .retrieval import build_retrieval_tools
from .web import build_web_tools


def build_codebase_tools(repository) -> list[BaseTool]:
    """Build the complete read-only toolset for the Codebase Agent."""
    return (
        build_retrieval_tools(repository)
        + build_graph_tools(repository)
        + build_context_tools(repository)
        + build_web_tools()
    )


def build_tool_map(repository) -> Dict[str, BaseTool]:
    """Generates an O(1) name-to-tool lookup dictionary for the dispatcher."""
    return {t.name: t for t in build_codebase_tools(repository)}
