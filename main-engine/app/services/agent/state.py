from typing import Annotated, Any, Dict, List, Optional, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class Evidence(TypedDict, total=False):
    """
    A piece of evidence collected from the repository.

    This is intentionally structured so the final answer can later
    cite where a conclusion came from.
    """

    node_id: str
    qualified_name: str
    file_path: str
    symbol_kind: str
    summary: str

    source_code: Optional[str]

    relationship: Optional[str]
    related_node_id: Optional[str]
    related_qualified_name: Optional[str]

    relevance_score: Optional[float]


class AgentState(TypedDict):
    # ---------------------------------------------------------
    # Conversation / tool history
    # ---------------------------------------------------------

    messages: Annotated[Sequence[BaseMessage], add_messages]

    # ---------------------------------------------------------
    # Original user question
    # ---------------------------------------------------------

    query: str

    # ---------------------------------------------------------
    # Current investigation frontier
    #
    # Nodes the agent currently considers worth exploring.
    # ---------------------------------------------------------

    active_node_ids: List[str]

    # ---------------------------------------------------------
    # Nodes already investigated
    #
    # Prevents repeatedly exploring the same nodes.
    # ---------------------------------------------------------

    visited_node_ids: List[str]

    # ---------------------------------------------------------
    # Grounded evidence collected during investigation
    # ---------------------------------------------------------

    gathered_context: List[Evidence]

    # ---------------------------------------------------------
    # Things the agent believes it still needs to answer
    # ---------------------------------------------------------

    missing_evidence: List[str]

    # ---------------------------------------------------------
    # Investigation budget
    # ---------------------------------------------------------

    tool_calls: int

    # ---------------------------------------------------------
    # Final response
    # ---------------------------------------------------------

    final_answer: Optional[str]
