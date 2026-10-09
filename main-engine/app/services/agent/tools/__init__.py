from .context import build_context_tools
from .graph import build_graph_tools
from .retrieval import build_retrieval_tools


def build_codebase_tools(repository):
    """
    Build the complete read-only toolset for the Codebase Agent.
    """

    return (
        build_retrieval_tools(repository)
        + build_graph_tools(repository)
        + build_context_tools(repository)
    )
